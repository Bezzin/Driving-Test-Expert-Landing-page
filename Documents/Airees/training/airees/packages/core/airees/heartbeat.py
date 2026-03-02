"""Tiered heartbeat daemon for background monitoring and self-healing.

Tier 1 (Heartbeat, 15s): Goal queue, stale tasks, context budget
Tier 2 (Health, 60s): Resource usage
Tier 3 (Deep Audit, 300s): Memory compaction, skill decay
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from airees.db.schema import GoalStore, TaskStatus
from airees.events import Event, EventBus, EventType
from airees.scheduler import Scheduler

logger = logging.getLogger(__name__)

_TIER_1_INTERVAL = 15
_TIER_2_INTERVAL = 60
_TIER_3_INTERVAL = 300
_MAX_CONSECUTIVE_FAILURES = 3


@dataclass
class HeartbeatDaemon:
    """Background daemon with tiered monitoring and closed-loop remediation.

    Each check follows: Detect -> Diagnose -> Act -> Verify -> Escalate.
    Failure counters track consecutive failures per check name.
    After MAX_CONSECUTIVE_FAILURES, an escalation event is emitted.
    Silent when healthy (no events emitted on passing checks).
    """

    store: GoalStore
    scheduler: Scheduler
    event_bus: EventBus
    corpus_engine: Any = None
    skill_store: Any = None
    stale_task_timeout_seconds: int = 300
    _failure_counts: dict[str, int] = field(default_factory=dict)
    _poll_tasks: list[asyncio.Task] = field(default_factory=list, init=False, repr=False)

    async def run_forever(self) -> None:
        """Launch all tiered polling tasks as concurrent coroutines."""
        logger.info("HeartbeatDaemon started")
        self._poll_tasks = [
            asyncio.create_task(self._poll_loop("goal_queue", self._check_goal_queue, _TIER_1_INTERVAL)),
            asyncio.create_task(self._poll_loop("stale_tasks", self._check_stale_tasks, _TIER_1_INTERVAL)),
            asyncio.create_task(self._poll_loop("context_budget", self._check_context_budgets, _TIER_1_INTERVAL)),
            asyncio.create_task(self._poll_loop("resource_usage", self._check_resources, _TIER_2_INTERVAL)),
            asyncio.create_task(self._poll_loop("memory_compaction", self._compact_memory, _TIER_3_INTERVAL)),
            asyncio.create_task(self._poll_loop("skill_decay", self._decay_skills, _TIER_3_INTERVAL)),
        ]
        try:
            await asyncio.gather(*self._poll_tasks)
        except asyncio.CancelledError:
            logger.info("HeartbeatDaemon stopped")
            raise

    async def stop(self) -> None:
        """Cancel all polling tasks gracefully."""
        for task in self._poll_tasks:
            task.cancel()
        self._poll_tasks.clear()

    async def _poll_loop(self, name: str, check_fn: Any, interval: int) -> None:
        """Run a single check on a loop with the given interval."""
        while True:
            await self._run_check(name, check_fn)
            await asyncio.sleep(interval)

    async def _run_check(self, name: str, check_fn: Any) -> None:
        """Execute a check and handle its result."""
        try:
            issue = await check_fn()
            if issue is None:
                self._failure_counts[name] = 0
            else:
                await self._handle_anomaly(name, issue)
        except Exception as e:
            logger.warning("Heartbeat check '%s' raised: %s", name, e)
            await self._handle_anomaly(name, str(e))

    async def _handle_anomaly(self, name: str, issue: str) -> None:
        """Handle a detected anomaly with escalation logic."""
        count = self._failure_counts.get(name, 0) + 1
        self._failure_counts[name] = count

        if count > _MAX_CONSECUTIVE_FAILURES:
            await self.event_bus.emit_async(Event(
                event_type=EventType.HEARTBEAT_ESCALATE,
                agent_name="heartbeat",
                data={"check": name, "issue": issue, "consecutive_failures": count},
            ))
            return

        await self.event_bus.emit_async(Event(
            event_type=EventType.HEARTBEAT_ANOMALY,
            agent_name="heartbeat",
            data={"check": name, "issue": issue, "consecutive_failures": count},
        ))

    async def _check_goal_queue(self) -> str | None:
        """Poll for pending goals and check scheduler capacity."""
        pending = await self.store.get_pending_goals()
        if pending and not self.scheduler.has_capacity:
            return f"Scheduler at capacity, {len(pending)} goals waiting"
        return None

    async def _check_stale_tasks(self) -> str | None:
        """Find running tasks older than stale_task_timeout_seconds."""
        import aiosqlite
        async with aiosqlite.connect(self.store.db_path) as db:
            cursor = await db.execute(
                """SELECT id, title FROM tasks
                   WHERE status = ?
                   AND updated_at < datetime('now', ?)""",
                (TaskStatus.RUNNING.value, f"-{self.stale_task_timeout_seconds} seconds"),
            )
            stale = await cursor.fetchall()
        if stale:
            ids = [row[0] for row in stale]
            return f"Found {len(stale)} stale running tasks: {ids}"
        return None

    async def _check_context_budgets(self) -> str | None:
        """Check context budget across active goals (placeholder)."""
        return None

    async def _check_resources(self) -> str | None:
        """Sample resource usage (placeholder for future metrics)."""
        return None

    async def _compact_memory(self) -> str | None:
        """Trigger corpus reindex if corpus engine is available."""
        if self.corpus_engine is not None:
            try:
                await asyncio.to_thread(self.corpus_engine._build_index)
            except Exception as e:
                return f"Memory compaction failed: {e}"
        return None

    async def _decay_skills(self) -> str | None:
        """Decay success_rate for unused skills (placeholder)."""
        return None
