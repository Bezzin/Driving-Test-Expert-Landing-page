# tests/test_memory_sqlite.py
import pytest
import pytest_asyncio
from airees.memory.sqlite_store import SQLiteRunStore


@pytest_asyncio.fixture
async def store(tmp_path):
    s = SQLiteRunStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_save_and_get_run(store):
    await store.save_run(
        run_id="r1",
        agent_name="researcher",
        task="Find info",
        output="Here is info",
        turns=3,
        input_tokens=100,
        output_tokens=50,
    )
    run = await store.get_run("r1")
    assert run is not None
    assert run["agent_name"] == "researcher"
    assert run["output"] == "Here is info"
    assert run["turns"] == 3


@pytest.mark.asyncio
async def test_list_runs(store):
    await store.save_run("r1", "agent1", "task1", "out1", 1, 10, 5)
    await store.save_run("r2", "agent2", "task2", "out2", 2, 20, 10)
    runs = await store.list_runs()
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_get_nonexistent_run(store):
    run = await store.get_run("nonexistent")
    assert run is None


@pytest.mark.asyncio
async def test_list_runs_respects_limit(store):
    for i in range(10):
        await store.save_run(f"r{i}", "agent", f"task{i}", f"out{i}", 1, 10, 5)
    runs = await store.list_runs(limit=3)
    assert len(runs) == 3
