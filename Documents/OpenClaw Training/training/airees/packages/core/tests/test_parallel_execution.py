"""Tests for parallel worker execution in the orchestrator."""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus


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
