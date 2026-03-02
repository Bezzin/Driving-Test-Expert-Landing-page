"""ProactiveScheduler — evaluate cron triggers and fire goals."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from airees.gateway.cron import CronTrigger, is_due
from airees.gateway.types import InboundMessage

log = logging.getLogger(__name__)


@dataclass
class ProactiveScheduler:
    """Evaluates cron triggers and submits matching goals via the gateway.

    Attributes:
        gateway: The Gateway instance (used to send messages).
        triggers: Active cron triggers.
    """

    gateway: Any
    triggers: list[CronTrigger] = field(default_factory=list)
    _running: set[str] = field(default_factory=set, init=False)

    def add_trigger(self, trigger: CronTrigger) -> None:
        self.triggers.append(trigger)
        log.info("Added trigger: %s (%s)", trigger.id, trigger.expression)

    def remove_trigger(self, trigger_id: str) -> bool:
        before = len(self.triggers)
        self.triggers = [t for t in self.triggers if t.id != trigger_id]
        removed = len(self.triggers) < before
        if removed:
            self._running.discard(trigger_id)
            log.info("Removed trigger: %s", trigger_id)
        return removed

    async def evaluate(self, now: datetime) -> int:
        """Check all triggers against *now* and fire matching ones.

        Returns:
            Number of triggers fired.
        """
        fired = 0
        for trigger in self.triggers:
            if trigger.id in self._running:
                log.debug("Skipping trigger %s — still running", trigger.id)
                continue

            if is_due(trigger, now):
                log.info("Firing trigger: %s (%s)", trigger.id, trigger.goal_text)
                self._running.add(trigger.id)
                try:
                    message = InboundMessage(
                        channel=trigger.channel,
                        sender_id=trigger.recipient_id,
                        text=trigger.goal_text,
                    )
                    await self.gateway.handle_message(message)
                    fired += 1
                except Exception as exc:
                    log.error("Trigger %s failed: %s", trigger.id, exc, exc_info=True)
                finally:
                    self._running.discard(trigger.id)
        return fired
