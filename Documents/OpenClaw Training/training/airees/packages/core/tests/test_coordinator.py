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
