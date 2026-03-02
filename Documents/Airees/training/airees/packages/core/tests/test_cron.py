"""Tests for CronTrigger data model and evaluation."""
from __future__ import annotations

from datetime import datetime

import pytest

from airees.gateway.cron import CronTrigger, is_due


def test_cron_trigger_creation():
    trigger = CronTrigger(
        id="t1",
        expression="0 9 * * *",
        goal_text="Check calendar",
        channel="telegram",
        recipient_id="user-1",
    )
    assert trigger.id == "t1"
    assert trigger.enabled is True


def test_is_due_matching():
    """A trigger matching the current minute is due."""
    trigger = CronTrigger(
        id="t1",
        expression="* * * * *",  # Every minute
        goal_text="test",
        channel="cli",
        recipient_id="u1",
    )
    assert is_due(trigger, datetime(2026, 3, 2, 9, 0)) is True


def test_is_due_not_matching():
    """A trigger not matching the current time is not due."""
    trigger = CronTrigger(
        id="t1",
        expression="0 9 * * *",  # 9am only
        goal_text="test",
        channel="cli",
        recipient_id="u1",
    )
    # 10am should not match
    assert is_due(trigger, datetime(2026, 3, 2, 10, 0)) is False


def test_disabled_trigger_never_due():
    trigger = CronTrigger(
        id="t1",
        expression="* * * * *",
        goal_text="test",
        channel="cli",
        recipient_id="u1",
        enabled=False,
    )
    assert is_due(trigger, datetime(2026, 3, 2, 9, 0)) is False
