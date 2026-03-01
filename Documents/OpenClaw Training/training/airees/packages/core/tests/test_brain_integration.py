"""Integration test — full Brain orchestrator loop with mocked LLM."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from airees.brain.orchestrator import BrainOrchestrator
from airees.brain.state_machine import BrainState
from airees.db.schema import GoalStore
from airees.events import EventBus


def _make_tool_response(tool_name: str, tool_input: dict):
    """Build a mock LLM response containing a single tool_use block."""
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
    """Build a mock LLM response containing a single text block."""
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
    """Exercise the complete Brain -> Coordinator -> Worker loop.

    The orchestrator makes exactly 4 calls to the router:
      1. plan()            — Brain creates task plan via create_plan tool
      2. _execute_worker   — Worker runs Research task (no deps)
      3. _execute_worker   — Worker runs Build task (depends on Research)
      4. _evaluate          — Brain evaluates via evaluate_result tool
    """
    mock_router = AsyncMock()

    # Call 1: Brain plans (create_plan tool call)
    plan_response = _make_tool_response("create_plan", {
        "tasks": [
            {
                "title": "Research",
                "description": "Research the topic",
                "agent_role": "researcher",
                "dependencies": [],
            },
            {
                "title": "Build",
                "description": "Build the thing",
                "agent_role": "coder",
                "dependencies": [0],
            },
        ],
        "strategy": "Research then build",
    })

    # Call 2: Worker 1 (Research) executes
    worker1_response = _make_text_response(
        "Research complete. Found best libraries."
    )

    # Call 3: Worker 2 (Build) executes
    worker2_response = _make_text_response(
        "Built the project. All tests pass."
    )

    # Call 4: Brain evaluates (evaluate_result tool call)
    eval_response = _make_tool_response("evaluate_result", {
        "satisfied": True,
        "reasoning": "All tasks complete, quality is good.",
        "action": "satisfied",
    })

    mock_router.create_message = AsyncMock(side_effect=[
        plan_response,
        worker1_response,
        worker2_response,
        eval_response,
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

    # Verify state machine returned to IDLE
    assert orch.state_machine.state == BrainState.IDLE

    # Verify the router was called exactly 4 times
    assert mock_router.create_message.call_count == 4

    # Verify report was returned (non-empty string)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_brain_loop_with_adapt_iteration(store, tmp_path):
    """Test the adapt loop: Brain evaluates, asks to adapt, then re-evaluates.

    Call flow:
      1. plan()            — Brain creates a single task
      2. _execute_worker   — Worker runs the task
      3. _evaluate (iter 0) — Brain says "adapt"
      4. _evaluate (iter 1) — Brain says "satisfied" (no new ready tasks)
    """
    mock_router = AsyncMock()

    plan_response = _make_tool_response("create_plan", {
        "tasks": [
            {
                "title": "Draft",
                "description": "Write first draft",
                "agent_role": "writer",
                "dependencies": [],
            },
        ],
        "strategy": "Single task approach",
    })

    worker_response = _make_text_response("Draft complete.")

    # First eval: adapt (iterate again)
    eval_adapt = _make_tool_response("evaluate_result", {
        "satisfied": False,
        "reasoning": "Needs revision.",
        "action": "adapt",
    })

    # Second eval: satisfied
    eval_satisfied = _make_tool_response("evaluate_result", {
        "satisfied": True,
        "reasoning": "Revision looks good.",
        "action": "satisfied",
    })

    mock_router.create_message = AsyncMock(side_effect=[
        plan_response,
        worker_response,
        eval_adapt,
        eval_satisfied,
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
    )

    goal_id = await orch.submit_goal("Write a report")
    result = await orch.execute_goal(goal_id)

    goal = await store.get_goal(goal_id)
    assert goal["status"] == "completed"
    assert mock_router.create_message.call_count == 4
    assert orch.state_machine.state == BrainState.IDLE


@pytest.mark.asyncio
async def test_events_emitted_during_loop(store, tmp_path):
    """Verify that RUN_START, AGENT_START, and AGENT_COMPLETE events fire."""
    mock_router = AsyncMock()
    event_bus = EventBus()
    captured_events = []

    async def capture(event):
        captured_events.append(event)

    event_bus.subscribe_all(capture)

    plan_response = _make_tool_response("create_plan", {
        "tasks": [
            {
                "title": "Only task",
                "description": "Do the thing",
                "agent_role": "coder",
                "dependencies": [],
            },
        ],
        "strategy": "Single task",
    })

    worker_response = _make_text_response("Done.")

    eval_response = _make_tool_response("evaluate_result", {
        "satisfied": True,
        "reasoning": "Looks good.",
        "action": "satisfied",
    })

    mock_router.create_message = AsyncMock(side_effect=[
        plan_response,
        worker_response,
        eval_response,
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
    )

    goal_id = await orch.submit_goal("Simple task")
    await orch.execute_goal(goal_id)

    event_types = [e.event_type.value for e in captured_events]
    assert "run.start" in event_types
    assert "agent.start" in event_types
    assert "agent.complete" in event_types
