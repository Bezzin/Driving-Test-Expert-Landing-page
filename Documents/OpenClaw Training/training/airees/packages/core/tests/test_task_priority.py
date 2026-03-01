"""Tests for task priority support."""
import pytest
import pytest_asyncio
from airees.db.schema import GoalStore


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_create_task_with_priority(store):
    goal_id = await store.create_goal(description="Test goal")
    task_id = await store.create_task(
        goal_id=goal_id, title="Important task", description="Do something",
        agent_role="coder", dependencies=[], priority=1,
    )
    task = await store.get_task(task_id)
    assert task["priority"] == 1


@pytest.mark.asyncio
async def test_create_task_default_priority(store):
    goal_id = await store.create_goal(description="Test goal")
    task_id = await store.create_task(
        goal_id=goal_id, title="Normal task", description="Regular work",
        agent_role="coder", dependencies=[],
    )
    task = await store.get_task(task_id)
    assert task["priority"] == 2


@pytest.mark.asyncio
async def test_ready_tasks_include_priority(store):
    goal_id = await store.create_goal(description="Test goal")
    await store.create_task(
        goal_id=goal_id, title="Low", description="", agent_role="coder",
        dependencies=[], priority=3,
    )
    await store.create_task(
        goal_id=goal_id, title="High", description="", agent_role="coder",
        dependencies=[], priority=1,
    )
    ready = await store.get_ready_tasks(goal_id)
    assert len(ready) == 2
    assert all("priority" in t for t in ready)
