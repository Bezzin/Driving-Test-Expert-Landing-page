"""Tests for the Brain orchestrator — the main execution loop."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from airees.brain.orchestrator import BrainOrchestrator
from airees.brain.state_machine import BrainState
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

    mock_router.create_message = AsyncMock(return_value=plan_response)

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
    )
    goal_id = await orch.submit_goal("Build a todo app")
    created = await orch.plan(goal_id)

    tasks = await store.get_all_tasks(goal_id)
    assert len(tasks) == 2
    # Use the return value from plan() for ordered assertions since
    # get_all_tasks orders by created_at which has second-level resolution
    assert created[0]["title"] == "Scaffold"
    assert created[1]["title"] == "Add features"
    titles = {t["title"] for t in tasks}
    assert titles == {"Scaffold", "Add features"}


@pytest.mark.asyncio
async def test_orchestrator_state_transitions(store, mock_router, event_bus, tmp_path):
    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
    )
    assert orch.state_machine.state == BrainState.IDLE

    goal_id = await orch.submit_goal("Test")
    assert orch.state_machine.state == BrainState.IDLE  # still idle until plan() called
