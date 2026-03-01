"""Tests for the priority-aware worker pool."""
import asyncio
import pytest
from airees.concurrency import ConcurrencyManager
from airees.worker_pool import WorkerPool


@pytest.mark.asyncio
async def test_pool_executes_all_tasks():
    mgr = ConcurrencyManager(provider_limits={"test": 10}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    results = []

    async def executor(task):
        results.append(task["title"])
        return {"task_id": task["id"], "status": "completed"}

    pool.submit({"id": "1", "title": "A", "priority": 2, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "B", "priority": 2, "agent_role": "coder"})

    await pool.run_all(executor, provider="test", model="test-model")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pool_respects_priority_order():
    mgr = ConcurrencyManager(provider_limits={"test": 1}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    execution_order = []

    async def executor(task):
        execution_order.append(task["title"])
        await asyncio.sleep(0.01)
        return {"task_id": task["id"], "status": "completed"}

    # Submit low priority first, then high
    pool.submit({"id": "1", "title": "Low", "priority": 3, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "High", "priority": 1, "agent_role": "coder"})
    pool.submit({"id": "3", "title": "Critical", "priority": 0, "agent_role": "coder"})

    # With concurrency=1, tasks run sequentially in priority order
    await pool.run_all(executor, provider="test", model="test-model")
    assert execution_order == ["Critical", "High", "Low"]


@pytest.mark.asyncio
async def test_pool_returns_results():
    mgr = ConcurrencyManager(provider_limits={"test": 10}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    async def executor(task):
        return {"task_id": task["id"], "output": f"done-{task['title']}"}

    pool.submit({"id": "1", "title": "A", "priority": 2, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "B", "priority": 2, "agent_role": "coder"})

    results = await pool.run_all(executor, provider="test", model="test-model")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pool_captures_exceptions():
    mgr = ConcurrencyManager(provider_limits={"test": 10}, model_limits={})
    pool = WorkerPool(concurrency=mgr)

    async def executor(task):
        if task["title"] == "Fail":
            raise RuntimeError("Worker crashed")
        return {"task_id": task["id"], "status": "ok"}

    pool.submit({"id": "1", "title": "OK", "priority": 2, "agent_role": "coder"})
    pool.submit({"id": "2", "title": "Fail", "priority": 2, "agent_role": "coder"})

    results = await pool.run_all(executor, provider="test", model="test-model")
    # Both results returned; one is an exception
    assert len(results) == 2
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) == 1
