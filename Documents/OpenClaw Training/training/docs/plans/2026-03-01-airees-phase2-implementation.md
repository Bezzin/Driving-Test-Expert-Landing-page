# Airees Phase 2 — Worker Tools, Parallel Execution, and Resilience — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade Airees workers from one-shot text generators to parallel, tool-using agents with web research (Tavily), provider failover, concurrency control, priority queuing, and intent-aware planning.

**Architecture:** Workers gain an agentic tool_use loop. The orchestrator dispatches independent workers concurrently via a priority-aware WorkerPool. A FallbackRouter wraps the model router with retry + provider failover. TavilyToolProvider exposes web_search/web_extract as worker tools. An IntentClassifier (Haiku) pre-processes goals before Brain planning.

**Tech Stack:** Python 3.12+, tavily-python, asyncio (Semaphore, PriorityQueue, gather), existing aiosqlite/FastAPI/pytest stack.

**Design doc:** `docs/plans/2026-03-01-airees-phase2-design.md`

---

### Task 1: Add `priority` Column to Tasks Table

**Files:**
- Modify: `airees/packages/core/airees/db/schema.py:47-85` (initialize method, add priority column)
- Modify: `airees/packages/core/airees/db/schema.py:160-191` (create_task, accept priority param)
- Modify: `airees/packages/core/airees/brain/tools.py:27-63` (create_plan schema, add priority field)
- Test: `airees/packages/core/tests/test_task_priority.py`

**Context:** Tasks need a priority field so the worker pool can schedule higher-priority tasks first. The Brain sets priority when planning via the `create_plan` tool. The `tasks` table needs a new `priority` column.

**Step 1: Write the failing tests**

```python
"""Tests for task priority support."""
import pytest
import pytest_asyncio
from airees.db.schema import GoalStore, TaskStatus


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_create_task_with_priority(store):
    goal_id = await store.create_goal(description="Test goal")
    task_id = await store.create_task(
        goal_id=goal_id,
        title="Important task",
        description="Do something important",
        agent_role="coder",
        dependencies=[],
        priority=1,
    )
    task = await store.get_task(task_id)
    assert task["priority"] == 1


@pytest.mark.asyncio
async def test_create_task_default_priority(store):
    goal_id = await store.create_goal(description="Test goal")
    task_id = await store.create_task(
        goal_id=goal_id,
        title="Normal task",
        description="Regular work",
        agent_role="coder",
        dependencies=[],
    )
    task = await store.get_task(task_id)
    assert task["priority"] == 2


@pytest.mark.asyncio
async def test_ready_tasks_include_priority(store):
    goal_id = await store.create_goal(description="Test goal")
    await store.create_task(
        goal_id=goal_id, title="Low", description="", agent_role="coder",
        dependencies=[], priority=3,
    )
    await store.create_task(
        goal_id=goal_id, title="High", description="", agent_role="coder",
        dependencies=[], priority=1,
    )
    ready = await store.get_ready_tasks(goal_id)
    assert len(ready) == 2
    assert all("priority" in t for t in ready)
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_task_priority.py -v`
Expected: FAIL — `create_task() got an unexpected keyword argument 'priority'`

**Step 3: Implement**

In `schema.py`, modify `initialize()` — add `priority INTEGER NOT NULL DEFAULT 2` to the tasks table after `status`:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL REFERENCES goals(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    agent_role TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 2,
    dependencies TEXT NOT NULL DEFAULT '[]',
    ...
);
```

Modify `create_task()` — add `priority: int = 2` parameter, include it in the INSERT:

```python
async def create_task(
    self,
    goal_id: str,
    title: str,
    description: str,
    agent_role: str,
    dependencies: list[str],
    max_retries: int = 3,
    priority: int = 2,
) -> str:
    task_id = str(uuid.uuid4())
    status = (
        TaskStatus.BLOCKED.value if dependencies else TaskStatus.PENDING.value
    )
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            """INSERT INTO tasks
               (id, goal_id, title, description, agent_role, status, priority, dependencies, max_retries)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, goal_id, title, description, agent_role, status, priority, json.dumps(dependencies), max_retries),
        )
        await db.commit()
    return task_id
```

In `brain/tools.py`, add `priority` to the create_plan task item schema (inside `get_brain_tools()`, in the `create_plan` tool's task item properties):

```python
"priority": {
    "type": "integer",
    "enum": [0, 1, 2, 3],
    "description": "Task priority: 0=critical, 1=high, 2=normal, 3=low",
},
```

In `orchestrator.py` `plan()` method, pass priority through when creating tasks (around line 89):

```python
task_id = await self.store.create_task(
    goal_id=goal_id,
    title=task_spec["title"],
    description=task_spec.get("description", ""),
    agent_role=task_spec.get("agent_role", "coder"),
    dependencies=dep_ids,
    priority=task_spec.get("priority", 2),
)
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_task_priority.py -v`
Expected: 3 PASS

Run: `cd airees/packages/core && python -m pytest tests/ -v`
Expected: All existing tests still pass (156+ tests)

**Step 5: Commit**

```bash
git add airees/packages/core/airees/db/schema.py airees/packages/core/airees/brain/tools.py airees/packages/core/airees/brain/orchestrator.py airees/packages/core/tests/test_task_priority.py
git commit -m "feat: add priority field to tasks for priority-aware scheduling"
```

---

### Task 2: Concurrency Manager

**Files:**
- Create: `airees/packages/core/airees/concurrency.py`
- Test: `airees/packages/core/tests/test_concurrency.py`

**Context:** When workers run in parallel, we need to limit how many hit each provider/model simultaneously to avoid rate limits. The ConcurrencyManager uses `asyncio.Semaphore` per concurrency key.

**Step 1: Write the failing tests**

```python
"""Tests for the concurrency manager."""
import asyncio
import pytest
from airees.concurrency import ConcurrencyManager


@pytest.mark.asyncio
async def test_acquire_and_release():
    mgr = ConcurrencyManager(
        provider_limits={"anthropic": 2},
        model_limits={},
    )
    await mgr.acquire(provider="anthropic", model="haiku")
    await mgr.acquire(provider="anthropic", model="haiku")
    # Third acquire should block — verify with timeout
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mgr.acquire(provider="anthropic", model="haiku"),
            timeout=0.1,
        )
    await mgr.release(provider="anthropic", model="haiku")
    # Now a slot is free
    await asyncio.wait_for(
        mgr.acquire(provider="anthropic", model="haiku"),
        timeout=0.1,
    )
    # Cleanup
    await mgr.release(provider="anthropic", model="haiku")
    await mgr.release(provider="anthropic", model="haiku")


@pytest.mark.asyncio
async def test_model_limit_overrides_provider():
    mgr = ConcurrencyManager(
        provider_limits={"anthropic": 10},
        model_limits={"claude-opus-4-6": 1},
    )
    await mgr.acquire(provider="anthropic", model="claude-opus-4-6")
    # Model limit is 1, so second acquire blocks even though provider allows 10
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mgr.acquire(provider="anthropic", model="claude-opus-4-6"),
            timeout=0.1,
        )
    await mgr.release(provider="anthropic", model="claude-opus-4-6")


@pytest.mark.asyncio
async def test_default_limit_when_not_configured():
    mgr = ConcurrencyManager(
        provider_limits={},
        model_limits={},
        default_limit=5,
    )
    # Should use default_limit for unknown providers
    tasks_acquired = 0
    for _ in range(5):
        await mgr.acquire(provider="unknown", model="some-model")
        tasks_acquired += 1
    assert tasks_acquired == 5
    # 6th should block
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mgr.acquire(provider="unknown", model="some-model"),
            timeout=0.1,
        )
    for _ in range(5):
        await mgr.release(provider="unknown", model="some-model")


@pytest.mark.asyncio
async def test_different_providers_independent():
    mgr = ConcurrencyManager(
        provider_limits={"anthropic": 1, "openrouter": 1},
        model_limits={},
    )
    await mgr.acquire(provider="anthropic", model="haiku")
    # Different provider should not be blocked
    await asyncio.wait_for(
        mgr.acquire(provider="openrouter", model="llama"),
        timeout=0.1,
    )
    await mgr.release(provider="anthropic", model="haiku")
    await mgr.release(provider="openrouter", model="llama")
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_concurrency.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'airees.concurrency'`

**Step 3: Implement**

```python
"""Concurrency manager — rate-limits parallel worker execution per provider and model."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class ConcurrencyManager:
    """Controls how many workers can hit each provider/model simultaneously.

    Uses asyncio.Semaphore per concurrency key. Both provider-level and
    model-level limits are enforced — a worker must acquire both before
    executing.

    Attributes:
        provider_limits: Max concurrent requests per provider name.
        model_limits: Max concurrent requests per model ID (overrides provider).
        default_limit: Fallback limit for unconfigured providers/models.
    """

    provider_limits: dict[str, int] = field(default_factory=dict)
    model_limits: dict[str, int] = field(default_factory=dict)
    default_limit: int = 5
    _semaphores: dict[str, asyncio.Semaphore] = field(
        default_factory=dict, init=False, repr=False
    )

    def _get_semaphore(self, key: str, limit: int) -> asyncio.Semaphore:
        if key not in self._semaphores:
            self._semaphores[key] = asyncio.Semaphore(limit)
        return self._semaphores[key]

    async def acquire(self, provider: str, model: str) -> None:
        """Acquire provider and model semaphores before executing a worker."""
        provider_limit = self.provider_limits.get(provider, self.default_limit)
        provider_sem = self._get_semaphore(f"provider:{provider}", provider_limit)
        await provider_sem.acquire()

        if model in self.model_limits:
            model_sem = self._get_semaphore(f"model:{model}", self.model_limits[model])
            try:
                await model_sem.acquire()
            except Exception:
                provider_sem.release()
                raise

    async def release(self, provider: str, model: str) -> None:
        """Release provider and model semaphores after worker completes."""
        provider_key = f"provider:{provider}"
        if provider_key in self._semaphores:
            self._semaphores[provider_key].release()

        model_key = f"model:{model}"
        if model_key in self._semaphores:
            self._semaphores[model_key].release()
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_concurrency.py -v`
Expected: 4 PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/concurrency.py airees/packages/core/tests/test_concurrency.py
git commit -m "feat: add ConcurrencyManager with per-provider and per-model rate limiting"
```

---

### Task 3: Worker Pool with Priority Queue

**Files:**
- Create: `airees/packages/core/airees/worker_pool.py`
- Test: `airees/packages/core/tests/test_worker_pool.py`

**Context:** The WorkerPool wraps the ConcurrencyManager with a priority queue. Tasks are submitted with their priority value. The pool processes them highest-priority-first, respecting concurrency limits, and returns results when all are done.

**Step 1: Write the failing tests**

```python
"""Tests for the priority-aware worker pool."""
import asyncio
import pytest
from airees.concurrency import ConcurrencyManager
from airees.worker_pool import WorkerPool


@pytest.mark.asyncio
async def test_pool_executes_all_tasks():
    mgr = ConcurrencyManager(provider_limits={"test": 10}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    results = []

    async def executor(task):
        results.append(task["title"])
        return {"task_id": task["id"], "status": "completed"}

    pool.submit({"id": "1", "title": "A", "priority": 2, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "B", "priority": 2, "agent_role": "coder"})

    await pool.run_all(executor, provider="test", model="test-model")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pool_respects_priority_order():
    mgr = ConcurrencyManager(provider_limits={"test": 1}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    execution_order = []

    async def executor(task):
        execution_order.append(task["title"])
        await asyncio.sleep(0.01)
        return {"task_id": task["id"], "status": "completed"}

    # Submit low priority first, then high
    pool.submit({"id": "1", "title": "Low", "priority": 3, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "High", "priority": 1, "agent_role": "coder"})
    pool.submit({"id": "3", "title": "Critical", "priority": 0, "agent_role": "coder"})

    # With concurrency=1, tasks run sequentially in priority order
    await pool.run_all(executor, provider="test", model="test-model")
    assert execution_order == ["Critical", "High", "Low"]


@pytest.mark.asyncio
async def test_pool_returns_results():
    mgr = ConcurrencyManager(provider_limits={"test": 10}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    async def executor(task):
        return {"task_id": task["id"], "output": f"done-{task['title']}"}

    pool.submit({"id": "1", "title": "A", "priority": 2, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "B", "priority": 2, "agent_role": "coder"})

    results = await pool.run_all(executor, provider="test", model="test-model")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pool_captures_exceptions():
    mgr = ConcurrencyManager(provider_limits={"test": 10}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    async def executor(task):
        if task["title"] == "Fail":
            raise RuntimeError("Worker crashed")
        return {"task_id": task["id"], "status": "ok"}

    pool.submit({"id": "1", "title": "OK", "priority": 2, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "Fail", "priority": 2, "agent_role": "coder"})

    results = await pool.run_all(executor, provider="test", model="test-model")
    # Both results returned; one is an exception
    assert len(results) == 2
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) == 1
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_worker_pool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'airees.worker_pool'`

**Step 3: Implement**

```python
"""Priority-aware worker pool for parallel task execution."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from airees.concurrency import ConcurrencyManager


@dataclass
class WorkerPool:
    """Executes tasks in priority order, respecting concurrency limits.

    Tasks are submitted with a priority value (lower = higher priority).
    The pool uses an asyncio.PriorityQueue internally and launches workers
    up to the concurrency limit, processing highest-priority tasks first.
    """

    concurrency: ConcurrencyManager
    _queue: asyncio.PriorityQueue = field(init=False)
    _counter: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._queue = asyncio.PriorityQueue()

    def submit(self, task: dict) -> None:
        """Add a task to the priority queue.

        Uses (priority, counter) as the sort key so tasks with equal
        priority preserve insertion order.
        """
        priority = task.get("priority", 2)
        self._queue.put_nowait((priority, self._counter, task))
        self._counter += 1

    async def run_all(
        self,
        executor: Callable[[dict], Coroutine[Any, Any, Any]],
        provider: str,
        model: str,
    ) -> list[Any]:
        """Process all queued tasks and return results.

        Args:
            executor: Async function that takes a task dict and returns a result.
            provider: Provider name for concurrency limiting.
            model: Model ID for concurrency limiting.

        Returns:
            List of results (or Exception objects for failed tasks).
        """
        tasks: list[asyncio.Task] = []

        async def _run(task_dict: dict) -> Any:
            await self.concurrency.acquire(provider, model)
            try:
                return await executor(task_dict)
            except Exception as e:
                return e
            finally:
                await self.concurrency.release(provider, model)

        while not self._queue.empty():
            _, _, task_dict = self._queue.get_nowait()
            tasks.append(asyncio.create_task(_run(task_dict)))

        if not tasks:
            return []

        return list(await asyncio.gather(*tasks))
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_worker_pool.py -v`
Expected: 4 PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/worker_pool.py airees/packages/core/tests/test_worker_pool.py
git commit -m "feat: add WorkerPool with priority queue and concurrency control"
```

---

### Task 4: Fallback Router

**Files:**
- Create: `airees/packages/core/airees/router/fallback.py`
- Test: `airees/packages/core/tests/test_fallback_router.py`

**Context:** The FallbackRouter wraps multiple provider routers. If one fails (rate limit, error), it tries the next provider. Exponential backoff between retries. Only tries providers that support the requested model.

**Step 1: Write the failing tests**

```python
"""Tests for the fallback router."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from airees.router.fallback import FallbackRouter
from airees.router.types import ModelConfig


@pytest.mark.asyncio
async def test_fallback_uses_first_provider():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(return_value=MagicMock(content=[]))

    router = FallbackRouter(
        providers=[("anthropic", provider1)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    await router.create_message(model=model, system="test", messages=[])
    provider1.create_message.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_retries_on_rate_limit():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(
        side_effect=[Exception("rate limit"), MagicMock(content=[])]
    )

    router = FallbackRouter(
        providers=[("anthropic", provider1)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
        backoff_base=0.01,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    result = await router.create_message(model=model, system="test", messages=[])
    assert provider1.create_message.call_count == 2


@pytest.mark.asyncio
async def test_fallback_tries_next_provider():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(side_effect=Exception("down"))

    provider2 = AsyncMock()
    provider2.create_message = AsyncMock(return_value=MagicMock(content=[]))

    router = FallbackRouter(
        providers=[("anthropic", provider1), ("openrouter", provider2)],
        model_compatibility={"claude-haiku-4-5": ["anthropic", "openrouter"]},
        max_retries=1,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    result = await router.create_message(model=model, system="test", messages=[])
    provider2.create_message.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_skips_incompatible_providers():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(side_effect=Exception("down"))

    provider2 = AsyncMock()
    provider2.create_message = AsyncMock(return_value=MagicMock(content=[]))

    router = FallbackRouter(
        providers=[("anthropic", provider1), ("openai", provider2)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
        max_retries=1,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    with pytest.raises(Exception, match="down"):
        await router.create_message(model=model, system="test", messages=[])
    # openai was never called because it's not compatible with claude
    provider2.create_message.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_raises_after_all_retries():
    provider1 = AsyncMock()
    provider1.create_message = AsyncMock(side_effect=Exception("always fails"))

    router = FallbackRouter(
        providers=[("anthropic", provider1)],
        model_compatibility={"claude-haiku-4-5": ["anthropic"]},
        max_retries=2,
        backoff_base=0.01,
    )
    model = ModelConfig(model_id="claude-haiku-4-5")
    with pytest.raises(Exception, match="always fails"):
        await router.create_message(model=model, system="test", messages=[])
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_fallback_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'airees.router.fallback'`

**Step 3: Implement**

```python
"""Fallback router — retries across multiple providers with exponential backoff."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from airees.router.types import ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class FallbackRouter:
    """Wraps multiple provider routers with retry and failover logic.

    When a provider returns an error (rate limit, outage, etc.), the router
    retries with exponential backoff, then tries the next compatible provider.

    Attributes:
        providers: Ordered list of (name, router) tuples. First = preferred.
        model_compatibility: Maps model IDs to lists of compatible provider names.
        max_retries: Max retry attempts per provider per round.
        backoff_base: Base delay in seconds for exponential backoff.
    """

    providers: list[tuple[str, Any]]
    model_compatibility: dict[str, list[str]] = field(default_factory=dict)
    max_retries: int = 3
    backoff_base: float = 1.0

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a message, retrying across providers on failure.

        Args:
            model: Model configuration.
            system: System prompt.
            messages: Conversation messages.
            tools: Optional tool definitions.

        Returns:
            The response from the first successful provider.

        Raises:
            The last exception if all providers and retries are exhausted.
        """
        compatible = self.model_compatibility.get(model.model_id)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            for provider_name, router in self.providers:
                if compatible and provider_name not in compatible:
                    continue
                try:
                    return await router.create_message(
                        model=model,
                        system=system,
                        messages=messages,
                        tools=tools,
                        **kwargs,
                    )
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "Provider %s failed (attempt %d): %s",
                        provider_name, attempt + 1, e,
                    )
                    continue

            if attempt < self.max_retries - 1:
                delay = self.backoff_base * (2 ** attempt)
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise RuntimeError("No providers configured")
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_fallback_router.py -v`
Expected: 5 PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/router/fallback.py airees/packages/core/tests/test_fallback_router.py
git commit -m "feat: add FallbackRouter with multi-provider retry and exponential backoff"
```

---

### Task 5: Tavily Tool Provider

**Files:**
- Create: `airees/packages/core/airees/tools/providers/__init__.py`
- Create: `airees/packages/core/airees/tools/providers/tavily.py`
- Modify: `airees/packages/core/pyproject.toml:6-12` (add tavily-python dependency)
- Test: `airees/packages/core/tests/test_tavily_provider.py`

**Context:** The TavilyToolProvider wraps the `tavily-python` SDK. It exposes `web_search` and `web_extract` as `ToolDefinition` objects that workers can call via `tool_use`. If `TAVILY_API_KEY` is not set, the provider returns an empty tool list (graceful degradation).

**Step 1: Write the failing tests**

```python
"""Tests for the Tavily tool provider."""
import json
import os
import pytest
from unittest.mock import MagicMock, patch
from airees.tools.providers.tavily import TavilyToolProvider


def test_get_tools_returns_definitions():
    provider = TavilyToolProvider(api_key="test-key")
    tools = provider.get_tools()
    assert len(tools) == 2
    names = [t.name for t in tools]
    assert "web_search" in names
    assert "web_extract" in names


def test_get_tools_empty_when_no_key():
    provider = TavilyToolProvider(api_key="")
    tools = provider.get_tools()
    assert tools == []


def test_web_search_tool_schema():
    provider = TavilyToolProvider(api_key="test-key")
    tools = provider.get_tools()
    search_tool = next(t for t in tools if t.name == "web_search")
    props = search_tool.input_schema["properties"]
    assert "query" in props
    assert "max_results" in props


def test_web_extract_tool_schema():
    provider = TavilyToolProvider(api_key="test-key")
    tools = provider.get_tools()
    extract_tool = next(t for t in tools if t.name == "web_extract")
    props = extract_tool.input_schema["properties"]
    assert "urls" in props


@pytest.mark.asyncio
async def test_execute_web_search():
    provider = TavilyToolProvider(api_key="test-key")
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {"title": "Result 1", "url": "https://example.com", "content": "Some info"}
        ]
    }
    provider._client = mock_client

    result = await provider.execute("web_search", {"query": "test query"})
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Result 1"
    mock_client.search.assert_called_once_with(query="test query")


@pytest.mark.asyncio
async def test_execute_web_extract():
    provider = TavilyToolProvider(api_key="test-key")
    mock_client = MagicMock()
    mock_client.extract.return_value = {
        "results": [
            {"url": "https://example.com", "raw_content": "Page content here"}
        ]
    }
    provider._client = mock_client

    result = await provider.execute("web_extract", {"urls": ["https://example.com"]})
    parsed = json.loads(result)
    assert parsed[0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    provider = TavilyToolProvider(api_key="test-key")
    with pytest.raises(ValueError, match="Unknown tool"):
        await provider.execute("unknown_tool", {})


def test_from_env_returns_none_when_not_set():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("TAVILY_API_KEY", None)
        provider = TavilyToolProvider.from_env()
        assert provider is None


def test_from_env_returns_provider_when_set():
    with patch.dict(os.environ, {"TAVILY_API_KEY": "tvly-test"}):
        provider = TavilyToolProvider.from_env()
        assert provider is not None
        assert provider.api_key == "tvly-test"
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_tavily_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'airees.tools.providers'`

**Step 3: Implement**

First, add `tavily-python` to `pyproject.toml` dependencies:

```toml
dependencies = [
    "anthropic>=0.52.0",
    "httpx>=0.27.0",
    "pydantic>=2.10.0",
    "aiosqlite>=0.20.0",
    "click>=8.1.0",
    "tavily-python>=0.5.0",
]
```

Create `airees/packages/core/airees/tools/providers/__init__.py`:

```python
"""Tool providers — external service integrations for worker agents."""
```

Create `airees/packages/core/airees/tools/providers/tavily.py`:

```python
"""Tavily tool provider — web search and content extraction for workers."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from airees.tools.registry import ToolDefinition


@dataclass
class TavilyToolProvider:
    """Wraps the Tavily API as tools workers can call via tool_use.

    Exposes web_search and web_extract. If api_key is empty, get_tools()
    returns an empty list (graceful degradation — workers still function
    but cannot search the web).

    Attributes:
        api_key: Tavily API key from TAVILY_API_KEY env var.
    """

    api_key: str
    _client: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.api_key:
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=self.api_key)

    @classmethod
    def from_env(cls) -> TavilyToolProvider | None:
        """Create a provider from the TAVILY_API_KEY env var.

        Returns None if the env var is not set.
        """
        key = os.environ.get("TAVILY_API_KEY", "")
        if not key:
            return None
        return cls(api_key=key)

    def get_tools(self) -> list[ToolDefinition]:
        """Return tool definitions for LLM tool_use.

        Returns an empty list if no API key is configured.
        """
        if not self.api_key:
            return []

        return [
            ToolDefinition(
                name="web_search",
                description=(
                    "Search the web for current information. Returns ranked results "
                    "with titles, URLs, and content snippets."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            ToolDefinition(
                name="web_extract",
                description=(
                    "Extract content from one or more URLs. Returns the full page "
                    "content as text."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs to extract content from (max 20)",
                        },
                    },
                    "required": ["urls"],
                },
            ),
        ]

    async def execute(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call and return the result as a JSON string.

        Args:
            tool_name: The tool to execute (web_search or web_extract).
            tool_input: The tool's input parameters.

        Returns:
            JSON string of the results.

        Raises:
            ValueError: If tool_name is not recognized.
        """
        if tool_name == "web_search":
            result = self._client.search(**tool_input)
            return json.dumps(result.get("results", []), indent=2)
        elif tool_name == "web_extract":
            result = self._client.extract(urls=tool_input["urls"])
            return json.dumps(result.get("results", []), indent=2)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
```

Run: `pip install tavily-python` to install the dependency.

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && pip install -e ".[dev]" && python -m pytest tests/test_tavily_provider.py -v`
Expected: 9 PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/tools/providers/ airees/packages/core/tests/test_tavily_provider.py airees/packages/core/pyproject.toml
git commit -m "feat: add TavilyToolProvider with web_search and web_extract tools"
```

---

### Task 6: Role-to-Tools Mapping in Worker Builder

**Files:**
- Modify: `airees/packages/core/airees/coordinator/worker_builder.py:1-73` (add ROLE_TOOLS mapping and tools parameter to build_worker_prompt)
- Test: `airees/packages/core/tests/test_role_tools.py`

**Context:** Different agent roles need different tools. Researchers need web search. Coders don't. This task adds a mapping from role to tool names, and updates `build_worker_prompt` to include tool usage instructions when tools are available.

**Step 1: Write the failing tests**

```python
"""Tests for role-to-tools mapping."""
import pytest
from airees.coordinator.worker_builder import ROLE_TOOLS, get_tools_for_role, build_worker_prompt


def test_researcher_gets_search_tools():
    tools = get_tools_for_role("researcher")
    assert "web_search" in tools
    assert "web_extract" in tools


def test_coder_gets_no_tools():
    tools = get_tools_for_role("coder")
    assert tools == []


def test_reviewer_gets_search():
    tools = get_tools_for_role("reviewer")
    assert "web_search" in tools


def test_unknown_role_gets_empty():
    tools = get_tools_for_role("unknown_role")
    assert tools == []


def test_worker_prompt_includes_tool_instructions():
    prompt = build_worker_prompt(
        task_title="Research AI",
        task_description="Find AI papers",
        agent_role="researcher",
        available_tools=["web_search"],
    )
    assert "web_search" in prompt
    assert "tool" in prompt.lower()


def test_worker_prompt_no_tools_no_instructions():
    prompt = build_worker_prompt(
        task_title="Write code",
        task_description="Build a function",
        agent_role="coder",
    )
    assert "web_search" not in prompt
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_role_tools.py -v`
Expected: FAIL — `ImportError: cannot import name 'ROLE_TOOLS' from 'airees.coordinator.worker_builder'`

**Step 3: Implement**

Add to `worker_builder.py` after the ESCALATION_MODELS dict:

```python
ROLE_TOOLS: dict[str, list[str]] = {
    "researcher": ["web_search", "web_extract"],
    "coder": [],
    "reviewer": ["web_search"],
    "writer": ["web_search", "web_extract"],
    "planner": ["web_search"],
    "tester": [],
    "security": ["web_search"],
    "architect": ["web_search"],
}


def get_tools_for_role(agent_role: str) -> list[str]:
    """Return the list of tool names available to the given agent role."""
    return list(ROLE_TOOLS.get(agent_role, []))
```

Update `build_worker_prompt` to accept and use an `available_tools` parameter:

```python
def build_worker_prompt(
    *,
    task_title: str,
    task_description: str,
    agent_role: str,
    skill_content: str | None = None,
    previous_output: str | None = None,
    available_tools: list[str] | None = None,
) -> str:
    sections = [
        f"You are a specialist {agent_role} agent. Complete the following task thoroughly.",
        f"\n## Task: {task_title}\n\n{task_description}",
    ]

    if previous_output:
        sections.append(f"\n## Context From Previous Task\n\n{previous_output}")

    if skill_content:
        sections.append(f"\n## Relevant Skill Reference\n\n{skill_content}")

    if available_tools:
        tool_list = ", ".join(available_tools)
        sections.append(
            f"\n## Available Tools\n\n"
            f"You have access to the following tools: {tool_list}\n"
            f"Use these tools when you need external information. "
            f"Call tools via tool_use blocks. You can call multiple tools "
            f"in sequence to gather information before producing your final output.\n"
        )

    sections.append(
        "\n## Output Requirements\n\n"
        "Return your work product clearly. Include:\n"
        "- The actual output (code, text, analysis, etc.)\n"
        "- A confidence score (0-10) for your work quality\n"
        "- Any discoveries or unexpected findings\n"
    )

    return "\n".join(sections)
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_role_tools.py -v`
Expected: 6 PASS

Run: `cd airees/packages/core && python -m pytest tests/ -v`
Expected: All existing tests still pass

**Step 5: Commit**

```bash
git add airees/packages/core/airees/coordinator/worker_builder.py airees/packages/core/tests/test_role_tools.py
git commit -m "feat: add role-to-tools mapping and tool instructions in worker prompts"
```

---

### Task 7: Tool_use Agentic Loop in Worker Execution

**Files:**
- Modify: `airees/packages/core/airees/brain/orchestrator.py:156-203` (_execute_worker method — replace one-shot with loop)
- Test: `airees/packages/core/tests/test_worker_tool_loop.py`

**Context:** This is the big change. Currently `_execute_worker` makes one LLM call and reads the text. Now it runs an agentic loop: call LLM → check for tool_use → execute tools → feed results back → repeat until `end_turn`. This lets workers actually use Tavily search/extract during their work.

**Step 1: Write the failing tests**

```python
"""Tests for the agentic tool_use loop in worker execution."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus


def _make_tool_use_response(tool_name: str, tool_input: dict) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=50, output_tokens=50)
    block = MagicMock()
    block.type = "tool_use"
    block.id = "tool_call_1"
    block.name = tool_name
    block.input = tool_input
    response.content = [block]
    return response


def _make_text_response(text: str) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=50, output_tokens=100)
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_worker_with_tool_use_loop(store, tmp_path):
    """Worker calls web_search, gets result, then produces final text."""
    mock_router = AsyncMock()
    mock_tool_provider = AsyncMock()
    mock_tool_provider.execute = AsyncMock(return_value='[{"title": "Result", "content": "Found it"}]')
    mock_tool_provider.get_tools.return_value = []

    # Call 1: Worker requests tool_use (web_search)
    # Call 2: Worker produces final text after getting search results
    mock_router.create_message = AsyncMock(side_effect=[
        _make_tool_use_response("web_search", {"query": "test query"}),
        _make_text_response("Based on my research, the answer is 42."),
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
        tool_provider=mock_tool_provider,
    )

    goal_id = await store.create_goal(description="Test")
    task_id = await store.create_task(
        goal_id=goal_id, title="Research", description="Find info",
        agent_role="researcher", dependencies=[],
    )
    task = await store.get_task(task_id)
    await orch._execute_worker(goal_id, task)

    # Tool was called
    mock_tool_provider.execute.assert_called_once_with("web_search", {"query": "test query"})
    # Router was called twice (tool_use then end_turn)
    assert mock_router.create_message.call_count == 2
    # Task completed with final text
    completed_task = await store.get_task(task_id)
    assert completed_task["status"] == "completed"
    assert "42" in completed_task["result"]


@pytest.mark.asyncio
async def test_worker_without_tools_still_works(store, tmp_path):
    """Workers without tools work as before — single call, text response."""
    mock_router = AsyncMock()
    mock_router.create_message = AsyncMock(
        return_value=_make_text_response("Code written successfully.")
    )

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
    )

    goal_id = await store.create_goal(description="Test")
    task_id = await store.create_task(
        goal_id=goal_id, title="Code", description="Write code",
        agent_role="coder", dependencies=[],
    )
    task = await store.get_task(task_id)
    await orch._execute_worker(goal_id, task)

    assert mock_router.create_message.call_count == 1
    completed_task = await store.get_task(task_id)
    assert completed_task["status"] == "completed"


@pytest.mark.asyncio
async def test_worker_tool_loop_max_rounds(store, tmp_path):
    """Worker stops after max_tool_rounds even if LLM keeps requesting tools."""
    mock_router = AsyncMock()
    mock_tool_provider = AsyncMock()
    mock_tool_provider.execute = AsyncMock(return_value='{"result": "data"}')
    mock_tool_provider.get_tools.return_value = []

    # Always returns tool_use — should hit max_tool_rounds limit
    mock_router.create_message = AsyncMock(
        return_value=_make_tool_use_response("web_search", {"query": "infinite"})
    )

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
        tool_provider=mock_tool_provider,
    )

    goal_id = await store.create_goal(description="Test")
    task_id = await store.create_task(
        goal_id=goal_id, title="Search", description="Search forever",
        agent_role="researcher", dependencies=[],
    )
    task = await store.get_task(task_id)
    await orch._execute_worker(goal_id, task)

    # Should have stopped at max_tool_rounds (10)
    assert mock_router.create_message.call_count == 10
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_worker_tool_loop.py -v`
Expected: FAIL — `TypeError: BrainOrchestrator.__init__() got an unexpected keyword argument 'tool_provider'`

**Step 3: Implement**

Modify `BrainOrchestrator` dataclass to accept `tool_provider`:

Add after `state_machine` field:
```python
tool_provider: Any = None  # TavilyToolProvider or None
```

Replace the entire `_execute_worker` method with the agentic loop:

```python
async def _execute_worker(self, goal_id: str, task: dict) -> None:
    """Run a single worker sub-agent with an agentic tool_use loop."""
    from airees.coordinator.worker_builder import get_tools_for_role

    role_tool_names = get_tools_for_role(task["agent_role"])
    worker_prompt = build_worker_prompt(
        task_title=task["title"],
        task_description=task["description"],
        agent_role=task["agent_role"],
        available_tools=role_tool_names if role_tool_names else None,
    )
    model_id = select_model(agent_role=task["agent_role"])
    model = ModelConfig(model_id=model_id)

    # Build tool definitions for the LLM
    tools_formatted = None
    if self.tool_provider and role_tool_names:
        tool_defs = self.tool_provider.get_tools()
        available = [t for t in tool_defs if t.name in role_tool_names]
        if available:
            registry = ToolRegistry()
            for t in available:
                registry.register(t)
            tools_formatted = registry.to_anthropic_format(
                [t.name for t in available]
            )

    await self.event_bus.emit_async(Event(
        event_type=EventType.AGENT_START,
        agent_name=f"worker:{task['title']}",
        data={"task_id": task["id"], "model": model_id},
    ))

    try:
        messages = [{"role": "user", "content": task["description"]}]
        total_tokens = 0
        output = ""
        max_tool_rounds = 10

        for _ in range(max_tool_rounds):
            response = await self.router.create_message(
                model=model,
                system=worker_prompt,
                messages=messages,
                tools=tools_formatted,
            )

            total_tokens += (
                response.usage.input_tokens + response.usage.output_tokens
            )

            if response.stop_reason == "end_turn" or response.stop_reason != "tool_use":
                # Extract final text
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        output += block.text
                break

            # Process tool_use blocks
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use" and self.tool_provider:
                    result = await self.tool_provider.execute(
                        block.name, block.input
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        cost = total_tokens * 0.000001

        await self.store.complete_task(
            task["id"],
            result=output,
            tokens_used=total_tokens,
            cost=cost,
        )

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_COMPLETE,
            agent_name=f"worker:{task['title']}",
            data={"task_id": task["id"], "tokens": total_tokens},
        ))

    except Exception as e:
        logger.exception("Worker failed: %s", task["title"])
        retry = task.get("retry_count", 0) < task.get("max_retries", 3)
        await self.store.fail_task(task["id"], error=str(e), retry=retry)
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_worker_tool_loop.py -v`
Expected: 3 PASS

Run: `cd airees/packages/core && python -m pytest tests/ -v`
Expected: All existing tests still pass (tool_provider defaults to None, preserving backward compatibility)

**Step 5: Commit**

```bash
git add airees/packages/core/airees/brain/orchestrator.py airees/packages/core/tests/test_worker_tool_loop.py
git commit -m "feat: add agentic tool_use loop in worker execution"
```

---

### Task 8: Parallel Execution in Orchestrator

**Files:**
- Modify: `airees/packages/core/airees/brain/orchestrator.py:110-154` (execute_goal — replace sequential with parallel via WorkerPool)
- Test: `airees/packages/core/tests/test_parallel_execution.py`

**Context:** This task replaces the sequential `for task in ready` loop with parallel execution via WorkerPool. Independent tasks (same wave in the DAG) run concurrently. Dependencies are still respected — the orchestrator loops until all tasks complete.

**Step 1: Write the failing tests**

```python
"""Tests for parallel worker execution in the orchestrator."""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus


def _make_tool_response(tool_name: str, tool_input: dict) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=100, output_tokens=200)
    block = MagicMock()
    block.type = "tool_use"
    block.id = "tool_1"
    block.name = tool_name
    block.input = tool_input
    response.content = [block]
    return response


def _make_text_response(text: str) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=50, output_tokens=100)
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_independent_tasks_run_in_parallel(store, tmp_path):
    """Two tasks with no dependencies should be executed concurrently."""
    execution_times = []

    original_create_message = AsyncMock()

    async def slow_create_message(**kwargs):
        start = asyncio.get_event_loop().time()
        await asyncio.sleep(0.05)  # Simulate work
        execution_times.append(start)
        return _make_text_response("Done")

    mock_router = AsyncMock()
    mock_router.create_message = AsyncMock(side_effect=slow_create_message)

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
    )

    goal_id = await store.create_goal(description="Parallel test")
    # Create two independent tasks directly (skip Brain planning)
    await store.create_task(
        goal_id=goal_id, title="Task A", description="Do A",
        agent_role="coder", dependencies=[], priority=2,
    )
    await store.create_task(
        goal_id=goal_id, title="Task B", description="Do B",
        agent_role="coder", dependencies=[], priority=2,
    )

    # Execute just the worker phase (not full goal loop)
    await orch._execute_wave(goal_id)

    # Both tasks started within 0.02s of each other (parallel, not sequential)
    assert len(execution_times) == 2
    time_diff = abs(execution_times[1] - execution_times[0])
    assert time_diff < 0.03, f"Tasks should start concurrently, but diff was {time_diff}s"


@pytest.mark.asyncio
async def test_dependent_tasks_run_in_waves(store, tmp_path):
    """Task B depends on Task A, so B should only run after A completes."""
    mock_router = AsyncMock()
    call_count = 0

    async def tracked_create_message(**kwargs):
        nonlocal call_count
        call_count += 1
        return _make_text_response(f"Result {call_count}")

    mock_router.create_message = AsyncMock(side_effect=tracked_create_message)

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
    )

    goal_id = await store.create_goal(description="Wave test")
    task_a_id = await store.create_task(
        goal_id=goal_id, title="Task A", description="Do A first",
        agent_role="coder", dependencies=[],
    )
    task_b_id = await store.create_task(
        goal_id=goal_id, title="Task B", description="Do B after A",
        agent_role="coder", dependencies=[task_a_id],
    )

    # Wave 1: Only A should run (B is blocked)
    await orch._execute_wave(goal_id)
    task_a = await store.get_task(task_a_id)
    task_b = await store.get_task(task_b_id)
    assert task_a["status"] == "completed"
    assert task_b["status"] == "pending"  # unblocked by complete_task

    # Wave 2: Now B should run
    await orch._execute_wave(goal_id)
    task_b = await store.get_task(task_b_id)
    assert task_b["status"] == "completed"
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_parallel_execution.py -v`
Expected: FAIL — `AttributeError: 'BrainOrchestrator' object has no attribute '_execute_wave'`

**Step 3: Implement**

Add a new `_execute_wave` method to `BrainOrchestrator` and update `execute_goal` to use it.

Add this import at the top of `orchestrator.py`:
```python
import asyncio
from airees.coordinator.worker_builder import build_worker_prompt, select_model, get_tools_for_role
```

Add `_execute_wave` method:
```python
async def _execute_wave(self, goal_id: str) -> None:
    """Execute all ready tasks in parallel."""
    coordinator = Coordinator(store=self.store, runner=self.router)
    ready = await coordinator.get_next_tasks(goal_id)
    if not ready:
        return

    # Sort by priority (lower = higher priority)
    ready.sort(key=lambda t: t.get("priority", 2))

    # Execute all ready tasks concurrently
    tasks = [self._execute_worker(goal_id, task) for task in ready]
    await asyncio.gather(*tasks, return_exceptions=True)
```

Update `execute_goal` to use `_execute_wave` instead of the sequential loop:
```python
async def execute_goal(self, goal_id: str) -> str:
    """Full autonomous loop: plan -> execute -> evaluate -> iterate."""
    await self.plan(goal_id)

    coordinator = Coordinator(store=self.store, runner=self.router)

    self.state_machine.transition(BrainState.WAITING)
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        while True:
            ready = await coordinator.get_next_tasks(goal_id)
            if not ready:
                break
            await self._execute_wave(goal_id)
            if await coordinator.is_goal_complete(goal_id):
                break
            if await coordinator.has_failures(goal_id):
                break

        self.state_machine.transition(BrainState.EVALUATING)
        report = await coordinator.build_report(goal_id)
        action = await self._evaluate(goal_id, report, iteration)

        if action == "satisfied":
            self.state_machine.transition(BrainState.COMPLETING)
            await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
            self.state_machine.transition(BrainState.IDLE)
            return report

        iteration += 1
        await self.store.increment_iteration(goal_id)
        self.state_machine.transition(BrainState.ADAPTING)
        self.state_machine.transition(BrainState.DELEGATING)
        self.state_machine.transition(BrainState.WAITING)

    await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
    report = await coordinator.build_report(goal_id)
    if self.state_machine.state != BrainState.IDLE:
        self.state_machine.force_reset(reason="max_iterations")
    return report
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_parallel_execution.py -v`
Expected: 2 PASS

Run: `cd airees/packages/core && python -m pytest tests/ -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add airees/packages/core/airees/brain/orchestrator.py airees/packages/core/tests/test_parallel_execution.py
git commit -m "feat: execute independent workers in parallel with wave-based scheduling"
```

---

### Task 9: Intent Classifier

**Files:**
- Create: `airees/packages/core/airees/brain/intent.py`
- Modify: `airees/packages/core/airees/brain/prompt.py:7-73` (accept intent parameter)
- Test: `airees/packages/core/tests/test_intent_classifier.py`

**Context:** A lightweight pre-processing step before Brain planning. Uses a cheap model (Haiku) to classify the goal as research/build/fix/investigate/optimize. The intent influences the Brain's planning prompt and default tool assignment.

**Step 1: Write the failing tests**

```python
"""Tests for the intent classifier."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from airees.brain.intent import GoalIntent, classify_intent, intent_to_prompt_hint
from airees.brain.prompt import build_brain_prompt
from airees.soul import Soul


def test_goal_intent_values():
    assert GoalIntent.RESEARCH.value == "research"
    assert GoalIntent.BUILD.value == "build"
    assert GoalIntent.FIX.value == "fix"
    assert GoalIntent.INVESTIGATE.value == "investigate"
    assert GoalIntent.OPTIMIZE.value == "optimize"


@pytest.mark.asyncio
async def test_classify_intent_research():
    mock_router = AsyncMock()
    response = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "research"
    response.content = [block]
    mock_router.create_message = AsyncMock(return_value=response)

    intent = await classify_intent(mock_router, "Find information about quantum computing")
    assert intent == GoalIntent.RESEARCH


@pytest.mark.asyncio
async def test_classify_intent_defaults_to_build():
    mock_router = AsyncMock()
    response = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "something_unknown"
    response.content = [block]
    mock_router.create_message = AsyncMock(return_value=response)

    intent = await classify_intent(mock_router, "Do something vague")
    assert intent == GoalIntent.BUILD


def test_intent_to_prompt_hint_research():
    hint = intent_to_prompt_hint(GoalIntent.RESEARCH)
    assert "research" in hint.lower()
    assert "search" in hint.lower()


def test_intent_to_prompt_hint_fix():
    hint = intent_to_prompt_hint(GoalIntent.FIX)
    assert "fix" in hint.lower() or "debug" in hint.lower()


def test_brain_prompt_includes_intent():
    soul = Soul(name="Test", version=0, content="Test soul", raw="")
    prompt = build_brain_prompt(
        soul=soul, goal="Fix the login bug", intent="fix",
    )
    assert "fix" in prompt.lower() or "debug" in prompt.lower()
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_intent_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'airees.brain.intent'`

**Step 3: Implement**

Create `airees/packages/core/airees/brain/intent.py`:

```python
"""Intent classifier — lightweight pre-processing before Brain planning."""
from __future__ import annotations

from enum import Enum
from typing import Any

from airees.router.types import ModelConfig


class GoalIntent(Enum):
    """Classification of what kind of work a goal requires."""

    RESEARCH = "research"
    BUILD = "build"
    FIX = "fix"
    INVESTIGATE = "investigate"
    OPTIMIZE = "optimize"


_INTENT_MAP = {v.value: v for v in GoalIntent}


async def classify_intent(router: Any, goal_description: str) -> GoalIntent:
    """Classify a goal's intent using a cheap model (~100 tokens).

    Args:
        router: The model router for LLM calls.
        goal_description: The raw goal text from the user.

    Returns:
        The classified GoalIntent. Defaults to BUILD if unrecognized.
    """
    model = ModelConfig(model_id="anthropic/claude-haiku-4-5")
    response = await router.create_message(
        model=model,
        system=(
            "Classify this goal into exactly one category: "
            "research, build, fix, investigate, optimize. "
            "Reply with only the category name, nothing else."
        ),
        messages=[{"role": "user", "content": goal_description}],
    )

    text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text = block.text.strip().lower()
            break

    return _INTENT_MAP.get(text, GoalIntent.BUILD)


_INTENT_HINTS: dict[GoalIntent, str] = {
    GoalIntent.RESEARCH: (
        "This is a RESEARCH goal. Prioritize information gathering. "
        "Assign web_search tools to workers. Focus on finding, summarizing, "
        "and synthesizing information rather than building artifacts."
    ),
    GoalIntent.BUILD: (
        "This is a BUILD goal. Focus on creating deliverables — code, "
        "documents, designs. Use a structured approach: plan, implement, test."
    ),
    GoalIntent.FIX: (
        "This is a FIX goal. Focus on debugging and repair. Start by "
        "investigating the root cause, then implement a targeted fix. "
        "Prioritize tasks that reproduce and diagnose the issue."
    ),
    GoalIntent.INVESTIGATE: (
        "This is an INVESTIGATION goal. Focus on understanding why something "
        "is happening. Gather evidence, form hypotheses, test them. "
        "Report findings clearly."
    ),
    GoalIntent.OPTIMIZE: (
        "This is an OPTIMIZATION goal. Focus on measuring current performance, "
        "identifying bottlenecks, and implementing targeted improvements. "
        "Benchmark before and after."
    ),
}


def intent_to_prompt_hint(intent: GoalIntent) -> str:
    """Return a prompt hint for the Brain based on the classified intent."""
    return _INTENT_HINTS.get(intent, _INTENT_HINTS[GoalIntent.BUILD])
```

Modify `build_brain_prompt` in `brain/prompt.py` to accept an `intent` parameter:

```python
def build_brain_prompt(
    *,
    soul: Soul,
    goal: str,
    coordinator_report: str | None = None,
    active_skill: str | None = None,
    iteration: int = 0,
    intent: str | None = None,
) -> str:
```

Add after the goal section (after `sections.append(f"\n## Current Goal\n\n{goal}\n")`):

```python
    if intent:
        from airees.brain.intent import GoalIntent, intent_to_prompt_hint
        try:
            goal_intent = GoalIntent(intent)
            sections.append(f"\n## Goal Intent\n\n{intent_to_prompt_hint(goal_intent)}\n")
        except ValueError:
            pass
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_intent_classifier.py -v`
Expected: 6 PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/brain/intent.py airees/packages/core/airees/brain/prompt.py airees/packages/core/tests/test_intent_classifier.py
git commit -m "feat: add lightweight intent classifier for goal-aware planning"
```

---

### Task 10: Wire Intent + Tavily into Orchestrator and Update Exports

**Files:**
- Modify: `airees/packages/core/airees/brain/orchestrator.py` (call classify_intent before plan, pass intent to prompt)
- Modify: `airees/packages/core/airees/__init__.py` (add new exports)
- Test: `airees/packages/core/tests/test_phase2_integration.py`

**Context:** Final wiring task. The orchestrator calls `classify_intent` before planning, passes the intent to `build_brain_prompt`, and the TavilyToolProvider is wired into worker execution. Update `__init__.py` with all new Phase 2 exports.

**Step 1: Write the integration test**

```python
"""Phase 2 integration test — full loop with Tavily tools and intent classification."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from airees.brain.orchestrator import BrainOrchestrator
from airees.brain.intent import GoalIntent
from airees.db.schema import GoalStore
from airees.events import EventBus


def _make_tool_response(tool_name: str, tool_input: dict) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=100, output_tokens=200)
    block = MagicMock()
    block.type = "tool_use"
    block.id = "tool_1"
    block.name = tool_name
    block.input = tool_input
    response.content = [block]
    return response


def _make_text_response(text: str) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=50, output_tokens=100)
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_full_phase2_loop_with_tools(store, tmp_path):
    """Full loop: intent classify → plan → parallel execute with tools → evaluate."""
    mock_router = AsyncMock()
    mock_tool_provider = AsyncMock()
    mock_tool_provider.execute = AsyncMock(
        return_value='[{"title": "Found it", "content": "Research results"}]'
    )
    mock_tool_provider.get_tools.return_value = []

    # Call 1: Intent classification (Haiku)
    intent_response = _make_text_response("research")

    # Call 2: Brain plans (create_plan tool)
    plan_response = _make_tool_response("create_plan", {
        "tasks": [
            {"title": "Research", "description": "Search for info", "agent_role": "researcher", "dependencies": [], "priority": 1},
            {"title": "Summarize", "description": "Summarize findings", "agent_role": "writer", "dependencies": [0], "priority": 2},
        ],
        "strategy": "Research then summarize",
    })

    # Call 3: Worker 1 (Research) calls web_search
    worker1_tool = MagicMock()
    worker1_tool.stop_reason = "tool_use"
    worker1_tool.usage = MagicMock(input_tokens=50, output_tokens=50)
    ws_block = MagicMock()
    ws_block.type = "tool_use"
    ws_block.id = "ws_1"
    ws_block.name = "web_search"
    ws_block.input = {"query": "research topic"}
    worker1_tool.content = [ws_block]

    # Call 4: Worker 1 final text
    worker1_final = _make_text_response("Research complete: found key info.")

    # Call 5: Worker 2 (Summarize) — no tools, just text
    worker2_response = _make_text_response("Summary: the topic is about X.")

    # Call 6: Brain evaluates
    eval_response = _make_tool_response("evaluate_result", {
        "satisfied": True,
        "reasoning": "Research and summary complete.",
        "action": "satisfied",
    })

    mock_router.create_message = AsyncMock(side_effect=[
        intent_response,
        plan_response,
        worker1_tool, worker1_final,
        worker2_response,
        eval_response,
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
        tool_provider=mock_tool_provider,
    )

    goal_id = await orch.submit_goal("Research quantum computing")
    result = await orch.execute_goal(goal_id)

    # Verify
    goal = await store.get_goal(goal_id)
    assert goal["status"] == "completed"

    tasks = await store.get_all_tasks(goal_id)
    assert len(tasks) == 2
    assert all(t["status"] == "completed" for t in tasks)

    # Tavily was called
    mock_tool_provider.execute.assert_called_once()


def test_new_exports_available():
    """Verify Phase 2 modules are exported from the core package."""
    from airees import (
        ConcurrencyManager,
        FallbackRouter,
        GoalIntent,
        WorkerPool,
        classify_intent,
        get_tools_for_role,
        intent_to_prompt_hint,
    )
    assert GoalIntent.RESEARCH.value == "research"
```

**Step 2: Run test to verify it fails**

Run: `cd airees/packages/core && python -m pytest tests/test_phase2_integration.py -v`
Expected: FAIL

**Step 3: Implement**

Wire intent classification into `execute_goal()` in `orchestrator.py`:

Add import at top:
```python
from airees.brain.intent import classify_intent
```

Modify `execute_goal` to classify intent first:
```python
async def execute_goal(self, goal_id: str) -> str:
    """Full autonomous loop: classify intent -> plan -> execute -> evaluate -> iterate."""
    # Pre-process: classify goal intent
    goal = await self.store.get_goal(goal_id)
    if goal is None:
        raise ValueError(f"Goal not found: {goal_id}")
    intent = await classify_intent(self.router, goal["description"])

    await self.plan(goal_id, intent=intent.value)
    # ... rest of method unchanged
```

Update `plan()` to accept and pass intent:
```python
async def plan(self, goal_id: str, intent: str | None = None) -> list[dict]:
```

And when building the prompt:
```python
prompt = build_brain_prompt(soul=soul, goal=goal["description"], intent=intent)
```

Update `__init__.py` — add the new imports and __all__ entries:

```python
from airees.brain.intent import GoalIntent, classify_intent, intent_to_prompt_hint
from airees.concurrency import ConcurrencyManager
from airees.coordinator.worker_builder import build_worker_prompt, get_tools_for_role, select_model
from airees.router.fallback import FallbackRouter
from airees.worker_pool import WorkerPool
```

Add to `__all__`:
```python
    "ConcurrencyManager",
    "FallbackRouter",
    "GoalIntent",
    "WorkerPool",
    "classify_intent",
    "get_tools_for_role",
    "intent_to_prompt_hint",
```

**Step 4: Run ALL tests**

Run: `cd airees/packages/core && python -m pytest tests/ -v`
Expected: All tests PASS

Run: `cd airees/packages/server && python -m pytest tests/ -v`
Expected: All server tests PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/brain/orchestrator.py airees/packages/core/airees/__init__.py airees/packages/core/tests/test_phase2_integration.py
git commit -m "feat: wire intent classifier and Tavily tools into orchestrator, update exports"
```

---

## Summary

| Task | What It Builds | Tests |
|------|---------------|-------|
| 1 | Priority column in tasks table | 3 |
| 2 | ConcurrencyManager with semaphores | 4 |
| 3 | WorkerPool with priority queue | 4 |
| 4 | FallbackRouter with retry + exponential backoff | 5 |
| 5 | TavilyToolProvider (web_search, web_extract) | 9 |
| 6 | Role-to-tools mapping in worker_builder | 6 |
| 7 | Tool_use agentic loop in worker execution | 3 |
| 8 | Parallel execution via _execute_wave | 2 |
| 9 | Intent classifier (GoalIntent, classify_intent) | 6 |
| 10 | Wire everything together + integration test | 2 |

**Total: 10 tasks, ~44 new tests, 10 commits**

**After Phase 2 you'll have:** Workers that can search the web and extract content via Tavily. Independent tasks running in parallel with priority scheduling. Automatic provider failover across Anthropic, OpenRouter, OpenAI, and Google. Intent-aware planning that tailors the Brain's strategy to the type of goal. All building on the Phase 1 Brain Foundation.
