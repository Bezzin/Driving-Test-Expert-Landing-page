"""Phase 2 integration test -- full loop with Tavily tools and intent classification."""
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
    """Full loop: intent classify -> plan -> parallel execute with tools -> evaluate."""
    mock_router = AsyncMock()
    mock_tool_provider = MagicMock()  # Note: MagicMock for sync get_tools
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

    # Call 5: Worker 2 (Summarize) -- no tools, just text
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
