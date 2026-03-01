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
    mock_tool_provider = MagicMock()
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
    """Workers without tools work as before -- single call, text response."""
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
    mock_tool_provider = MagicMock()
    mock_tool_provider.execute = AsyncMock(return_value='{"result": "data"}')
    mock_tool_provider.get_tools.return_value = []

    # Always returns tool_use -- should hit max_tool_rounds limit
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
