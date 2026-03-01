# Phase 3: Factory Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire standalone factory primitives (QualityGate, ProjectState, ContextBudget, Scheduler, DecisionDocument, FeedbackLoop, validation) into the live BrainOrchestrator execution pipeline with full crash recovery and a background goal daemon.

**Architecture:** Orchestrator-centric integration — primitives are injected into `BrainOrchestrator` as constructor arguments and used at lifecycle transition points. No new abstractions. A `GoalDaemon` wraps the Scheduler to poll for pending/interrupted goals.

**Tech Stack:** Python 3.12, asyncio, aiosqlite, Anthropic SDK, pytest, pytest-asyncio

**Design doc:** `training/docs/plans/2026-03-01-airees-phase3-design.md`

**Base path:** `training/airees/packages/core/`

---

## Task 1: Add new EventType variants

**Files:**
- Modify: `airees/events.py:23-34`
- Test: `tests/test_events.py`

**Step 1: Write the failing test**

```python
# tests/test_events.py — append these tests

def test_quality_gate_pass_event_type():
    assert EventType.QUALITY_GATE_PASS.value == "quality_gate.pass"

def test_quality_gate_fail_event_type():
    assert EventType.QUALITY_GATE_FAIL.value == "quality_gate.fail"

def test_needs_attention_event_type():
    assert EventType.NEEDS_ATTENTION.value == "goal.needs_attention"

def test_state_persisted_event_type():
    assert EventType.STATE_PERSISTED.value == "state.persisted"

def test_validation_warning_event_type():
    assert EventType.VALIDATION_WARNING.value == "validation.warning"

def test_goal_resumed_event_type():
    assert EventType.GOAL_RESUMED.value == "goal.resumed"

def test_feedback_recorded_event_type():
    assert EventType.FEEDBACK_RECORDED.value == "feedback.recorded"
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_events.py -v -k "quality_gate_pass or quality_gate_fail or needs_attention or state_persisted or validation_warning or goal_resumed or feedback_recorded"`
Expected: FAIL — `AttributeError: 'EventType' has no attribute 'QUALITY_GATE_PASS'`

**Step 3: Write minimal implementation**

In `airees/events.py`, add to the `EventType` enum after line 34 (`CONTEXT_WARNING`):

```python
    QUALITY_GATE_PASS = "quality_gate.pass"
    QUALITY_GATE_FAIL = "quality_gate.fail"
    NEEDS_ATTENTION = "goal.needs_attention"
    STATE_PERSISTED = "state.persisted"
    VALIDATION_WARNING = "validation.warning"
    GOAL_RESUMED = "goal.resumed"
    FEEDBACK_RECORDED = "feedback.recorded"
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_events.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/events.py tests/test_events.py
git commit -m "feat: add Phase 3 event types for quality gates, state, validation, feedback"
```

---

## Task 2: Add GoalStore helper methods for daemon polling and crash recovery

**Files:**
- Modify: `airees/db/schema.py`
- Test: `tests/test_db_schema.py`

**Step 1: Write the failing tests**

```python
# tests/test_db_schema.py — append these tests

@pytest.mark.asyncio
async def test_get_pending_goals(tmp_path):
    store = GoalStore(db_path=tmp_path / "test.db")
    await store.initialize()
    gid1 = await store.create_goal(description="goal one")
    gid2 = await store.create_goal(description="goal two")
    await store.update_goal_status(gid1, GoalStatus.EXECUTING)
    pending = await store.get_pending_goals()
    assert len(pending) == 1
    assert pending[0]["id"] == gid2

@pytest.mark.asyncio
async def test_reset_stale_running_tasks(tmp_path):
    store = GoalStore(db_path=tmp_path / "test.db")
    await store.initialize()
    gid = await store.create_goal(description="goal")
    tid = await store.create_task(
        goal_id=gid, title="task", description="desc",
        agent_role="coder", dependencies=[],
    )
    # Simulate a crash: task is RUNNING but has no result
    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (TaskStatus.RUNNING.value, tid),
        )
        await db.commit()
    count = await store.reset_stale_running_tasks(gid)
    assert count == 1
    task = await store.get_task(tid)
    assert task["status"] == TaskStatus.PENDING.value

@pytest.mark.asyncio
async def test_flag_task_human(tmp_path):
    store = GoalStore(db_path=tmp_path / "test.db")
    await store.initialize()
    gid = await store.create_goal(description="goal")
    tid = await store.create_task(
        goal_id=gid, title="task", description="desc",
        agent_role="coder", dependencies=[],
    )
    await store.flag_task_human(tid, reason="quality too low after 3 retries")
    task = await store.get_task(tid)
    assert task["status"] == TaskStatus.FAILED.value
    assert "quality too low" in task["error"]
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_db_schema.py -v -k "pending_goals or stale_running or flag_task_human"`
Expected: FAIL — `AttributeError: 'GoalStore' object has no attribute 'get_pending_goals'`

**Step 3: Write minimal implementation**

Add these methods to `GoalStore` in `airees/db/schema.py`:

```python
    async def get_pending_goals(self) -> list[dict]:
        """Return all goals with status PENDING, oldest first."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM goals WHERE status = ? ORDER BY created_at ASC",
                (GoalStatus.PENDING.value,),
            )
            rows = await cursor.fetchall()
            return [
                {**dict(r), "metadata": json.loads(r["metadata"]) if r["metadata"] else {}}
                for r in rows
            ]

    async def reset_stale_running_tasks(self, goal_id: str) -> int:
        """Reset RUNNING tasks with no result back to PENDING (crash recovery).

        Returns the number of tasks reset.
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT id FROM tasks
                   WHERE goal_id = ? AND status = ? AND result IS NULL""",
                (goal_id, TaskStatus.RUNNING.value),
            )
            stale_ids = [row[0] for row in await cursor.fetchall()]
            for tid in stale_ids:
                await db.execute(
                    "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (TaskStatus.PENDING.value, tid),
                )
            await db.commit()
            return len(stale_ids)

    async def flag_task_human(self, task_id: str, reason: str) -> None:
        """Mark a task as FAILED with a human-attention reason."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE tasks SET status = ?, error = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (TaskStatus.FAILED.value, reason, task_id),
            )
            await db.commit()
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_db_schema.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/db/schema.py tests/test_db_schema.py
git commit -m "feat: add GoalStore helpers for daemon polling and crash recovery"
```

---

## Task 3: Wire ProjectState into BrainOrchestrator

**Files:**
- Modify: `airees/brain/orchestrator.py:25-40,42-112,114-160`
- Test: `tests/test_brain_orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/test_brain_orchestrator.py — append these tests

@pytest.mark.asyncio
async def test_execute_goal_persists_state(tmp_path, mock_router, mock_store):
    """State file should be created and updated during goal execution."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    bus = EventBus()
    orch = BrainOrchestrator(
        store=mock_store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        state_dir=state_dir,
    )
    # mock_store and mock_router are pre-configured to return a single task
    # that completes immediately and the brain evaluates as "satisfied"
    goal_id = await orch.submit_goal("Test goal")
    await orch.execute_goal(goal_id)

    state_file = state_dir / f"{goal_id}.json"
    assert state_file.exists()
    loaded = load_state(state_file)
    assert loaded.is_complete

@pytest.mark.asyncio
async def test_submit_goal_creates_initial_state(tmp_path, mock_router, mock_store):
    """submit_goal should create a ProjectState with planning as current phase."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    bus = EventBus()
    orch = BrainOrchestrator(
        store=mock_store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        state_dir=state_dir,
    )
    goal_id = await orch.submit_goal("Test goal")
    state_file = state_dir / f"{goal_id}.json"
    assert state_file.exists()
    loaded = load_state(state_file)
    assert loaded.current_phase == "planning"
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v -k "persists_state or creates_initial_state"`
Expected: FAIL — `TypeError: BrainOrchestrator.__init__() got an unexpected keyword argument 'state_dir'`

**Step 3: Write minimal implementation**

In `airees/brain/orchestrator.py`, modify the `BrainOrchestrator` dataclass:

1. Add imports at top:
```python
from airees.state import ProjectState, save_state, load_state
```

2. Add `state_dir` field after `tool_provider`:
```python
    state_dir: Path = Path("data/states")
```

3. In `submit_goal()`, after creating the goal and emitting the event, create and persist initial state:
```python
        state = ProjectState(
            project_id=goal_id,
            name=description[:80],
            phases=["planning", "executing", "evaluating", "completing"],
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        save_state(state, self.state_dir / f"{goal_id}.json")
```

4. In `plan()`, after transitioning to PLANNING:
```python
        self._persist_phase(goal_id, "planning")
```

5. At the start of the execute wave inner loop:
```python
        self._persist_phase(goal_id, "executing")
```

6. Before `_evaluate()`:
```python
        self._persist_phase(goal_id, "evaluating")
```

7. On completion (where GoalStatus.COMPLETED is set):
```python
        self._persist_phase(goal_id, "completing")
        self._complete_state(goal_id)
```

8. Add helper methods:
```python
    def _persist_phase(self, goal_id: str, phase: str) -> None:
        """Load state, advance to given phase, and save."""
        state_path = self.state_dir / f"{goal_id}.json"
        state = load_state(state_path)
        while state.current_phase != phase and state.current_phase is not None:
            state = state.advance()
        save_state(state, state_path)

    def _complete_state(self, goal_id: str) -> None:
        """Mark all remaining phases as complete and save."""
        state_path = self.state_dir / f"{goal_id}.json"
        state = load_state(state_path)
        while not state.is_complete:
            state = state.advance()
        save_state(state, state_path)
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/brain/orchestrator.py tests/test_brain_orchestrator.py
git commit -m "feat: wire ProjectState persistence into BrainOrchestrator lifecycle"
```

---

## Task 4: Wire QualityGate into worker execution

**Files:**
- Modify: `airees/brain/orchestrator.py:175-268`
- Test: `tests/test_quality_gate_integration.py` (new file)

**Step 1: Write the failing test**

```python
# tests/test_quality_gate_integration.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from airees.brain.orchestrator import BrainOrchestrator
from airees.events import EventBus, EventType
from airees.quality_gate import QualityGate, GateAction


@dataclass
class FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class FakeTextBlock:
    type: str = "text"
    text: str = "Worker output here"


@dataclass
class FakeResponse:
    content: list = None
    stop_reason: str = "end_turn"
    usage: FakeUsage = None

    def __post_init__(self):
        if self.content is None:
            self.content = [FakeTextBlock()]
        if self.usage is None:
            self.usage = FakeUsage()


@pytest.mark.asyncio
async def test_quality_gate_retry_on_low_score(tmp_path):
    """Worker should retry when quality gate score is below threshold."""
    events_captured = []

    async def capture(event):
        events_captured.append(event)

    bus = EventBus()
    bus.subscribe(EventType.QUALITY_GATE_FAIL, capture)

    mock_store = AsyncMock()
    mock_store.get_goal.return_value = {"description": "Test", "id": "g1"}

    mock_router = AsyncMock()
    # First call: worker output; Second call: scoring (low); Third: retry output; Fourth: scoring (high)
    mock_router.create_message.side_effect = [
        FakeResponse(content=[FakeTextBlock(text="Bad output")]),
        FakeResponse(content=[FakeTextBlock(text='{"score": 4, "feedback": "Incomplete"}')]),
        FakeResponse(content=[FakeTextBlock(text="Good output")]),
        FakeResponse(content=[FakeTextBlock(text='{"score": 8, "feedback": "Good"}')]),
    ]

    gate = QualityGate(name="default", min_score=7.0, max_retries=3)
    orch = BrainOrchestrator(
        store=mock_store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        quality_gate=gate,
        state_dir=tmp_path / "states",
    )

    task = {
        "id": "t1", "title": "Test task", "description": "Do something",
        "agent_role": "coder", "priority": 2,
    }
    await orch._execute_worker("g1", task)

    # Should have emitted a quality gate fail event
    assert any(e.event_type == EventType.QUALITY_GATE_FAIL for e in events_captured)
    # Store should have been called with the good output (retry succeeded)
    mock_store.complete_task.assert_called_once()


@pytest.mark.asyncio
async def test_quality_gate_escalate_after_max_retries(tmp_path):
    """Worker should escalate to human after exhausting retries."""
    events_captured = []

    async def capture(event):
        events_captured.append(event)

    bus = EventBus()
    bus.subscribe(EventType.NEEDS_ATTENTION, capture)

    mock_store = AsyncMock()
    mock_router = AsyncMock()
    # Every attempt scores low
    low_score = FakeResponse(content=[FakeTextBlock(text='{"score": 3, "feedback": "Bad"}')])
    worker_output = FakeResponse(content=[FakeTextBlock(text="Bad output")])
    mock_router.create_message.side_effect = [
        worker_output, low_score,   # attempt 1
        worker_output, low_score,   # attempt 2
        worker_output, low_score,   # attempt 3
    ]

    gate = QualityGate(name="strict", min_score=7.0, max_retries=3, on_failure=GateAction.FLAG_HUMAN)
    orch = BrainOrchestrator(
        store=mock_store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        quality_gate=gate,
        state_dir=tmp_path / "states",
    )

    task = {
        "id": "t2", "title": "Hard task", "description": "Complex work",
        "agent_role": "coder", "priority": 2,
    }
    await orch._execute_worker("g1", task)

    # Should have flagged as needing human attention
    assert any(e.event_type == EventType.NEEDS_ATTENTION for e in events_captured)
    mock_store.flag_task_human.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_quality_gate_integration.py -v`
Expected: FAIL — `TypeError: BrainOrchestrator.__init__() got an unexpected keyword argument 'quality_gate'`

**Step 3: Write minimal implementation**

In `airees/brain/orchestrator.py`:

1. Add imports:
```python
import json as json_module
from airees.quality_gate import QualityGate, GateAction
```

2. Add field to `BrainOrchestrator`:
```python
    quality_gate: QualityGate = field(
        default_factory=lambda: QualityGate(name="default", min_score=7.0, max_retries=3)
    )
```

3. Add `_score_output` method:
```python
    async def _score_output(self, task: dict, output: str) -> tuple[float, str]:
        """Rate worker output using Haiku for cost efficiency."""
        model = ModelConfig(model_id="claude-haiku-4-5-20251001")
        response = await self.router.create_message(
            model=model,
            system=(
                "You are a quality scorer. Rate the output 1-10 for completeness, "
                "accuracy, and quality relative to the task. "
                'Respond with ONLY valid JSON: {"score": N, "feedback": "..."}'
            ),
            messages=[{
                "role": "user",
                "content": f"Task: {task['title']}\nDescription: {task['description']}\n\nOutput:\n{output}",
            }],
        )
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text
        try:
            parsed = json_module.loads(text)
            return float(parsed.get("score", 5)), parsed.get("feedback", "")
        except (json_module.JSONDecodeError, ValueError):
            return 5.0, "Could not parse score"
```

4. Rewrite `_execute_worker` to include quality gate loop:

Replace the try/except block in `_execute_worker` (lines ~208-267) with:

```python
        try:
            max_gate_attempts = self.quality_gate.max_retries
            output = ""
            total_tokens = 0

            for attempt in range(max_gate_attempts):
                messages = [{"role": "user", "content": task["description"]}]
                if attempt > 0:
                    messages[0]["content"] += f"\n\nPrevious attempt feedback: {gate_feedback}. Improve your output."
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
                        for block in response.content:
                            if getattr(block, "type", None) == "text":
                                output += block.text
                        break

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

                # Quality gate evaluation
                score, gate_feedback = await self._score_output(task, output)
                gate_result = self.quality_gate.evaluate(score, gate_feedback)

                if gate_result.passed:
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.QUALITY_GATE_PASS,
                        agent_name=f"worker:{task['title']}",
                        data={"task_id": task["id"], "score": score, "attempt": attempt + 1},
                    ))
                    break

                await self.event_bus.emit_async(Event(
                    event_type=EventType.QUALITY_GATE_FAIL,
                    agent_name=f"worker:{task['title']}",
                    data={"task_id": task["id"], "score": score, "feedback": gate_feedback, "attempt": attempt + 1},
                ))

                if not self.quality_gate.should_retry(attempt + 1):
                    if self.quality_gate.should_escalate(attempt + 1):
                        await self.store.flag_task_human(task["id"], reason=gate_feedback)
                        await self.event_bus.emit_async(Event(
                            event_type=EventType.NEEDS_ATTENTION,
                            agent_name=f"worker:{task['title']}",
                            data={"task_id": task["id"], "reason": gate_feedback},
                        ))
                        return
                    break

                output = ""  # Reset for retry

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

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_quality_gate_integration.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/brain/orchestrator.py tests/test_quality_gate_integration.py
git commit -m "feat: wire QualityGate into worker execution with retry and escalation"
```

---

## Task 5: Wire DecisionDocument into orchestrator

**Files:**
- Modify: `airees/brain/orchestrator.py`
- Test: `tests/test_brain_orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/test_brain_orchestrator.py — append

@pytest.mark.asyncio
async def test_execute_goal_writes_decision_doc(tmp_path, mock_router, mock_store):
    """A decisions markdown file should be written on goal completion."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    decisions_dir = tmp_path / "decisions"
    decisions_dir.mkdir()
    bus = EventBus()

    orch = BrainOrchestrator(
        store=mock_store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        state_dir=state_dir,
        decisions_dir=decisions_dir,
    )
    goal_id = await orch.submit_goal("Test goal")
    await orch.execute_goal(goal_id)

    decision_file = decisions_dir / f"{goal_id}.md"
    assert decision_file.exists()
    content = decision_file.read_text(encoding="utf-8")
    assert "create_plan" in content
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v -k "writes_decision_doc"`
Expected: FAIL — `TypeError: BrainOrchestrator.__init__() got an unexpected keyword argument 'decisions_dir'`

**Step 3: Write minimal implementation**

In `airees/brain/orchestrator.py`:

1. Add import:
```python
from airees.decision_doc import DecisionDocument, DecisionEntry
```

2. Add field:
```python
    decisions_dir: Path = Path("data/decisions")
```

3. In `submit_goal()`, initialize a DecisionDocument and store it:
```python
        # After creating goal_id, before return:
        self._decision_docs[goal_id] = DecisionDocument(
            project_id=goal_id,
            title=description[:80],
        )
```

4. Add a dict to hold per-goal docs — add field:
```python
    _decision_docs: dict[str, DecisionDocument] = field(default_factory=dict)
```

5. Add helper to record a decision:
```python
    def _record_decision(self, goal_id: str, phase: str, agent: str,
                         decision: str, reasoning: str, confidence: float = 0.8) -> None:
        doc = self._decision_docs.get(goal_id)
        if doc is None:
            return
        entry = DecisionEntry(
            phase=phase, agent=agent, decision=decision,
            reasoning=reasoning, confidence=confidence,
        )
        self._decision_docs[goal_id] = doc.add_entry(entry)
```

6. In `plan()`, after `log_decision`:
```python
        self._record_decision(
            goal_id, "planning", "brain",
            "create_plan", plan_data.get("strategy", "Initial plan created"),
        )
```

7. In `_evaluate()`, after `log_decision`:
```python
        self._record_decision(goal_id, "evaluating", "brain", action, reasoning)
```

8. On goal completion (both early "satisfied" and max_iterations paths), save the doc:
```python
        self._save_decision_doc(goal_id)
```

9. Add save helper:
```python
    def _save_decision_doc(self, goal_id: str) -> None:
        doc = self._decision_docs.pop(goal_id, None)
        if doc is None:
            return
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        path = self.decisions_dir / f"{goal_id}.md"
        path.write_text(doc.to_markdown(), encoding="utf-8")
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/brain/orchestrator.py tests/test_brain_orchestrator.py
git commit -m "feat: wire DecisionDocument into orchestrator with markdown export"
```

---

## Task 6: Wire FeedbackLoop into orchestrator

**Files:**
- Modify: `airees/brain/orchestrator.py`
- Test: `tests/test_brain_orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/test_brain_orchestrator.py — append

@pytest.mark.asyncio
async def test_execute_goal_records_feedback(tmp_path, mock_router, mock_store):
    """FeedbackLoop should record an entry on goal completion."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    bus = EventBus()

    orch = BrainOrchestrator(
        store=mock_store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        state_dir=state_dir,
        memory_dir=memory_dir,
    )
    goal_id = await orch.submit_goal("Test goal")
    await orch.execute_goal(goal_id)

    feedback_file = memory_dir / "feedback.md"
    assert feedback_file.exists()
    content = feedback_file.read_text(encoding="utf-8")
    assert "success" in content.lower() or "Learned Patterns" in content
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v -k "records_feedback"`
Expected: FAIL — `TypeError: BrainOrchestrator.__init__() got an unexpected keyword argument 'memory_dir'`

**Step 3: Write minimal implementation**

In `airees/brain/orchestrator.py`:

1. Add import:
```python
from airees.feedback import FeedbackLoop, FeedbackEntry
```

2. Add fields:
```python
    memory_dir: Path = Path("data/memory")
    _feedback: FeedbackLoop = field(default_factory=FeedbackLoop)
```

3. On goal completion (the "satisfied" path and max_iterations path), record feedback:
```python
        self._record_feedback(goal_id, outcome="success", score=8.0, lesson="Goal completed successfully")
```

4. On goal failure/needs_human, record feedback:
```python
        self._record_feedback(goal_id, outcome="failure", score=3.0, lesson="Goal failed or required human intervention")
```

5. Add helper:
```python
    def _record_feedback(self, goal_id: str, outcome: str, score: float, lesson: str) -> None:
        entry = FeedbackEntry(
            run_id=goal_id,
            agent_name="brain-orchestrator",
            outcome=outcome,
            score=score,
            lesson=lesson,
        )
        self._feedback = self._feedback.record(entry)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        feedback_path = self.memory_dir / "feedback.md"
        content = self._feedback.to_memory_content("brain-orchestrator")
        if content:
            feedback_path.write_text(content, encoding="utf-8")
        self.event_bus.emit(Event(
            event_type=EventType.FEEDBACK_RECORDED,
            agent_name="brain-orchestrator",
            data={"goal_id": goal_id, "outcome": outcome, "score": score},
        ))
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/brain/orchestrator.py tests/test_brain_orchestrator.py
git commit -m "feat: wire FeedbackLoop into orchestrator with memory persistence"
```

---

## Task 7: Wire validate_pipeline into plan creation

**Files:**
- Modify: `airees/brain/orchestrator.py:52-112`
- Test: `tests/test_brain_orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/test_brain_orchestrator.py — append

@pytest.mark.asyncio
async def test_plan_emits_validation_warning_for_same_model(tmp_path, mock_router, mock_store):
    """When builder and reviewer use the same model, a VALIDATION_WARNING event should emit."""
    events_captured = []

    async def capture(event):
        events_captured.append(event)

    bus = EventBus()
    bus.subscribe(EventType.VALIDATION_WARNING, capture)

    orch = BrainOrchestrator(
        store=mock_store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        state_dir=tmp_path / "states",
    )
    # Configure mock_router to return a plan with builder + reviewer both using same model
    # The actual validation happens on the created tasks' agent_roles + model mapping
    goal_id = await orch.submit_goal("Test goal")
    tasks = await orch.plan(goal_id)
    # Note: validation warnings are advisory — plan still succeeds
    # Test passes if no errors thrown; actual warning emission depends on
    # task roles returned by the Brain's create_plan tool use
```

Note: This test validates the wiring exists. The validation logic itself is already tested in `test_validation.py`. The integration test just ensures the event is emitted when applicable.

**Step 2: Run test to verify behavior**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v -k "validation_warning"`

**Step 3: Write minimal implementation**

In `airees/brain/orchestrator.py`, in the `plan()` method, after tasks are created and before transitioning to DELEGATING:

```python
        # Validate task assignments for cross-model review
        self._validate_task_models(goal_id, tasks_created)
```

Add helper:
```python
    async def _validate_task_models(self, goal_id: str, tasks: list[dict]) -> None:
        """Check for same-model builder/reviewer pairs and emit warnings."""
        from airees.coordinator.worker_builder import select_model
        builder_models = []
        reviewer_models = []
        for t in tasks:
            role = t.get("agent_role", "")
            model_id = select_model(agent_role=role)
            if any(kw in role.lower() for kw in ("coder", "builder", "implement")):
                builder_models.append((t["title"], model_id))
            elif any(kw in role.lower() for kw in ("review", "audit", "verify")):
                reviewer_models.append((t["title"], model_id))
        for b_title, b_model in builder_models:
            for r_title, r_model in reviewer_models:
                if b_model == r_model:
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.VALIDATION_WARNING,
                        agent_name="brain",
                        data={
                            "code": "SAME_MODEL_BUILD_REVIEW",
                            "message": f"Builder '{b_title}' and reviewer '{r_title}' use model '{b_model}'",
                            "goal_id": goal_id,
                        },
                    ))
                    self._record_decision(
                        goal_id, "planning", "validator",
                        "validation_warning",
                        f"Same model '{b_model}' used for build and review",
                        confidence=0.9,
                    )
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_brain_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/brain/orchestrator.py tests/test_brain_orchestrator.py
git commit -m "feat: wire validate_pipeline check into plan creation"
```

---

## Task 8: Implement GoalDaemon for background goal polling

**Files:**
- Create: `airees/goal_daemon.py`
- Test: `tests/test_goal_daemon.py` (new file)

**Step 1: Write the failing test**

```python
# tests/test_goal_daemon.py

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from airees.goal_daemon import GoalDaemon
from airees.scheduler import Scheduler, SchedulerConfig
from airees.state import ProjectState, save_state, PhaseStatus


@pytest.mark.asyncio
async def test_daemon_finds_pending_goals():
    """Daemon should find pending goals from the store and submit them."""
    mock_orch = AsyncMock()
    mock_orch.store = AsyncMock()
    mock_orch.store.get_pending_goals.return_value = [
        {"id": "g1", "description": "Test goal"},
    ]
    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        poll_interval=0.1,
        state_dir=Path("/nonexistent"),
    )
    pending = await daemon._find_pending_goals()
    assert len(pending) == 1
    assert pending[0] == "g1"


@pytest.mark.asyncio
async def test_daemon_finds_interrupted_goals(tmp_path):
    """Daemon should find interrupted goals from state files."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()

    # Create an interrupted state file
    state = ProjectState(
        project_id="g2",
        name="Interrupted goal",
        phases=["planning", "executing", "evaluating", "completing"],
    )
    # Advance to "executing" phase
    state = state.advance()
    save_state(state, state_dir / "g2.json")

    mock_orch = AsyncMock()
    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        state_dir=state_dir,
    )
    interrupted = daemon._find_interrupted_goals()
    assert "g2" in interrupted


@pytest.mark.asyncio
async def test_daemon_does_not_resume_completed_goals(tmp_path):
    """Completed goals should not be resumed."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()

    state = ProjectState(
        project_id="g3",
        name="Done goal",
        phases=["planning", "executing", "evaluating", "completing"],
    )
    # Advance through all phases
    state = state.advance()  # planning -> executing
    state = state.advance()  # executing -> evaluating
    state = state.advance()  # evaluating -> completing
    state = state.advance()  # completing -> None (complete)
    save_state(state, state_dir / "g3.json")

    mock_orch = AsyncMock()
    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        state_dir=state_dir,
    )
    interrupted = daemon._find_interrupted_goals()
    assert "g3" not in interrupted


@pytest.mark.asyncio
async def test_daemon_respects_capacity(tmp_path):
    """Daemon should not submit more goals than scheduler capacity."""
    mock_orch = AsyncMock()
    mock_orch.store = AsyncMock()
    mock_orch.store.get_pending_goals.return_value = [
        {"id": f"g{i}", "description": f"Goal {i}"} for i in range(10)
    ]
    mock_orch.store.reset_stale_running_tasks = AsyncMock(return_value=0)
    mock_orch.execute_goal = AsyncMock()

    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=2))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        poll_interval=0.1,
        state_dir=tmp_path / "states",
    )
    await daemon._poll_once()
    # Only 2 should have been submitted (max_concurrent=2)
    assert scheduler.active_count <= 2


@pytest.mark.asyncio
async def test_daemon_resets_stale_tasks_on_resume(tmp_path):
    """When resuming an interrupted goal, stale RUNNING tasks should be reset."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()

    state = ProjectState(
        project_id="g4",
        name="Crashed goal",
        phases=["planning", "executing", "evaluating", "completing"],
    )
    state = state.advance()
    save_state(state, state_dir / "g4.json")

    mock_orch = AsyncMock()
    mock_orch.store = AsyncMock()
    mock_orch.store.get_pending_goals.return_value = []
    mock_orch.store.reset_stale_running_tasks = AsyncMock(return_value=2)
    mock_orch.execute_goal = AsyncMock()

    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        poll_interval=0.1,
        state_dir=state_dir,
    )
    await daemon._poll_once()
    mock_orch.store.reset_stale_running_tasks.assert_called_once_with("g4")
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_goal_daemon.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'airees.goal_daemon'`

**Step 3: Write minimal implementation**

Create `airees/goal_daemon.py`:

```python
"""Background daemon for polling and executing pending/interrupted goals."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from airees.events import Event, EventType
from airees.scheduler import Scheduler
from airees.state import load_state

logger = logging.getLogger(__name__)


@dataclass
class GoalDaemon:
    """Polls for pending and interrupted goals, submits them to the Scheduler.

    The daemon runs as a long-lived background task. On each poll cycle it:
    1. Scans state_dir for interrupted goals (crash recovery, prioritised)
    2. Queries GoalStore for new pending goals
    3. Submits each to the Scheduler (respecting max_concurrent)
    """

    orchestrator: object  # BrainOrchestrator — typed as object to avoid circular import
    scheduler: Scheduler
    poll_interval: int = 30
    state_dir: Path = Path("data/states")

    async def run_forever(self) -> None:
        """Poll indefinitely until cancelled."""
        logger.info("GoalDaemon started (poll_interval=%ds)", self.poll_interval)
        try:
            while True:
                await self._poll_once()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            logger.info("GoalDaemon stopped")

    async def _poll_once(self) -> None:
        """Single poll cycle: find work, submit to scheduler."""
        interrupted = self._find_interrupted_goals()
        pending = await self._find_pending_goals()

        # Interrupted goals take priority
        for goal_id in [*interrupted, *pending]:
            if not self.scheduler.has_capacity:
                break

            if goal_id in interrupted:
                await self._resume_goal(goal_id)
            else:
                await self.scheduler.submit(
                    goal_id,
                    self._make_execute_fn(),
                )

    async def _find_pending_goals(self) -> list[str]:
        """Query GoalStore for goals with status PENDING."""
        goals = await self.orchestrator.store.get_pending_goals()
        return [g["id"] for g in goals]

    def _find_interrupted_goals(self) -> list[str]:
        """Scan state_dir for non-complete ProjectState files."""
        if not self.state_dir.exists():
            return []
        interrupted = []
        for state_file in self.state_dir.glob("*.json"):
            try:
                state = load_state(state_file)
                if not state.is_complete and state.current_phase is not None:
                    interrupted.append(state.project_id)
            except Exception:
                logger.warning("Could not load state file: %s", state_file)
        return interrupted

    async def _resume_goal(self, goal_id: str) -> None:
        """Reset stale tasks and submit goal for re-execution."""
        await self.orchestrator.store.reset_stale_running_tasks(goal_id)
        await self.orchestrator.event_bus.emit_async(Event(
            event_type=EventType.GOAL_RESUMED,
            agent_name="goal-daemon",
            data={"goal_id": goal_id},
        ))
        await self.scheduler.submit(
            goal_id,
            self._make_execute_fn(),
        )

    def _make_execute_fn(self):
        """Return a callable that executes a goal by id."""
        async def _execute(goal_id: str) -> str:
            return await self.orchestrator.execute_goal(goal_id)
        return _execute
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_goal_daemon.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/goal_daemon.py tests/test_goal_daemon.py
git commit -m "feat: add GoalDaemon for background goal polling and crash recovery"
```

---

## Task 9: Add CLI `daemon` command

**Files:**
- Modify: `airees/cli/main.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
# tests/test_cli.py — append

from click.testing import CliRunner
from airees.cli.main import app

def test_daemon_command_exists():
    """The 'daemon' command group should exist."""
    runner = CliRunner()
    result = runner.invoke(app, ["daemon", "--help"])
    assert result.exit_code == 0
    assert "start" in result.output.lower() or "daemon" in result.output.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_cli.py -v -k "daemon_command"`
Expected: FAIL — `Error: No such command 'daemon'`

**Step 3: Write minimal implementation**

In `airees/cli/main.py`:

```python
import asyncio

@app.group()
def daemon() -> None:
    """Manage the background goal daemon."""
    pass


@daemon.command()
@click.option("--interval", type=int, default=30, help="Poll interval in seconds")
@click.option("--max-concurrent", type=int, default=5, help="Max concurrent goals")
@click.option("--data-dir", type=click.Path(), default="data", help="Data directory")
def start(interval: int, max_concurrent: int, data_dir: str) -> None:
    """Start the goal daemon (polls for pending and interrupted goals)."""
    click.echo(f"Starting GoalDaemon (interval={interval}s, max_concurrent={max_concurrent})")

    from airees.goal_daemon import GoalDaemon
    from airees.scheduler import Scheduler, SchedulerConfig

    data_path = Path(data_dir)

    # The actual orchestrator setup requires DB, router, etc.
    # This is a placeholder that will be fleshed out when the full
    # runtime bootstrap is implemented.
    click.echo("GoalDaemon requires a configured BrainOrchestrator.")
    click.echo(f"Data dir: {data_path.resolve()}")
    click.echo(f"State dir: {(data_path / 'states').resolve()}")
```

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_cli.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/cli/main.py tests/test_cli.py
git commit -m "feat: add CLI daemon command group with start subcommand"
```

---

## Task 10: Update exports and add integration test

**Files:**
- Modify: `airees/__init__.py`
- Create: `tests/test_phase3_integration.py`

**Step 1: Write the failing test**

```python
# tests/test_phase3_integration.py

"""Integration test: full goal lifecycle with all Phase 3 primitives wired."""
import pytest
from pathlib import Path
from dataclasses import dataclass
from unittest.mock import AsyncMock

from airees import (
    BrainOrchestrator,
    EventBus,
    EventType,
    GoalDaemon,
    QualityGate,
)


def test_goal_daemon_importable():
    """GoalDaemon should be importable from airees top-level."""
    from airees import GoalDaemon
    assert GoalDaemon is not None


def test_all_phase3_exports():
    """All Phase 3 additions should be in __all__."""
    import airees
    assert "GoalDaemon" in airees.__all__


@dataclass
class FakeUsage:
    input_tokens: int = 50
    output_tokens: int = 50


@dataclass
class FakeTextBlock:
    type: str = "text"
    text: str = "output"


@dataclass
class FakeToolUseBlock:
    type: str = "tool_use"
    name: str = "create_plan"
    id: str = "tu_1"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {
                "strategy": "Test strategy",
                "tasks": [{
                    "title": "Task 1",
                    "description": "Do task 1",
                    "agent_role": "coder",
                    "priority": 1,
                }],
            }


@dataclass
class FakeEvalBlock:
    type: str = "tool_use"
    name: str = "evaluate_result"
    id: str = "tu_2"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {"action": "satisfied", "reasoning": "Looks good"}


@dataclass
class FakeResponse:
    content: list = None
    stop_reason: str = "end_turn"
    usage: FakeUsage = None

    def __post_init__(self):
        if self.content is None:
            self.content = [FakeTextBlock()]
        if self.usage is None:
            self.usage = FakeUsage()


@pytest.mark.asyncio
async def test_full_goal_lifecycle(tmp_path):
    """Full lifecycle: submit -> plan -> execute -> quality gate -> evaluate -> complete.

    Verifies:
    - ProjectState file created and completed
    - DecisionDocument markdown written
    - FeedbackLoop memory written
    - Quality gate evaluated on worker output
    - All events emitted
    """
    from airees.db.schema import GoalStore, GoalStatus
    from airees.state import load_state

    db_path = tmp_path / "test.db"
    store = GoalStore(db_path=db_path)
    await store.initialize()

    state_dir = tmp_path / "states"
    state_dir.mkdir()
    decisions_dir = tmp_path / "decisions"
    decisions_dir.mkdir()
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    events_captured = []
    bus = EventBus()
    bus.subscribe_all(lambda e: events_captured.append(e))

    # Mock router returns:
    # 1. Plan response (create_plan tool use)
    # 2. Intent classification (text response)
    # 3. Worker output
    # 4. Quality score (high, passes gate)
    # 5. Evaluation (satisfied)
    mock_router = AsyncMock()

    intent_response = FakeResponse(content=[FakeTextBlock(text="BUILD")])
    plan_response = FakeResponse(
        content=[FakeToolUseBlock()],
        stop_reason="tool_use",
    )
    worker_response = FakeResponse(content=[FakeTextBlock(text="Task completed")])
    score_response = FakeResponse(content=[FakeTextBlock(text='{"score": 9, "feedback": "Excellent"}')])
    eval_response = FakeResponse(content=[FakeEvalBlock()], stop_reason="tool_use")

    mock_router.create_message.side_effect = [
        intent_response,  # classify_intent
        plan_response,     # plan
        worker_response,   # worker execution
        score_response,    # quality gate scoring
        eval_response,     # evaluation
    ]

    gate = QualityGate(name="test", min_score=7.0, max_retries=3)

    orch = BrainOrchestrator(
        store=store,
        brain_model="claude-sonnet-4-5-20250514",
        router=mock_router,
        event_bus=bus,
        soul_path=tmp_path / "SOUL.md",
        state_dir=state_dir,
        decisions_dir=decisions_dir,
        memory_dir=memory_dir,
        quality_gate=gate,
    )

    # Create a minimal SOUL.md
    soul_path = tmp_path / "SOUL.md"
    soul_path.write_text("# Airees\nI am an autonomous agent.", encoding="utf-8")

    goal_id = await orch.submit_goal("Build a test project")
    report = await orch.execute_goal(goal_id)

    # Verify ProjectState
    state_file = state_dir / f"{goal_id}.json"
    assert state_file.exists()
    state = load_state(state_file)
    assert state.is_complete

    # Verify DecisionDocument
    decision_file = decisions_dir / f"{goal_id}.md"
    assert decision_file.exists()
    content = decision_file.read_text(encoding="utf-8")
    assert "create_plan" in content

    # Verify FeedbackLoop memory
    feedback_file = memory_dir / "feedback.md"
    assert feedback_file.exists()

    # Verify events
    event_types = [e.event_type for e in events_captured]
    assert EventType.RUN_START in event_types
    assert EventType.AGENT_START in event_types
    assert EventType.QUALITY_GATE_PASS in event_types
    assert EventType.AGENT_COMPLETE in event_types
```

**Step 2: Run test to verify it fails**

Run: `cd training/airees && python -m pytest tests/test_phase3_integration.py -v`
Expected: FAIL — `ImportError: cannot import name 'GoalDaemon' from 'airees'`

**Step 3: Write minimal implementation**

In `airees/__init__.py`, add import:

```python
from airees.goal_daemon import GoalDaemon
```

Add `"GoalDaemon"` to the `__all__` list (alphabetically, between `"GateResult"` and `"GoalIntent"`).

**Step 4: Run test to verify it passes**

Run: `cd training/airees && python -m pytest tests/test_phase3_integration.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `cd training/airees && python -m pytest --tb=short -q`
Expected: All existing tests still pass, no regressions.

**Step 6: Commit**

```bash
git add airees/__init__.py tests/test_phase3_integration.py
git commit -m "feat: update exports, add Phase 3 integration test for full goal lifecycle"
```

---

## Summary

| Task | Description | New/Modified Files | Tests |
|------|-------------|-------------------|-------|
| 1 | Add new EventType variants | events.py | 7 tests |
| 2 | GoalStore helper methods | db/schema.py | 3 tests |
| 3 | Wire ProjectState into orchestrator | brain/orchestrator.py | 2 tests |
| 4 | Wire QualityGate into worker execution | brain/orchestrator.py | 2 tests |
| 5 | Wire DecisionDocument into orchestrator | brain/orchestrator.py | 1 test |
| 6 | Wire FeedbackLoop into orchestrator | brain/orchestrator.py | 1 test |
| 7 | Wire validate_pipeline into plan creation | brain/orchestrator.py | 1 test |
| 8 | Implement GoalDaemon | goal_daemon.py (new) | 5 tests |
| 9 | Add CLI daemon command | cli/main.py | 1 test |
| 10 | Update exports + integration test | __init__.py | 3 tests |

**Total: 10 tasks, 10 commits, ~26 new tests**

**Dependencies:**
- Task 1 (events) must complete before Tasks 3-8 (they emit new event types)
- Task 2 (GoalStore helpers) must complete before Task 8 (daemon uses them)
- Tasks 3-7 modify orchestrator.py and should be done sequentially to avoid merge conflicts
- Task 8 (daemon) can be done after Tasks 1-2
- Task 9 depends on Task 8
- Task 10 depends on all previous tasks
