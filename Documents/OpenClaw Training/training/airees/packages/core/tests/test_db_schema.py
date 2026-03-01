"""Tests for database schema initialization and CRUD operations."""
import pytest
import pytest_asyncio
from airees.db.schema import GoalStore, GoalStatus, TaskStatus


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_create_goal(store):
    goal_id = await store.create_goal(
        description="Build a todo app",
        metadata={"source": "chat"},
    )
    assert goal_id is not None
    goal = await store.get_goal(goal_id)
    assert goal["description"] == "Build a todo app"
    assert goal["status"] == GoalStatus.PENDING.value


@pytest.mark.asyncio
async def test_create_task(store):
    goal_id = await store.create_goal(description="Build app")
    task_id = await store.create_task(
        goal_id=goal_id,
        title="Scaffold project",
        description="Create Next.js project with TypeScript",
        agent_role="coder",
        dependencies=[],
    )
    task = await store.get_task(task_id)
    assert task["title"] == "Scaffold project"
    assert task["status"] == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_task_dependencies(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="Auth", description="Add auth", agent_role="coder", dependencies=[t1])
    task2 = await store.get_task(t2)
    assert t1 in task2["dependencies"]


@pytest.mark.asyncio
async def test_get_ready_tasks(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="Auth", description="", agent_role="coder", dependencies=[t1])
    ready = await store.get_ready_tasks(goal_id)
    assert len(ready) == 1
    assert ready[0]["id"] == t1


@pytest.mark.asyncio
async def test_complete_task_unblocks_dependents(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="Auth", description="", agent_role="coder", dependencies=[t1])
    await store.complete_task(t1, result="Done", tokens_used=100, cost=0.01)
    ready = await store.get_ready_tasks(goal_id)
    assert len(ready) == 1
    assert ready[0]["id"] == t2


@pytest.mark.asyncio
async def test_fail_task(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="Scaffold", description="", agent_role="coder", dependencies=[])
    await store.fail_task(t1, error="Timeout", retry=True)
    task = await store.get_task(t1)
    assert task["status"] == TaskStatus.PENDING.value
    assert task["retry_count"] == 1


@pytest.mark.asyncio
async def test_fail_task_exceeds_max_retries(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(
        goal_id=goal_id, title="Scaffold", description="",
        agent_role="coder", dependencies=[], max_retries=1,
    )
    # First retry: retry_count 0 < max_retries 1 -> PENDING, retry_count bumped to 1
    await store.fail_task(t1, error="Timeout", retry=True)
    task = await store.get_task(t1)
    assert task["status"] == TaskStatus.PENDING.value
    assert task["retry_count"] == 1
    # Second retry: retry_count 1 >= max_retries 1 -> FAILED
    await store.fail_task(t1, error="Timeout", retry=True)
    task = await store.get_task(t1)
    assert task["status"] == TaskStatus.FAILED.value
    assert task["retry_count"] == 1


@pytest.mark.asyncio
async def test_get_goal_deserializes_metadata(store):
    goal_id = await store.create_goal(
        description="Build app", metadata={"source": "chat", "priority": 1},
    )
    goal = await store.get_goal(goal_id)
    assert isinstance(goal["metadata"], dict)
    assert goal["metadata"]["source"] == "chat"
    assert goal["metadata"]["priority"] == 1


@pytest.mark.asyncio
async def test_goal_progress(store):
    goal_id = await store.create_goal(description="Build app")
    t1 = await store.create_task(goal_id=goal_id, title="A", description="", agent_role="coder", dependencies=[])
    t2 = await store.create_task(goal_id=goal_id, title="B", description="", agent_role="coder", dependencies=[])
    await store.complete_task(t1, result="Done", tokens_used=50, cost=0.005)
    progress = await store.get_goal_progress(goal_id)
    assert progress["total"] == 2
    assert progress["completed"] == 1
    assert progress["percent"] == 50.0
