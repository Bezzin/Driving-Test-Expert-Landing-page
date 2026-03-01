"""Background daemon for polling and executing pending/interrupted goals."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from airees.events import Event, EventType
from airees.scheduler import Scheduler
from airees.state import load_state

logger = logging.getLogger(__name__)


@dataclass
class GoalDaemon:
    """Polls for pending and interrupted goals, submits them to the Scheduler.

    The daemon runs as a long-lived background task. On each poll cycle it:
    1. Scans state_dir for interrupted goals (crash recovery, prioritised)
    2. Queries GoalStore for new pending goals
    3. Submits each to the Scheduler (respecting max_concurrent)
    """

    orchestrator: object  # BrainOrchestrator — typed as object to avoid circular import
    scheduler: Scheduler
    poll_interval: int = 30
    state_dir: Path = Path("data/states")

    async def run_forever(self) -> None:
        """Poll indefinitely until cancelled."""
        logger.info("GoalDaemon started (poll_interval=%ds)", self.poll_interval)
        try:
            while True:
                await self._poll_once()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            logger.info("GoalDaemon stopped")

    async def _poll_once(self) -> None:
        """Single poll cycle: find work, submit to scheduler."""
        interrupted = self._find_interrupted_goals()
        pending = await self._find_pending_goals()

        for goal_id in [*interrupted, *pending]:
            if not self.scheduler.has_capacity:
                break

            if goal_id in interrupted:
                await self._resume_goal(goal_id)
            else:
                await self.scheduler.submit(
                    goal_id,
                    self._make_execute_fn(),
                )

    async def _find_pending_goals(self) -> list[str]:
        """Query GoalStore for goals with status PENDING."""
        goals = await self.orchestrator.store.get_pending_goals()
        return [g["id"] for g in goals]

    def _find_interrupted_goals(self) -> list[str]:
        """Scan state_dir for non-complete ProjectState files."""
        if not self.state_dir.exists():
            return []
        interrupted = []
        for state_file in self.state_dir.glob("*.json"):
            try:
                state = load_state(state_file)
                if not state.is_complete and state.current_phase is not None:
                    interrupted.append(state.project_id)
            except Exception:
                logger.warning("Could not load state file: %s", state_file)
        return interrupted

    async def _resume_goal(self, goal_id: str) -> None:
        """Reset stale tasks and submit goal for re-execution."""
        await self.orchestrator.store.reset_stale_running_tasks(goal_id)
        await self.orchestrator.event_bus.emit_async(Event(
            event_type=EventType.GOAL_RESUMED,
            agent_name="goal-daemon",
            data={"goal_id": goal_id},
        ))
        await self.scheduler.submit(
            goal_id,
            self._make_execute_fn(),
        )

    def _make_execute_fn(self):
        """Return a callable that executes a goal by id."""
        async def _execute(goal_id: str) -> str:
            return await self.orchestrator.execute_goal(goal_id)
        return _execute
