"""Tests for the Brain orchestrator — the main execution loop."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from airees.brain.orchestrator import BrainOrchestrator
from airees.brain.state_machine import BrainState
from airees.db.schema import GoalStore
from airees.events import EventBus
from airees.state import load_state


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


@pytest.mark.asyncio
async def test_submit_goal_creates_initial_state(store, mock_router, event_bus, tmp_path):
    """After submit_goal(), a state file must exist with current_phase == 'planning'."""
    state_dir = tmp_path / "states"

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
        state_dir=state_dir,
    )

    goal_id = await orch.submit_goal("Build a todo app")

    state_file = state_dir / f"{goal_id}.json"
    assert state_file.exists(), "State file should be created after submit_goal"

    loaded = load_state(state_file)
    assert loaded.project_id == goal_id
    assert loaded.current_phase == "planning"
    assert not loaded.is_complete


def _make_text_response(text: str) -> MagicMock:
    """Helper: build a mock LLM response containing a single text block."""
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.usage = MagicMock(input_tokens=10, output_tokens=20)
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp.content = [block]
    return resp


def _make_plan_response() -> MagicMock:
    """Helper: build a mock LLM response containing a create_plan tool_use."""
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.usage = MagicMock(input_tokens=100, output_tokens=200)
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tool_plan_1"
    tool_block.name = "create_plan"
    tool_block.input = {
        "tasks": [
            {
                "title": "Setup",
                "description": "Bootstrap project",
                "agent_role": "coder",
                "dependencies": [],
            },
        ],
        "strategy": "Single-step build",
    }
    resp.content = [tool_block]
    return resp


def _make_eval_response(action: str = "satisfied") -> MagicMock:
    """Helper: build a mock LLM response containing an evaluate_result tool_use."""
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.usage = MagicMock(input_tokens=50, output_tokens=80)
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tool_eval_1"
    tool_block.name = "evaluate_result"
    tool_block.input = {"action": action, "reasoning": "All tasks done"}
    resp.content = [tool_block]
    return resp


@pytest.mark.asyncio
async def test_execute_goal_completes_state(store, mock_router, event_bus, tmp_path):
    """After execute_goal(), the state file must show is_complete == True."""
    state_dir = tmp_path / "states"

    # Mock router responses in sequence:
    # 1) classify_intent     -> text "build"
    # 2) plan                -> create_plan tool_use
    # 3) worker execution    -> text output (end_turn)
    # 4) quality gate score  -> JSON with passing score
    # 5) evaluation          -> evaluate_result "satisfied"
    mock_router.create_message = AsyncMock(
        side_effect=[
            _make_text_response("build"),                          # classify_intent
            _make_plan_response(),                                  # plan
            _make_text_response("Done setup"),                     # worker execution
            _make_text_response('{"score": 9, "feedback": ""}'),   # quality gate
            _make_eval_response("satisfied"),                      # evaluation
        ]
    )

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=event_bus,
        soul_path=tmp_path / "SOUL.md",
        state_dir=state_dir,
    )

    goal_id = await orch.submit_goal("Build a todo app")
    await orch.execute_goal(goal_id)

    state_file = state_dir / f"{goal_id}.json"
    assert state_file.exists(), "State file should exist after execute_goal"

    loaded = load_state(state_file)
    assert loaded.is_complete, "All phases should be completed after successful execute_goal"
