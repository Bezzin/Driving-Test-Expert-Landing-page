"""Cron trigger definitions and evaluation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CronTrigger:
    """A scheduled task trigger.

    Attributes:
        id: Unique trigger identifier.
        expression: Cron expression (minute hour day month weekday).
            Only ``*`` and exact integer values are supported.
            Ranges (1-5), steps (*/5), and lists (1,15) are not yet implemented.
            Weekday uses Python convention: 0=Monday, 6=Sunday.
        goal_text: Goal to submit when triggered.
        channel: Channel to deliver the result to.
        recipient_id: User ID for the push notification.
        enabled: Whether this trigger is active.
    """

    id: str
    expression: str
    goal_text: str
    channel: str
    recipient_id: str
    enabled: bool = True


def is_due(trigger: CronTrigger, now: datetime) -> bool:
    """Check if a trigger is due at the given time.

    Supports standard 5-field cron: minute hour day month weekday.
    '*' matches any value. Specific values must match exactly.
    """
    if not trigger.enabled:
        return False

    parts = trigger.expression.strip().split()
    if len(parts) != 5:
        log.warning("Invalid cron expression: %s", trigger.expression)
        return False

    fields = [
        (parts[0], now.minute),
        (parts[1], now.hour),
        (parts[2], now.day),
        (parts[3], now.month),
        (parts[4], now.weekday()),  # 0=Monday
    ]

    for pattern, value in fields:
        if pattern == "*":
            continue
        try:
            if int(pattern) != value:
                return False
        except ValueError:
            log.warning("Invalid cron field: %s", pattern)
            return False

    return True
