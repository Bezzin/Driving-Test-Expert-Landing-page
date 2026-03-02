"""Tests for the HeartbeatDaemon tiered monitoring system."""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from airees.heartbeat import HeartbeatDaemon
from airees.db.schema import GoalStore
from airees.events import EventBus, EventType
from airees.scheduler import Scheduler, SchedulerConfig


@pytest_asyncio.fixture
async def store(tmp_path):
    s = GoalStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.fixture
def scheduler():
    return Scheduler(config=SchedulerConfig(max_concurrent=5))


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.mark.asyncio
async def test_heartbeat_daemon_creates(store, scheduler, event_bus):
    """HeartbeatDaemon should be instantiable with required fields."""
    daemon = HeartbeatDaemon(store=store, scheduler=scheduler, event_bus=event_bus)
    assert daemon.store is store
    assert daemon.scheduler is scheduler


@pytest.mark.asyncio
async def test_check_goal_queue_healthy(store, scheduler, event_bus):
    """Goal queue check returns None when no pending goals or has capacity."""
    daemon = HeartbeatDaemon(store=store, scheduler=scheduler, event_bus=event_bus)
    result = await daemon._check_goal_queue()
    assert result is None


@pytest.mark.asyncio
async def test_check_stale_tasks_detects_stuck(store, scheduler, event_bus):
    """Stale task check should detect running tasks older than timeout."""
    goal_id = await store.create_goal(description="Test")
    task_id = await store.create_task(
        goal_id=goal_id, title="Stuck task", description="",
        agent_role="coder", dependencies=[],
    )
    import aiosqlite
    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "UPDATE tasks SET status = 'running', updated_at = datetime('now', '-1 hour') WHERE id = ?",
            (task_id,),
        )
        await db.commit()

    daemon = HeartbeatDaemon(
        store=store, scheduler=scheduler, event_bus=event_bus,
        stale_task_timeout_seconds=60,
    )
    result = await daemon._check_stale_tasks()
    assert result is not None
    assert "stale" in result.lower()


@pytest.mark.asyncio
async def test_failure_counter_resets_on_healthy(store, scheduler, event_bus):
    """Failure count should reset to 0 when check passes."""
    daemon = HeartbeatDaemon(store=store, scheduler=scheduler, event_bus=event_bus)
    daemon._failure_counts["goal_queue"] = 2
    await daemon._run_check("goal_queue", daemon._check_goal_queue)
    assert daemon._failure_counts.get("goal_queue", 0) == 0


@pytest.mark.asyncio
async def test_escalation_after_3_failures(store, scheduler, event_bus):
    """After 3 consecutive failures, HEARTBEAT_ESCALATE event should emit."""
    captured = []
    event_bus.subscribe_all(lambda e: captured.append(e))

    daemon = HeartbeatDaemon(store=store, scheduler=scheduler, event_bus=event_bus)
    daemon._failure_counts["test_check"] = 3

    await daemon._handle_anomaly("test_check", "Something failed")

    escalate_events = [e for e in captured if e.event_type == EventType.HEARTBEAT_ESCALATE]
    assert len(escalate_events) == 1
    assert "test_check" in escalate_events[0].data.get("check", "")


@pytest.mark.asyncio
async def test_anomaly_event_before_escalation(store, scheduler, event_bus):
    """Before reaching escalation threshold, HEARTBEAT_ANOMALY should emit."""
    captured = []
    event_bus.subscribe_all(lambda e: captured.append(e))

    daemon = HeartbeatDaemon(store=store, scheduler=scheduler, event_bus=event_bus)
    daemon._failure_counts["test_check"] = 1

    await daemon._handle_anomaly("test_check", "Minor issue")

    anomaly_events = [e for e in captured if e.event_type == EventType.HEARTBEAT_ANOMALY]
    assert len(anomaly_events) == 1


@pytest.mark.asyncio
async def test_run_forever_can_be_cancelled(store, scheduler, event_bus):
    """run_forever should exit cleanly on cancellation."""
    daemon = HeartbeatDaemon(store=store, scheduler=scheduler, event_bus=event_bus)
    task = asyncio.create_task(daemon.run_forever())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_stop_cancels_all_tasks(store, scheduler, event_bus):
    """stop() should cancel all running poll loops."""
    daemon = HeartbeatDaemon(store=store, scheduler=scheduler, event_bus=event_bus)
    task = asyncio.create_task(daemon.run_forever())
    await asyncio.sleep(0.05)
    await daemon.stop()
    # Give a moment for cancellation to propagate
    await asyncio.sleep(0.05)
    assert task.cancelled() or task.done()


def test_heartbeat_event_types_exist():
    """Verify heartbeat event types are defined."""
    assert EventType.HEARTBEAT_ANOMALY.value == "heartbeat.anomaly"
    assert EventType.HEARTBEAT_ESCALATE.value == "heartbeat.escalate"


def test_heartbeat_exported_from_package():
    """HeartbeatDaemon should be importable from airees."""
    from airees import HeartbeatDaemon as HD
    assert HD is not None
