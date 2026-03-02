"""End-to-end test: goal submit -> daemon pickup -> brain execute -> complete."""
import asyncio

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus
from airees.goal_daemon import GoalDaemon
from airees.scheduler import Scheduler, SchedulerConfig


def _make_text_response(text: str) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=50, output_tokens=100)
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


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


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_daemon_picks_up_and_executes_goal(store, tmp_path):
    """Full e2e: submit goal -> daemon polls -> brain executes -> completed."""
    mock_router = AsyncMock()

    # Call 1: Intent classification
    intent = _make_text_response("build")
    # Call 2: Plan
    plan = _make_tool_response("create_plan", {
        "tasks": [
            {
                "title": "Do it",
                "description": "Do the thing",
                "agent_role": "coder",
                "dependencies": [],
            },
        ],
        "strategy": "Simple",
    })
    # Call 3: Worker produces text output
    worker = _make_text_response("Done.")
    # Call 4: Quality gate score
    score = _make_text_response('{"score": 9, "feedback": "Good"}')
    # Call 5: Evaluation — satisfied
    eval_resp = _make_tool_response("evaluate_result", {
        "satisfied": True,
        "reasoning": "Complete.",
        "action": "satisfied",
    })

    mock_router.create_message = AsyncMock(side_effect=[
        intent, plan, worker, score, eval_resp,
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=EventBus(),
        soul_path=tmp_path / "SOUL.md",
    )

    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))
    daemon = GoalDaemon(
        orchestrator=orch,
        scheduler=scheduler,
        poll_interval=1,
        state_dir=tmp_path / "states",
    )

    # Submit a goal directly to the store (simulating CLI `goal submit`)
    goal_id = await store.create_goal(description="E2E test goal")

    # Run one poll cycle — daemon discovers the pending goal and submits it
    await daemon._poll_once()

    # The scheduler fires an asyncio.Task; give the event loop time to run it
    for _ in range(20):
        await asyncio.sleep(0.1)
        goal = await store.get_goal(goal_id)
        if goal["status"] == "completed":
            break

    # Verify goal completed
    goal = await store.get_goal(goal_id)
    assert goal["status"] == "completed"

    # Verify tasks created and completed
    tasks = await store.get_all_tasks(goal_id)
    assert len(tasks) == 1
    assert tasks[0]["status"] == "completed"
