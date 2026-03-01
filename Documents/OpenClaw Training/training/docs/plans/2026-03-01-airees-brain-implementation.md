# Airees Brain Foundation — Implementation Plan (Phase 1)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core brain loop — goal submission through Brain planning, Coordinator execution, Worker delegation, and Brain evaluation — so Airees can autonomously execute a goal end-to-end.

**Architecture:** Brain (Opus) plans and evaluates. Coordinator (cheap model) manages task graph execution and worker lifecycle. Workers (cheapest viable model) do actual work. All state persisted to SQLite. Events streamed via WebSocket.

**Tech Stack:** Python 3.12+, Anthropic Agent SDK, OpenRouter, FastAPI, SQLite (aiosqlite), pytest + pytest-asyncio

**Scope:** This is Phase 1. Does NOT include: heartbeat daemon, tool discovery, self-reflection/SOUL evolution, skills creation, progressive compression. Those are Phase 2+.

**Design doc:** `docs/plans/2026-03-01-airees-brain-design.md`

---

### Task 1: Database Schema — Goals and Tasks Tables

**Files:**
- Create: `airees/packages/core/airees/db/schema.py`
- Create: `airees/packages/core/airees/db/__init__.py`
- Test: `airees/packages/core/tests/test_db_schema.py`

**Context:** We need SQLite tables for goals (user-submitted objectives) and tasks (individual work items in a DAG). The existing `SQLiteRunStore` uses aiosqlite — we follow the same pattern but with a richer schema.

**Step 1: Write the failing tests**

```python
"""Tests for database schema initialization and CRUD operations."""
import pytest
import pytest_asyncio
from pathlib import Path
from airees.db.schema import GoalStore, GoalStatus, TaskStatus

@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s

@pytest.mark.asyncio
async def test_create_goal(store):
    goal_id = await store.create_goal(
        description="Build a todo app",
        metadata={"source": "chat"},
    )
    assert goal_id is not None
    goal = await store.get_goal(goal_id)
    assert goal["description"] == "Build a todo app"
    assert goal["status"] == GoalStatus.PENDING.value

@pytest.mark.asyncio
async def test_create_task(store):
    goal_id = await store.create_goal(description="Build app")
    task_id = await store.create_task(
        goal_id=goal_id,
        title="Scaffold project",
        description="Create Next.js project with TypeScript",
        agent_role="coder",
        dependencies=[],
    )
    task = await store.get_task(task_id)
    assert task["title"] == "Scaffold project"
    assert task["status"] == TaskStatus.PENDING.value

@pytest.mark.asyncio
async def test_task_dependencies(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="Auth", description="Add auth", agent_role="coder", dependencies=[t1])
    task2 = await store.get_task(t2)
    assert t1 in task2["dependencies"]

@pytest.mark.asyncio
async def test_get_ready_tasks(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="Auth", description="", agent_role="coder", dependencies=[t1])
    ready = await store.get_ready_tasks(goal_id)
    assert len(ready) == 1
    assert ready[0]["id"] == t1

@pytest.mark.asyncio
async def test_complete_task_unblocks_dependents(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="Auth", description="", agent_role="coder", dependencies=[t1])
    await store.complete_task(t1, result="Done", tokens_used=100, cost=0.01)
    ready = await store.get_ready_tasks(goal_id)
    assert len(ready) == 1
    assert ready[0]["id"] == t2

@pytest.mark.asyncio
async def test_fail_task(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    await store.fail_task(t1, error="Timeout", retry=True)
    task = await store.get_task(t1)
    assert task["status"] == TaskStatus.PENDING.value
    assert task["retry_count"] == 1

@pytest.mark.asyncio
async def test_goal_progress(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="A", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="B", description="", agent_role="coder", dependencies=[])
    await store.complete_task(t1, result="Done", tokens_used=50, cost=0.005)
    progress = await store.get_goal_progress(goal_id)
    assert progress["total"] == 2
    assert progress["completed"] == 1
    assert progress["percent"] == 50.0
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_db_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'airees.db'`

**Step 3: Write the implementation**

```python
"""SQLite-backed goal and task store for the Airees brain."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import aiosqlite


class GoalStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    ITERATING = "iterating"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GoalStore:
    db_path: Path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    iteration INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL REFERENCES goals(id),
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    agent_role TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    dependencies TEXT NOT NULL DEFAULT '[]',
                    result TEXT,
                    error TEXT,
                    model_used TEXT,
                    tokens_used INTEGER NOT NULL DEFAULT 0,
                    cost REAL NOT NULL DEFAULT 0.0,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL REFERENCES goals(id),
                    iteration INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    async def create_goal(self, description: str, metadata: dict | None = None) -> str:
        goal_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO goals (id, description, metadata) VALUES (?, ?, ?)",
                (goal_id, description, json.dumps(metadata or {})),
            )
            await db.commit()
        return goal_id

    async def get_goal(self, goal_id: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_goal_status(self, goal_id: str, status: GoalStatus) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE goals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status.value, goal_id),
            )
            await db.commit()

    async def increment_iteration(self, goal_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE goals SET iteration = iteration + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (goal_id,),
            )
            await db.commit()
            cursor = await db.execute("SELECT iteration FROM goals WHERE id = ?", (goal_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def create_task(
        self,
        goal_id: str,
        title: str,
        description: str,
        agent_role: str,
        dependencies: list[str],
        max_retries: int = 3,
    ) -> str:
        task_id = str(uuid.uuid4())
        status = TaskStatus.BLOCKED.value if dependencies else TaskStatus.PENDING.value
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO tasks
                   (id, goal_id, title, description, agent_role, status, dependencies, max_retries)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, goal_id, title, description, agent_role, status, json.dumps(dependencies), max_retries),
            )
            await db.commit()
        return task_id

    async def get_task(self, task_id: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            result = dict(row)
            result["dependencies"] = json.loads(result["dependencies"])
            return result

    async def get_ready_tasks(self, goal_id: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE goal_id = ? AND status = ?",
                (goal_id, TaskStatus.PENDING.value),
            )
            rows = await cursor.fetchall()
            return [dict(r) | {"dependencies": json.loads(r["dependencies"])} for r in rows]

    async def get_all_tasks(self, goal_id: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE goal_id = ? ORDER BY created_at",
                (goal_id,),
            )
            rows = await cursor.fetchall()
            return [dict(r) | {"dependencies": json.loads(r["dependencies"])} for r in rows]

    async def complete_task(self, task_id: str, result: str, tokens_used: int, cost: float) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE tasks SET status = ?, result = ?, tokens_used = ?, cost = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (TaskStatus.COMPLETED.value, result, tokens_used, cost, task_id),
            )
            # Get goal_id and unblock dependents
            cursor = await db.execute("SELECT goal_id FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            if row:
                goal_id = row[0]
                # Find blocked tasks and check if their deps are all completed
                blocked = await db.execute(
                    "SELECT id, dependencies FROM tasks WHERE goal_id = ? AND status = ?",
                    (goal_id, TaskStatus.BLOCKED.value),
                )
                blocked_rows = await blocked.fetchall()
                for brow in blocked_rows:
                    deps = json.loads(brow[1])
                    # Check if all dependencies are completed
                    all_done = True
                    for dep_id in deps:
                        dep_cursor = await db.execute(
                            "SELECT status FROM tasks WHERE id = ?", (dep_id,)
                        )
                        dep_row = await dep_cursor.fetchone()
                        if dep_row is None or dep_row[0] != TaskStatus.COMPLETED.value:
                            all_done = False
                            break
                    if all_done:
                        await db.execute(
                            "UPDATE tasks SET status = ? WHERE id = ?",
                            (TaskStatus.PENDING.value, brow[0]),
                        )
            await db.commit()

    async def fail_task(self, task_id: str, error: str, retry: bool = False) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            if retry:
                await db.execute(
                    """UPDATE tasks SET status = ?, error = ?, retry_count = retry_count + 1,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (TaskStatus.PENDING.value, error, task_id),
                )
            else:
                await db.execute(
                    """UPDATE tasks SET status = ?, error = ?,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (TaskStatus.FAILED.value, error, task_id),
                )
            await db.commit()

    async def get_goal_progress(self, goal_id: str) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM tasks WHERE goal_id = ?", (goal_id,)
            )
            total = (await cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM tasks WHERE goal_id = ? AND status = ?",
                (goal_id, TaskStatus.COMPLETED.value),
            )
            completed = (await cursor.fetchone())[0]
            percent = (completed / total * 100) if total > 0 else 0.0
            return {"total": total, "completed": completed, "percent": percent}

    async def log_decision(self, goal_id: str, iteration: int, action: str, reasoning: str) -> str:
        dec_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO decisions (id, goal_id, iteration, action, reasoning) VALUES (?, ?, ?, ?, ?)",
                (dec_id, goal_id, iteration, action, reasoning),
            )
            await db.commit()
        return dec_id
```

`airees/packages/core/airees/db/__init__.py`:
```python
"""Database layer for Airees brain state persistence."""
from airees.db.schema import GoalStore, GoalStatus, TaskStatus

__all__ = ["GoalStore", "GoalStatus", "TaskStatus"]
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_db_schema.py -v`
Expected: 7 tests PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/db/ airees/packages/core/tests/test_db_schema.py
git commit -m "feat: add SQLite-backed GoalStore with task graph and dependency tracking"
```

---

### Task 2: SOUL.md — Initial File and Loader

**Files:**
- Create: `airees/packages/core/airees/soul.py`
- Create: `airees/data/SOUL.md`
- Test: `airees/packages/core/tests/test_soul.py`

**Context:** SOUL.md defines Airees' identity. The loader reads it and makes it available to the Brain's system prompt. Keep it simple for Phase 1 — just load and return the content. Evolution/reflection comes in Phase 2.

**Step 1: Write the failing tests**

```python
"""Tests for SOUL.md loader."""
import pytest
from pathlib import Path
from airees.soul import load_soul, Soul

@pytest.fixture
def soul_path(tmp_path):
    content = """---
format: soul/v1
name: Airees
version: 1
---

# Core Purpose
I am Airees — an autonomous orchestrator.

# Values
1. Autonomy
2. Quality over speed
"""
    path = tmp_path / "SOUL.md"
    path.write_text(content, encoding="utf-8")
    return path

def test_load_soul(soul_path):
    soul = load_soul(soul_path)
    assert soul.name == "Airees"
    assert soul.version == 1
    assert "autonomous orchestrator" in soul.content

def test_load_soul_missing_file(tmp_path):
    soul = load_soul(tmp_path / "missing.md")
    assert soul.name == "Airees"
    assert soul.version == 0
    assert "autonomous orchestrator" in soul.content  # returns default

def test_soul_to_prompt(soul_path):
    soul = load_soul(soul_path)
    prompt = soul.to_prompt()
    assert isinstance(prompt, str)
    assert "Airees" in prompt
    assert len(prompt) > 50
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_soul.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'airees.soul'`

**Step 3: Write the implementation**

```python
"""SOUL.md loader — reads and parses Airees' identity file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOUL = """---
format: soul/v1
name: Airees
version: 0
---

# Core Purpose

I am Airees — an autonomous orchestrator that takes goals and delivers
completed projects. I think like a COO: I plan, delegate, evaluate,
iterate, and learn. I don't ask my boss what to do next. I figure it
out and report back with results.

# Values

1. Autonomy — I work independently. Only contact user to deliver results.
2. Quality over speed — I iterate until work is genuinely good.
3. Learn from everything — Every goal teaches me something.
4. Efficiency — Cheapest model that gets the job done.

# Personality

Direct, confident, proactive. Lead with accomplishments, then explain
what I learned and optimized.

# Boundaries

- Never expose API keys or secrets
- Never push to production without testing
- Never delete user data without explicit instruction
- Never spend on paid services without user-configured API keys
"""


@dataclass(frozen=True)
class Soul:
    name: str
    version: int
    content: str
    raw: str

    def to_prompt(self) -> str:
        return (
            f"You are {self.name}.\n\n"
            f"{self.content}\n\n"
            "Follow your values and boundaries in all decisions."
        )


def load_soul(path: Path) -> Soul:
    if not path.exists():
        return _parse_soul(DEFAULT_SOUL)
    raw = path.read_text(encoding="utf-8")
    return _parse_soul(raw)


def _parse_soul(raw: str) -> Soul:
    name = "Airees"
    version = 0
    content = raw

    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            content = parts[2].strip()
            for line in frontmatter.strip().splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("version:"):
                    try:
                        version = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass

    return Soul(name=name, version=version, content=content, raw=raw)
```

Also create the default SOUL.md file:

`airees/data/SOUL.md`: (copy of DEFAULT_SOUL constant with version: 1)

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_soul.py -v`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/soul.py airees/packages/core/tests/test_soul.py airees/data/SOUL.md
git commit -m "feat: add SOUL.md loader with default identity and frontmatter parsing"
```

---

### Task 3: Brain Agent — System Prompt Builder and Tools

**Files:**
- Create: `airees/packages/core/airees/brain/__init__.py`
- Create: `airees/packages/core/airees/brain/prompt.py`
- Create: `airees/packages/core/airees/brain/tools.py`
- Test: `airees/packages/core/tests/test_brain_prompt.py`
- Test: `airees/packages/core/tests/test_brain_tools.py`

**Context:** The Brain's system prompt is assembled from SOUL.md + goal context + coordinator report. Brain tools are the structured outputs it can produce (create_plan, evaluate_result, adapt_plan, message_user). In Phase 1, tools return structured JSON that the Coordinator parses — they don't call external APIs.

**Step 1: Write the failing tests**

`test_brain_prompt.py`:
```python
"""Tests for Brain system prompt builder."""
import pytest
from airees.brain.prompt import build_brain_prompt
from airees.soul import Soul

def test_build_prompt_includes_soul():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app")
    assert "Airees" in prompt
    assert "COO" in prompt
    assert "Build a todo app" in prompt

def test_build_prompt_includes_coordinator_report():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    report = "3/5 tasks complete. Auth task failed twice."
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app", coordinator_report=report)
    assert "Auth task failed" in prompt

def test_build_prompt_includes_skill():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    skill = "# Todo App Pipeline\n1. Scaffold\n2. Database\n3. Auth"
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app", active_skill=skill)
    assert "Todo App Pipeline" in prompt

def test_build_prompt_includes_iteration():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app", iteration=3)
    assert "iteration 3" in prompt.lower() or "Iteration: 3" in prompt
```

`test_brain_tools.py`:
```python
"""Tests for Brain tool definitions."""
from airees.brain.tools import get_brain_tools

def test_brain_tools_exist():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "create_plan" in names
    assert "evaluate_result" in names
    assert "adapt_plan" in names
    assert "message_user" in names

def test_create_plan_schema():
    tools = get_brain_tools()
    create_plan = next(t for t in tools if t.name == "create_plan")
    props = create_plan.input_schema["properties"]
    assert "tasks" in props
    assert "model_recommendations" in props

def test_evaluate_result_schema():
    tools = get_brain_tools()
    evaluate = next(t for t in tools if t.name == "evaluate_result")
    props = evaluate.input_schema["properties"]
    assert "satisfied" in props
    assert "reasoning" in props
    assert "action" in props
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_brain_prompt.py tests/test_brain_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'airees.brain'`

**Step 3: Write the implementation**

`brain/__init__.py`:
```python
"""Airees Brain — the strategic orchestrator."""
```

`brain/prompt.py`:
```python
"""Build the Brain's system prompt from components."""
from __future__ import annotations

from airees.soul import Soul


def build_brain_prompt(
    *,
    soul: Soul,
    goal: str,
    coordinator_report: str | None = None,
    active_skill: str | None = None,
    iteration: int = 0,
) -> str:
    sections = [soul.to_prompt()]

    sections.append(
        "\n## Your Role\n\n"
        "You are the strategic brain of a multi-agent system. You PLAN, EVALUATE, "
        "and DECIDE. You never do the work yourself — you delegate everything to "
        "workers via the Coordinator.\n\n"
        "When planning, break the goal into a task graph with dependencies. "
        "Assign agent roles and recommend models for each task.\n\n"
        "When evaluating, think holistically: does the whole thing work together? "
        "Is there a better approach? Did workers discover anything useful?\n\n"
        "You have three actions after evaluation:\n"
        "- **satisfied**: goal is complete, report to user\n"
        "- **adapt**: modify the task graph (add/remove/change tasks)\n"
        "- **rewrite**: scrap parts of the plan based on what was learned\n"
    )

    sections.append(f"\n## Current Goal\n\n{goal}\n")

    if iteration > 0:
        sections.append(f"\n## Iteration: {iteration}\n\nThis goal has been through {iteration} iteration(s). Review what changed and why.\n")

    if active_skill:
        sections.append(f"\n## Relevant Skill (Proven Pipeline)\n\n{active_skill}\n")

    if coordinator_report:
        sections.append(f"\n## Coordinator Report\n\n{coordinator_report}\n")

    sections.append(
        "\n## Output Rules\n\n"
        "- Use the `create_plan` tool to output your task graph\n"
        "- Use the `evaluate_result` tool to judge completed work\n"
        "- Use the `adapt_plan` tool to modify the plan mid-execution\n"
        "- Use the `message_user` tool ONLY to report final results or ask for input you genuinely need\n"
        "- NEVER output a plain text plan — always use tools\n"
    )

    return "\n".join(sections)
```

`brain/tools.py`:
```python
"""Tool definitions for the Brain agent."""
from __future__ import annotations

from airees.tools.registry import ToolDefinition


def get_brain_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="create_plan",
            description="Create a task graph to achieve the goal. Each task has a title, description, agent role, dependencies, and model recommendation.",
            input_schema={
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "agent_role": {"type": "string"},
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Indices of tasks this depends on (0-based)"
                                },
                                "model": {"type": "string", "description": "Recommended model ID"},
                            },
                            "required": ["title", "description", "agent_role"],
                        },
                    },
                    "model_recommendations": {
                        "type": "object",
                        "description": "Default model for each agent role",
                        "additionalProperties": {"type": "string"},
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Brief explanation of the overall approach",
                    },
                },
                "required": ["tasks"],
            },
        ),
        ToolDefinition(
            name="evaluate_result",
            description="Evaluate the completed work from the Coordinator. Decide whether to accept, adapt, or rewrite.",
            input_schema={
                "type": "object",
                "properties": {
                    "satisfied": {"type": "boolean", "description": "Is the work satisfactory?"},
                    "reasoning": {"type": "string", "description": "Why you made this decision"},
                    "action": {
                        "type": "string",
                        "enum": ["satisfied", "adapt", "rewrite"],
                        "description": "What to do next"
                    },
                    "changes": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Task changes if action is adapt/rewrite"
                    },
                },
                "required": ["satisfied", "reasoning", "action"],
            },
        ),
        ToolDefinition(
            name="adapt_plan",
            description="Modify the existing task graph. Add, remove, or change tasks.",
            input_schema={
                "type": "object",
                "properties": {
                    "add_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "agent_role": {"type": "string"},
                                "dependencies": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["title", "description", "agent_role"],
                        },
                    },
                    "remove_task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "reasoning": {"type": "string"},
                },
                "required": ["reasoning"],
            },
        ),
        ToolDefinition(
            name="message_user",
            description="Send a message to the user. Use ONLY for final results or when genuinely stuck.",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message to send"},
                    "type": {
                        "type": "string",
                        "enum": ["result", "update", "question"],
                    },
                },
                "required": ["message", "type"],
            },
        ),
    ]
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_brain_prompt.py tests/test_brain_tools.py -v`
Expected: 7 tests PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/brain/ airees/packages/core/tests/test_brain_prompt.py airees/packages/core/tests/test_brain_tools.py
git commit -m "feat: add Brain system prompt builder and tool definitions"
```

---

### Task 4: Brain State Machine

**Files:**
- Create: `airees/packages/core/airees/brain/state_machine.py`
- Test: `airees/packages/core/tests/test_brain_state.py`

**Context:** The Brain operates as a state machine: idle → planning → delegating → waiting → evaluating → (adapting|completing). State transitions are validated and persisted to the GoalStore.

**Step 1: Write the failing tests**

```python
"""Tests for Brain state machine."""
import pytest
from airees.brain.state_machine import BrainState, BrainStateMachine

def test_initial_state():
    sm = BrainStateMachine()
    assert sm.state == BrainState.IDLE

def test_valid_transition_idle_to_planning():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    assert sm.state == BrainState.PLANNING

def test_valid_transition_planning_to_delegating():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    assert sm.state == BrainState.DELEGATING

def test_invalid_transition_raises():
    sm = BrainStateMachine()
    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition(BrainState.EVALUATING)

def test_full_happy_path():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    sm.transition(BrainState.WAITING)
    sm.transition(BrainState.EVALUATING)
    sm.transition(BrainState.COMPLETING)
    sm.transition(BrainState.IDLE)
    assert sm.state == BrainState.IDLE

def test_iteration_path():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    sm.transition(BrainState.WAITING)
    sm.transition(BrainState.EVALUATING)
    sm.transition(BrainState.ADAPTING)
    sm.transition(BrainState.DELEGATING)
    assert sm.state == BrainState.DELEGATING

def test_transition_history():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    assert len(sm.history) == 2
    assert sm.history[0] == (BrainState.IDLE, BrainState.PLANNING)
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_brain_state.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
"""Brain state machine — controls the orchestrator lifecycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BrainState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    DELEGATING = "delegating"
    WAITING = "waiting"
    EVALUATING = "evaluating"
    ADAPTING = "adapting"
    COMPLETING = "completing"


VALID_TRANSITIONS: dict[BrainState, set[BrainState]] = {
    BrainState.IDLE: {BrainState.PLANNING},
    BrainState.PLANNING: {BrainState.DELEGATING},
    BrainState.DELEGATING: {BrainState.WAITING},
    BrainState.WAITING: {BrainState.EVALUATING},
    BrainState.EVALUATING: {BrainState.ADAPTING, BrainState.COMPLETING},
    BrainState.ADAPTING: {BrainState.DELEGATING},
    BrainState.COMPLETING: {BrainState.IDLE},
}


@dataclass
class BrainStateMachine:
    state: BrainState = BrainState.IDLE
    history: list[tuple[BrainState, BrainState]] = field(default_factory=list)

    def transition(self, new_state: BrainState) -> None:
        valid = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in valid:
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {new_state.value}. "
                f"Valid targets: {[s.value for s in valid]}"
            )
        self.history.append((self.state, new_state))
        self.state = new_state

    def can_transition(self, new_state: BrainState) -> bool:
        return new_state in VALID_TRANSITIONS.get(self.state, set())
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_brain_state.py -v`
Expected: 7 tests PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/brain/state_machine.py airees/packages/core/tests/test_brain_state.py
git commit -m "feat: add Brain state machine with validated transitions and history"
```

---

### Task 5: Coordinator — Task Executor with Worker Lifecycle

**Files:**
- Create: `airees/packages/core/airees/coordinator/__init__.py`
- Create: `airees/packages/core/airees/coordinator/executor.py`
- Create: `airees/packages/core/airees/coordinator/worker_builder.py`
- Test: `airees/packages/core/tests/test_coordinator.py`
- Test: `airees/packages/core/tests/test_worker_builder.py`

**Context:** The Coordinator takes a goal_id, reads its task graph from the GoalStore, finds ready tasks, builds workers, executes them, collects results, and either continues or escalates to Brain. The worker_builder selects a model and assembles the worker's system prompt.

**Step 1: Write the failing tests**

`test_worker_builder.py`:
```python
"""Tests for worker builder — model selection and prompt assembly."""
import pytest
from airees.coordinator.worker_builder import build_worker_prompt, select_model

def test_select_model_for_code_task():
    model = select_model(agent_role="coder", recommended=None)
    assert "haiku" in model.lower() or "free" in model.lower()

def test_select_model_uses_recommendation():
    model = select_model(agent_role="coder", recommended="openrouter/meta-llama/llama-3.3-70b-instruct:free")
    assert "llama" in model.lower()

def test_select_model_for_research():
    model = select_model(agent_role="researcher", recommended=None)
    assert model  # returns a non-empty string

def test_build_worker_prompt():
    prompt = build_worker_prompt(
        task_title="Scaffold project",
        task_description="Create a Next.js project with TypeScript and Tailwind",
        agent_role="coder",
    )
    assert "Scaffold project" in prompt
    assert "Next.js" in prompt
    assert "coder" in prompt.lower() or "code" in prompt.lower()

def test_build_worker_prompt_with_skill():
    prompt = build_worker_prompt(
        task_title="Add auth",
        task_description="Integrate Clerk authentication",
        agent_role="coder",
        skill_content="## Auth Pattern\nUse Clerk for auth.",
    )
    assert "Clerk" in prompt
    assert "Auth Pattern" in prompt

def test_build_worker_prompt_with_previous_output():
    prompt = build_worker_prompt(
        task_title="Add API routes",
        task_description="Build REST endpoints",
        agent_role="coder",
        previous_output="Project scaffolded at /app with Next.js 15",
    )
    assert "scaffolded" in prompt
```

`test_coordinator.py`:
```python
"""Tests for Coordinator executor."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from airees.coordinator.executor import Coordinator
from airees.db.schema import GoalStore

@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s

@pytest.mark.asyncio
async def test_coordinator_finds_ready_tasks(store):
    goal_id = await store.create_goal(description="Build app")
    await store.create_task(goal_id=goal_id, title="Scaffold", description="Setup", agent_role="coder", dependencies=[])
    coord = Coordinator(store=store, runner=AsyncMock())
    ready = await coord.get_next_tasks(goal_id)
    assert len(ready) == 1

@pytest.mark.asyncio
async def test_coordinator_respects_dependencies(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="A", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="B", description="", agent_role="coder", dependencies=[t1])
    coord = Coordinator(store=store, runner=AsyncMock())
    ready = await coord.get_next_tasks(goal_id)
    assert len(ready) == 1
    assert ready[0]["title"] == "A"

@pytest.mark.asyncio
async def test_coordinator_detects_all_complete(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="A", description="", agent_role="coder", dependencies=[])
    await store.complete_task(t1, result="Done", tokens_used=100, cost=0.01)
    coord = Coordinator(store=store, runner=AsyncMock())
    assert await coord.is_goal_complete(goal_id)

@pytest.mark.asyncio
async def test_coordinator_builds_report(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="Setup", agent_role="coder", dependencies=[])
    await store.complete_task(t1, result="Project created at /app", tokens_used=100, cost=0.01)
    coord = Coordinator(store=store, runner=AsyncMock())
    report = await coord.build_report(goal_id)
    assert "Scaffold" in report
    assert "Project created" in report
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_coordinator.py tests/test_worker_builder.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

`coordinator/__init__.py`:
```python
"""Coordinator — the execution manager for Airees."""
```

`coordinator/worker_builder.py`:
```python
"""Build worker sub-agents with appropriate models and prompts."""
from __future__ import annotations

MODEL_DEFAULTS: dict[str, str] = {
    "researcher": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "coder": "anthropic/claude-haiku-4-5",
    "reviewer": "anthropic/claude-haiku-4-5",
    "writer": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "tester": "anthropic/claude-haiku-4-5",
    "security": "anthropic/claude-sonnet-4-6",
    "architect": "anthropic/claude-sonnet-4-6",
}

ESCALATION_MODELS: dict[str, str] = {
    "researcher": "anthropic/claude-haiku-4-5",
    "coder": "anthropic/claude-sonnet-4-6",
    "reviewer": "anthropic/claude-sonnet-4-6",
    "writer": "anthropic/claude-haiku-4-5",
    "tester": "anthropic/claude-sonnet-4-6",
    "security": "anthropic/claude-opus-4-6",
    "architect": "anthropic/claude-opus-4-6",
}


def select_model(agent_role: str, recommended: str | None = None, escalate: bool = False) -> str:
    if recommended and not escalate:
        return recommended
    if escalate:
        return ESCALATION_MODELS.get(agent_role, "anthropic/claude-sonnet-4-6")
    return MODEL_DEFAULTS.get(agent_role, "anthropic/claude-haiku-4-5")


def build_worker_prompt(
    *,
    task_title: str,
    task_description: str,
    agent_role: str,
    skill_content: str | None = None,
    previous_output: str | None = None,
) -> str:
    sections = [
        f"You are a specialist {agent_role} agent. Complete the following task thoroughly.",
        f"\n## Task: {task_title}\n\n{task_description}",
    ]

    if previous_output:
        sections.append(f"\n## Context From Previous Task\n\n{previous_output}")

    if skill_content:
        sections.append(f"\n## Relevant Skill Reference\n\n{skill_content}")

    sections.append(
        "\n## Output Requirements\n\n"
        "Return your work product clearly. Include:\n"
        "- The actual output (code, text, analysis, etc.)\n"
        "- A confidence score (0-10) for your work quality\n"
        "- Any discoveries or unexpected findings\n"
    )

    return "\n".join(sections)
```

`coordinator/executor.py`:
```python
"""Coordinator executor — manages task graph execution and worker lifecycle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from airees.db.schema import GoalStore, TaskStatus


@dataclass
class Coordinator:
    store: GoalStore
    runner: Any  # Runner instance, typed as Any to avoid circular imports

    async def get_next_tasks(self, goal_id: str) -> list[dict]:
        return await self.store.get_ready_tasks(goal_id)

    async def is_goal_complete(self, goal_id: str) -> bool:
        tasks = await self.store.get_all_tasks(goal_id)
        if not tasks:
            return False
        return all(t["status"] == TaskStatus.COMPLETED.value for t in tasks)

    async def has_failures(self, goal_id: str) -> bool:
        tasks = await self.store.get_all_tasks(goal_id)
        return any(t["status"] == TaskStatus.FAILED.value for t in tasks)

    async def build_report(self, goal_id: str) -> str:
        tasks = await self.store.get_all_tasks(goal_id)
        progress = await self.store.get_goal_progress(goal_id)
        lines = [
            f"## Progress: {progress['completed']}/{progress['total']} tasks ({progress['percent']:.0f}%)\n",
        ]
        total_tokens = 0
        total_cost = 0.0
        for t in tasks:
            status_icon = "done" if t["status"] == "completed" else t["status"]
            lines.append(f"- [{status_icon}] {t['title']}")
            if t.get("result"):
                summary = t["result"][:200]
                lines.append(f"  Result: {summary}")
            if t.get("error"):
                lines.append(f"  Error: {t['error']}")
            total_tokens += t.get("tokens_used", 0)
            total_cost += t.get("cost", 0.0)

        lines.append(f"\nTotal tokens: {total_tokens}")
        lines.append(f"Total cost: ${total_cost:.4f}")
        return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_coordinator.py tests/test_worker_builder.py -v`
Expected: 10 tests PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/coordinator/ airees/packages/core/tests/test_coordinator.py airees/packages/core/tests/test_worker_builder.py
git commit -m "feat: add Coordinator executor and worker builder with model selection"
```

---

### Task 6: Brain Orchestrator — The Main Loop

**Files:**
- Create: `airees/packages/core/airees/brain/orchestrator.py`
- Test: `airees/packages/core/tests/test_brain_orchestrator.py`

**Context:** This is the core loop that ties Brain + Coordinator + Workers together. It receives a goal, activates Brain for planning, hands to Coordinator for execution, then activates Brain again for evaluation. This is the end-to-end integration.

**Step 1: Write the failing tests**

```python
"""Tests for the Brain orchestrator — the main execution loop."""
import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus

@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s

@pytest.fixture
def mock_router():
    router = AsyncMock()
    return router

@pytest.fixture
def event_bus():
    return EventBus()

@pytest.mark.asyncio
async def test_orchestrator_creates_goal(store, mock_router, event_bus, tmp_path):
    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
    )
    goal_id = await orch.submit_goal("Build a todo app")
    goal = await store.get_goal(goal_id)
    assert goal is not None
    assert goal["description"] == "Build a todo app"

@pytest.mark.asyncio
async def test_orchestrator_planning_creates_tasks(store, mock_router, event_bus, tmp_path):
    # Mock Brain's LLM response with a create_plan tool call
    plan_response = MagicMock()
    plan_response.stop_reason = "tool_use"
    plan_response.usage = MagicMock(input_tokens=100, output_tokens=200)
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tool_1"
    tool_block.name = "create_plan"
    tool_block.input = {
        "tasks": [
            {"title": "Scaffold", "description": "Setup project", "agent_role": "coder", "dependencies": []},
            {"title": "Add features", "description": "Core logic", "agent_role": "coder", "dependencies": [0]},
        ],
        "strategy": "Simple two-step build",
    }
    plan_response.content = [tool_block]

    # Second call: Brain confirms (end_turn)
    confirm_response = MagicMock()
    confirm_response.stop_reason = "end_turn"
    confirm_response.usage = MagicMock(input_tokens=50, output_tokens=50)
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Plan created."
    confirm_response.content = [text_block]

    mock_router.create_message = AsyncMock(side_effect=[plan_response, confirm_response])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
    )
    goal_id = await orch.submit_goal("Build a todo app")
    await orch.plan(goal_id)

    tasks = await store.get_all_tasks(goal_id)
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Scaffold"

@pytest.mark.asyncio
async def test_orchestrator_state_transitions(store, mock_router, event_bus, tmp_path):
    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
    )
    from airees.brain.state_machine import BrainState
    assert orch.state_machine.state == BrainState.IDLE

    goal_id = await orch.submit_goal("Test")
    assert orch.state_machine.state == BrainState.IDLE  # still idle until plan() called
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/core && python -m pytest tests/test_brain_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
"""Brain Orchestrator — the main loop tying Brain + Coordinator + Workers."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from airees.brain.prompt import build_brain_prompt
from airees.brain.state_machine import BrainState, BrainStateMachine
from airees.brain.tools import get_brain_tools
from airees.coordinator.executor import Coordinator
from airees.coordinator.worker_builder import build_worker_prompt, select_model
from airees.db.schema import GoalStore, GoalStatus, TaskStatus
from airees.events import Event, EventBus, EventType
from airees.router.types import ModelConfig
from airees.soul import Soul, load_soul
from airees.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class BrainOrchestrator:
    store: GoalStore
    brain_model: str
    router: Any  # ModelRouter
    event_bus: EventBus
    soul_path: Path = Path("data/SOUL.md")
    state_machine: BrainStateMachine = field(default_factory=BrainStateMachine)

    async def submit_goal(self, description: str) -> str:
        goal_id = await self.store.create_goal(description=description)
        await self.event_bus.emit_async(Event(
            event_type=EventType.RUN_START,
            agent_name="airees-brain",
            data={"goal_id": goal_id, "description": description},
        ))
        return goal_id

    async def plan(self, goal_id: str) -> list[dict]:
        self.state_machine.transition(BrainState.PLANNING)
        await self.store.update_goal_status(goal_id, GoalStatus.PLANNING)

        goal = await self.store.get_goal(goal_id)
        soul = load_soul(self.soul_path)
        prompt = build_brain_prompt(soul=soul, goal=goal["description"])

        brain_tools = get_brain_tools()
        registry = ToolRegistry()
        for t in brain_tools:
            registry.register(t)

        tools_formatted = registry.to_anthropic_format([t.name for t in brain_tools])
        model = ModelConfig(model_id=self.brain_model)

        response = await self.router.create_message(
            model=model,
            system=prompt,
            messages=[{"role": "user", "content": f"Plan this goal: {goal['description']}"}],
            tools=tools_formatted,
        )

        tasks_created = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "create_plan":
                plan_data = block.input
                task_id_map: dict[int, str] = {}

                for i, task_spec in enumerate(plan_data.get("tasks", [])):
                    dep_indices = task_spec.get("dependencies", [])
                    dep_ids = [task_id_map[d] for d in dep_indices if d in task_id_map]

                    task_id = await self.store.create_task(
                        goal_id=goal_id,
                        title=task_spec["title"],
                        description=task_spec.get("description", ""),
                        agent_role=task_spec.get("agent_role", "coder"),
                        dependencies=dep_ids,
                    )
                    task_id_map[i] = task_id
                    tasks_created.append({"id": task_id, **task_spec})

                await self.store.log_decision(
                    goal_id=goal_id,
                    iteration=0,
                    action="create_plan",
                    reasoning=plan_data.get("strategy", "Initial plan created"),
                )

        self.state_machine.transition(BrainState.DELEGATING)
        await self.store.update_goal_status(goal_id, GoalStatus.EXECUTING)
        return tasks_created

    async def execute_goal(self, goal_id: str) -> str:
        """Full autonomous loop: plan → execute → evaluate → iterate."""
        # Plan
        await self.plan(goal_id)

        coordinator = Coordinator(store=self.store, runner=self.router)

        # Execution loop
        self.state_machine.transition(BrainState.WAITING)
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            # Execute all ready tasks via Coordinator
            while True:
                ready = await coordinator.get_next_tasks(goal_id)
                if not ready:
                    break

                for task in ready:
                    await self._execute_worker(goal_id, task)

                # Check if complete or stuck
                if await coordinator.is_goal_complete(goal_id):
                    break
                if await coordinator.has_failures(goal_id):
                    break

            # Evaluate
            self.state_machine.transition(BrainState.EVALUATING)
            report = await coordinator.build_report(goal_id)
            action = await self._evaluate(goal_id, report, iteration)

            if action == "satisfied":
                self.state_machine.transition(BrainState.COMPLETING)
                await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
                self.state_machine.transition(BrainState.IDLE)
                return report

            # Iterate
            iteration += 1
            await self.store.increment_iteration(goal_id)
            self.state_machine.transition(BrainState.ADAPTING)
            self.state_machine.transition(BrainState.DELEGATING)
            self.state_machine.transition(BrainState.WAITING)

        # Max iterations reached
        await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
        report = await coordinator.build_report(goal_id)
        if self.state_machine.state != BrainState.IDLE:
            # Force back to idle
            self.state_machine.state = BrainState.IDLE
        return report

    async def _execute_worker(self, goal_id: str, task: dict) -> None:
        worker_prompt = build_worker_prompt(
            task_title=task["title"],
            task_description=task["description"],
            agent_role=task["agent_role"],
        )
        model_id = select_model(agent_role=task["agent_role"])
        model = ModelConfig(model_id=model_id)

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_START,
            agent_name=f"worker:{task['title']}",
            data={"task_id": task["id"], "model": model_id},
        ))

        try:
            response = await self.router.create_message(
                model=model,
                system=worker_prompt,
                messages=[{"role": "user", "content": task["description"]}],
            )

            output = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    output += block.text

            tokens = response.usage.input_tokens + response.usage.output_tokens
            cost = tokens * 0.000001  # rough estimate

            await self.store.complete_task(
                task["id"],
                result=output,
                tokens_used=tokens,
                cost=cost,
            )

            await self.event_bus.emit_async(Event(
                event_type=EventType.AGENT_COMPLETE,
                agent_name=f"worker:{task['title']}",
                data={"task_id": task["id"], "tokens": tokens},
            ))

        except Exception as e:
            logger.exception("Worker failed: %s", task["title"])
            retry = task.get("retry_count", 0) < task.get("max_retries", 3)
            await self.store.fail_task(task["id"], error=str(e), retry=retry)

    async def _evaluate(self, goal_id: str, report: str, iteration: int) -> str:
        soul = load_soul(self.soul_path)
        goal = await self.store.get_goal(goal_id)
        prompt = build_brain_prompt(
            soul=soul,
            goal=goal["description"],
            coordinator_report=report,
            iteration=iteration,
        )

        brain_tools = get_brain_tools()
        registry = ToolRegistry()
        for t in brain_tools:
            registry.register(t)
        tools_formatted = registry.to_anthropic_format([t.name for t in brain_tools])
        model = ModelConfig(model_id=self.brain_model)

        response = await self.router.create_message(
            model=model,
            system=prompt,
            messages=[{"role": "user", "content": "Evaluate the results and decide: satisfied, adapt, or rewrite."}],
            tools=tools_formatted,
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "evaluate_result":
                action = block.input.get("action", "satisfied")
                reasoning = block.input.get("reasoning", "")
                await self.store.log_decision(
                    goal_id=goal_id,
                    iteration=iteration,
                    action=action,
                    reasoning=reasoning,
                )
                return action

        return "satisfied"
```

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/core && python -m pytest tests/test_brain_orchestrator.py -v`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add airees/packages/core/airees/brain/orchestrator.py airees/packages/core/tests/test_brain_orchestrator.py
git commit -m "feat: add Brain orchestrator with plan-execute-evaluate loop"
```

---

### Task 7: Server Routes — Goal Submission and Status

**Files:**
- Create: `airees/packages/server/airees_server/routes/goals.py`
- Modify: `airees/packages/server/airees_server/app.py`
- Test: `airees/packages/server/tests/test_goal_routes.py`

**Context:** Wire the Brain orchestrator to the FastAPI server so goals can be submitted via REST API and streamed via WebSocket. The chat interface will submit goals through this endpoint.

**Step 1: Write the failing tests**

```python
"""Tests for goal submission API routes."""
import pytest
from httpx import AsyncClient, ASGITransport
from airees_server.app import create_app

@pytest.fixture
def app(tmp_path):
    return create_app(data_dir=tmp_path / "data")

@pytest.mark.asyncio
async def test_submit_goal(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/goals", json={"description": "Build a todo app"})
        assert resp.status_code == 201
        data = resp.json()
        assert "goal_id" in data

@pytest.mark.asyncio
async def test_get_goal(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/goals", json={"description": "Build a todo app"})
        goal_id = create_resp.json()["goal_id"]
        resp = await client.get(f"/api/goals/{goal_id}")
        assert resp.status_code == 200
        assert resp.json()["description"] == "Build a todo app"

@pytest.mark.asyncio
async def test_list_goals(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/goals", json={"description": "Goal 1"})
        await client.post("/api/goals", json={"description": "Goal 2"})
        resp = await client.get("/api/goals")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

@pytest.mark.asyncio
async def test_goal_progress(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/goals", json={"description": "Build app"})
        goal_id = create_resp.json()["goal_id"]
        resp = await client.get(f"/api/goals/{goal_id}/progress")
        assert resp.status_code == 200
        assert "total" in resp.json()
```

**Step 2: Run tests to verify they fail**

Run: `cd airees/packages/server && python -m pytest tests/test_goal_routes.py -v`
Expected: FAIL

**Step 3: Write the implementation**

`routes/goals.py`:
```python
"""Goal submission and tracking API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airees.db.schema import GoalStore


router = APIRouter(prefix="/goals", tags=["goals"])


class GoalCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=32_000)


def _get_store(request: Request) -> GoalStore:
    return request.app.state.goal_store


@router.post("", status_code=201)
async def submit_goal(body: GoalCreate, request: Request):
    store = _get_store(request)
    goal_id = await store.create_goal(description=body.description)
    return {"goal_id": goal_id, "status": "pending"}


@router.get("")
async def list_goals(request: Request):
    store = _get_store(request)
    # Simple list from DB
    import aiosqlite
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM goals ORDER BY created_at DESC LIMIT 50")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/{goal_id}")
async def get_goal(goal_id: str, request: Request):
    store = _get_store(request)
    goal = await store.get_goal(goal_id)
    if not goal:
        raise HTTPException(404, f"Goal not found: {goal_id}")
    return goal


@router.get("/{goal_id}/progress")
async def get_progress(goal_id: str, request: Request):
    store = _get_store(request)
    goal = await store.get_goal(goal_id)
    if not goal:
        raise HTTPException(404, f"Goal not found: {goal_id}")
    return await store.get_goal_progress(goal_id)


@router.get("/{goal_id}/tasks")
async def get_tasks(goal_id: str, request: Request):
    store = _get_store(request)
    return await store.get_all_tasks(goal_id)
```

Modify `app.py` to add the goals router and initialize GoalStore:

Add to imports: `from airees.db.schema import GoalStore`
Add to imports: `from airees_server.routes.goals import router as goals_router`

Add after `app.state.agents = {}`:
```python
    goal_store = GoalStore(db_path=data_dir / "airees.db")
    import asyncio
    asyncio.get_event_loop().run_until_complete(goal_store.initialize())
    app.state.goal_store = goal_store
```

Add router: `app.include_router(goals_router, prefix="/api")`

**Step 4: Run tests to verify they pass**

Run: `cd airees/packages/server && python -m pytest tests/test_goal_routes.py -v`
Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add airees/packages/server/airees_server/routes/goals.py airees/packages/server/airees_server/app.py airees/packages/server/tests/test_goal_routes.py
git commit -m "feat: add goal submission and tracking API routes"
```

---

### Task 8: Update Core Exports and Integration Test

**Files:**
- Modify: `airees/packages/core/airees/__init__.py`
- Create: `airees/packages/core/tests/test_brain_integration.py`

**Context:** Export all new modules from the core package. Write an integration test that exercises the full Brain → Coordinator → Worker loop with mocked LLM responses.

**Step 1: Write the integration test**

```python
"""Integration test — full Brain orchestrator loop with mocked LLM."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus


def _make_tool_response(tool_name: str, tool_input: dict):
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


def _make_text_response(text: str):
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
async def test_full_brain_loop(store, tmp_path):
    mock_router = AsyncMock()

    # Call 1: Brain plans (create_plan tool call)
    plan_response = _make_tool_response("create_plan", {
        "tasks": [
            {"title": "Research", "description": "Research the topic", "agent_role": "researcher", "dependencies": []},
            {"title": "Build", "description": "Build the thing", "agent_role": "coder", "dependencies": [0]},
        ],
        "strategy": "Research then build",
    })

    # Call 2: Brain confirms plan
    plan_confirm = _make_text_response("Plan created successfully.")

    # Call 3: Worker 1 (Research) executes
    worker1_response = _make_text_response("Research complete. Found best libraries.")

    # Call 4: Worker 2 (Build) executes
    worker2_response = _make_text_response("Built the project. All tests pass.")

    # Call 5: Brain evaluates (evaluate_result tool call)
    eval_response = _make_tool_response("evaluate_result", {
        "satisfied": True,
        "reasoning": "All tasks complete, quality is good.",
        "action": "satisfied",
    })

    # Call 6: Brain confirms evaluation
    eval_confirm = _make_text_response("Goal complete.")

    mock_router.create_message = AsyncMock(side_effect=[
        plan_response, plan_confirm,
        worker1_response,
        worker2_response,
        eval_response, eval_confirm,
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
    )

    goal_id = await orch.submit_goal("Build a research tool")
    result = await orch.execute_goal(goal_id)

    # Verify goal completed
    goal = await store.get_goal(goal_id)
    assert goal["status"] == "completed"

    # Verify tasks were created and completed
    tasks = await store.get_all_tasks(goal_id)
    assert len(tasks) == 2
    assert all(t["status"] == "completed" for t in tasks)

    # Verify progress
    progress = await store.get_goal_progress(goal_id)
    assert progress["percent"] == 100.0
```

**Step 2: Run test to verify it fails**

Run: `cd airees/packages/core && python -m pytest tests/test_brain_integration.py -v`
Expected: FAIL (until all previous tasks are implemented)

**Step 3: Update core exports**

Add to `__init__.py`:
```python
from airees.brain.orchestrator import BrainOrchestrator
from airees.brain.state_machine import BrainState, BrainStateMachine
from airees.brain.prompt import build_brain_prompt
from airees.brain.tools import get_brain_tools
from airees.coordinator.executor import Coordinator
from airees.coordinator.worker_builder import build_worker_prompt, select_model
from airees.db.schema import GoalStore, GoalStatus, TaskStatus
from airees.soul import Soul, load_soul
```

And add all new names to `__all__`.

**Step 4: Run ALL tests**

Run: `cd airees/packages/core && python -m pytest tests/ -v`
Expected: All tests PASS (existing 111 + new ~38 = ~149 tests)

**Step 5: Commit**

```bash
git add airees/packages/core/airees/__init__.py airees/packages/core/tests/test_brain_integration.py
git commit -m "test: add full brain orchestrator integration test and update exports"
```

---

## Summary

| Task | What It Builds | Tests |
|------|---------------|-------|
| 1 | SQLite GoalStore with task graph + DAG dependencies | 7 |
| 2 | SOUL.md loader with frontmatter parsing | 3 |
| 3 | Brain system prompt builder + tool definitions | 7 |
| 4 | Brain state machine with validated transitions | 7 |
| 5 | Coordinator executor + worker builder + model selection | 10 |
| 6 | Brain orchestrator — the main plan-execute-evaluate loop | 3 |
| 7 | Server routes — goal submission and tracking API | 4 |
| 8 | Core exports + integration test | 1 |

**Total: 8 tasks, ~42 new tests, 8 commits**

**After Phase 1 you'll have:** A working brain that can receive a goal via API, plan it into a task graph, execute tasks via workers with model routing, evaluate results, and report back. The foundation for Phase 2 (heartbeat, skills, reflection, tool discovery, compression).
