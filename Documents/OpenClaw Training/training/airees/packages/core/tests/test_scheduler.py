"""Tests for the scheduler system."""
import asyncio

import pytest

from airees.scheduler import Scheduler, SchedulerConfig


@pytest.fixture
def config():
    return SchedulerConfig(interval_seconds=1, max_concurrent=2)


def test_scheduler_creation(config):
    scheduler = Scheduler(config=config)
    assert scheduler.config.interval_seconds == 1
    assert scheduler.config.max_concurrent == 2
    assert scheduler.active_count == 0


def test_scheduler_has_capacity(config):
    scheduler = Scheduler(config=config)
    assert scheduler.has_capacity is True


@pytest.mark.asyncio
async def test_scheduler_runs_work(config):
    results = []

    async def work_fn(project_id: str):
        results.append(project_id)

    scheduler = Scheduler(config=config)
    await scheduler.submit("proj-1", work_fn)
    await asyncio.sleep(0.1)
    assert "proj-1" in results


@pytest.mark.asyncio
async def test_scheduler_respects_capacity(config):
    started = []
    gate = asyncio.Event()

    async def slow_work(project_id: str):
        started.append(project_id)
        await gate.wait()

    scheduler = Scheduler(config=config)
    await scheduler.submit("a", slow_work)
    await scheduler.submit("b", slow_work)
    await asyncio.sleep(0.05)
    assert len(started) == 2
    assert scheduler.has_capacity is False

    await scheduler.submit("c", slow_work)
    await asyncio.sleep(0.05)
    assert "c" not in started

    gate.set()
    await asyncio.sleep(0.1)
    assert "c" in started
