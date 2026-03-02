"""Tests for ProactiveScheduler — cron-triggered goal execution."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from airees.gateway.cron import CronTrigger
from airees.gateway.proactive import ProactiveScheduler


@pytest.fixture
def scheduler() -> ProactiveScheduler:
    gateway = AsyncMock()
    gateway.handle_message = AsyncMock(return_value=None)
    return ProactiveScheduler(gateway=gateway)


def test_add_trigger(scheduler: ProactiveScheduler):
    trigger = CronTrigger(
        id="t1", expression="0 9 * * *",
        goal_text="morning check", channel="telegram", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)
    assert len(scheduler.triggers) == 1


def test_remove_trigger(scheduler: ProactiveScheduler):
    trigger = CronTrigger(
        id="t1", expression="0 9 * * *",
        goal_text="test", channel="cli", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)
    assert scheduler.remove_trigger("t1") is True
    assert len(scheduler.triggers) == 0


def test_remove_nonexistent(scheduler: ProactiveScheduler):
    assert scheduler.remove_trigger("nope") is False


@pytest.mark.asyncio
async def test_evaluate_fires_due_triggers(scheduler: ProactiveScheduler):
    trigger = CronTrigger(
        id="t1", expression="* * * * *",  # Every minute
        goal_text="do it", channel="cli", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)

    await scheduler.evaluate(datetime(2026, 3, 2, 9, 0))

    scheduler.gateway.handle_message.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_skips_running_trigger(scheduler: ProactiveScheduler):
    """If a trigger's previous execution is still running, skip it."""
    trigger = CronTrigger(
        id="t1", expression="* * * * *",
        goal_text="slow task", channel="cli", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)
    scheduler._running.add("t1")

    await scheduler.evaluate(datetime(2026, 3, 2, 9, 0))

    scheduler.gateway.handle_message.assert_not_called()
