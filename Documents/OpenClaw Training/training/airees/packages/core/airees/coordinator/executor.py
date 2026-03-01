"""Coordinator executor — manages task graph execution and worker lifecycle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from airees.db.schema import GoalStore, TaskStatus


@dataclass
class Coordinator:
    """Execution manager that walks the task DAG for a goal.

    The Coordinator reads the task graph from the GoalStore, identifies
    ready tasks (PENDING with no unmet dependencies), builds workers,
    executes them, collects results, and either continues or escalates
    to the Brain.
    """

    store: GoalStore
    runner: Any  # Runner instance, typed as Any to avoid circular imports

    async def get_next_tasks(self, goal_id: str) -> list[dict]:
        """Return all tasks that are ready to execute (PENDING status)."""
        return await self.store.get_ready_tasks(goal_id)

    async def is_goal_complete(self, goal_id: str) -> bool:
        """Check whether every task for a goal has completed."""
        tasks = await self.store.get_all_tasks(goal_id)
        if not tasks:
            return False
        return all(t["status"] == TaskStatus.COMPLETED.value for t in tasks)

    async def has_failures(self, goal_id: str) -> bool:
        """Check whether any task for a goal has failed."""
        tasks = await self.store.get_all_tasks(goal_id)
        return any(t["status"] == TaskStatus.FAILED.value for t in tasks)

    async def build_report(self, goal_id: str) -> str:
        """Build a human-readable progress report for a goal.

        Includes task statuses, result summaries, error details,
        and aggregate token/cost metrics.
        """
        tasks = await self.store.get_all_tasks(goal_id)
        progress = await self.store.get_goal_progress(goal_id)
        lines = [
            f"## Progress: {progress['completed']}/{progress['total']} tasks ({progress['percent']:.0f}%)\n",
        ]
        total_tokens = 0
        total_cost = 0.0
        for t in tasks:
            status_icon = "done" if t["status"] == "completed" else t["status"]
            lines.append(f"- [{status_icon}] {t['title']}")
            if t.get("result"):
                summary = t["result"][:200]
                lines.append(f"  Result: {summary}")
            if t.get("error"):
                lines.append(f"  Error: {t['error']}")
            total_tokens += t.get("tokens_used", 0)
            total_cost += t.get("cost", 0.0)

        lines.append(f"\nTotal tokens: {total_tokens}")
        lines.append(f"Total cost: ${total_cost:.4f}")
        return "\n".join(lines)
