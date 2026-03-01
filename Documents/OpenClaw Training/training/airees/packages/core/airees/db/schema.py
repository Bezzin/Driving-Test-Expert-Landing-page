"""SQLite-backed goal and task store for the Airees brain."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import aiosqlite


class GoalStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    ITERATING = "iterating"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GoalStore:
    """Persistent store for goals, tasks (DAG), and decisions.

    Uses aiosqlite following the same pattern as SQLiteRunStore.
    Goals contain tasks arranged in a dependency graph. Tasks with
    unmet dependencies start as BLOCKED and transition to PENDING
    once all upstream tasks complete.
    """

    db_path: Path

    async def initialize(self) -> None:
        """Create tables if they do not already exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    iteration INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL REFERENCES goals(id),
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    agent_role TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    dependencies TEXT NOT NULL DEFAULT '[]',
                    result TEXT,
                    error TEXT,
                    model_used TEXT,
                    tokens_used INTEGER NOT NULL DEFAULT 0,
                    cost REAL NOT NULL DEFAULT 0.0,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL REFERENCES goals(id),
                    iteration INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    # ------------------------------------------------------------------
    # Goal CRUD
    # ------------------------------------------------------------------

    async def create_goal(
        self, description: str, metadata: dict | None = None
    ) -> str:
        """Insert a new goal and return its id."""
        goal_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO goals (id, description, metadata) VALUES (?, ?, ?)",
                (goal_id, description, json.dumps(metadata or {})),
            )
            await db.commit()
        return goal_id

    async def get_goal(self, goal_id: str) -> dict | None:
        """Retrieve a single goal by id. Returns None if not found."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM goals WHERE id = ?", (goal_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_goal_status(
        self, goal_id: str, status: GoalStatus
    ) -> None:
        """Transition a goal to a new status."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE goals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status.value, goal_id),
            )
            await db.commit()

    async def increment_iteration(self, goal_id: str) -> int:
        """Bump the iteration counter and return the new value."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE goals SET iteration = iteration + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (goal_id,),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT iteration FROM goals WHERE id = ?", (goal_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    async def create_task(
        self,
        goal_id: str,
        title: str,
        description: str,
        agent_role: str,
        dependencies: list[str],
        max_retries: int = 3,
    ) -> str:
        """Insert a new task. Tasks with dependencies start as BLOCKED."""
        task_id = str(uuid.uuid4())
        status = (
            TaskStatus.BLOCKED.value if dependencies else TaskStatus.PENDING.value
        )
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO tasks
                   (id, goal_id, title, description, agent_role, status, dependencies, max_retries)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    goal_id,
                    title,
                    description,
                    agent_role,
                    status,
                    json.dumps(dependencies),
                    max_retries,
                ),
            )
            await db.commit()
        return task_id

    async def get_task(self, task_id: str) -> dict | None:
        """Retrieve a single task, deserialising its dependencies list."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            result = dict(row)
            result["dependencies"] = json.loads(result["dependencies"])
            return result

    async def get_ready_tasks(self, goal_id: str) -> list[dict]:
        """Return tasks that are PENDING (no unmet dependencies)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE goal_id = ? AND status = ?",
                (goal_id, TaskStatus.PENDING.value),
            )
            rows = await cursor.fetchall()
            return [
                dict(r) | {"dependencies": json.loads(r["dependencies"])}
                for r in rows
            ]

    async def get_all_tasks(self, goal_id: str) -> list[dict]:
        """Return every task for a goal, ordered by creation time."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE goal_id = ? ORDER BY created_at",
                (goal_id,),
            )
            rows = await cursor.fetchall()
            return [
                dict(r) | {"dependencies": json.loads(r["dependencies"])}
                for r in rows
            ]

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    async def complete_task(
        self, task_id: str, result: str, tokens_used: int, cost: float
    ) -> None:
        """Mark a task as completed and unblock any dependents."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE tasks SET status = ?, result = ?, tokens_used = ?, cost = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (TaskStatus.COMPLETED.value, result, tokens_used, cost, task_id),
            )
            # Unblock dependents whose upstream tasks are all completed
            cursor = await db.execute(
                "SELECT goal_id FROM tasks WHERE id = ?", (task_id,)
            )
            row = await cursor.fetchone()
            if row:
                goal_id = row[0]
                blocked = await db.execute(
                    "SELECT id, dependencies FROM tasks WHERE goal_id = ? AND status = ?",
                    (goal_id, TaskStatus.BLOCKED.value),
                )
                blocked_rows = await blocked.fetchall()
                for brow in blocked_rows:
                    deps = json.loads(brow[1])
                    all_done = True
                    for dep_id in deps:
                        dep_cursor = await db.execute(
                            "SELECT status FROM tasks WHERE id = ?", (dep_id,)
                        )
                        dep_row = await dep_cursor.fetchone()
                        if (
                            dep_row is None
                            or dep_row[0] != TaskStatus.COMPLETED.value
                        ):
                            all_done = False
                            break
                    if all_done:
                        await db.execute(
                            "UPDATE tasks SET status = ? WHERE id = ?",
                            (TaskStatus.PENDING.value, brow[0]),
                        )
            await db.commit()

    async def fail_task(
        self, task_id: str, error: str, retry: bool = False
    ) -> None:
        """Mark a task as failed. If *retry* is True, reset to PENDING and bump retry_count."""
        async with aiosqlite.connect(self.db_path) as db:
            if retry:
                await db.execute(
                    """UPDATE tasks SET status = ?, error = ?, retry_count = retry_count + 1,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (TaskStatus.PENDING.value, error, task_id),
                )
            else:
                await db.execute(
                    """UPDATE tasks SET status = ?, error = ?,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (TaskStatus.FAILED.value, error, task_id),
                )
            await db.commit()

    # ------------------------------------------------------------------
    # Progress & decisions
    # ------------------------------------------------------------------

    async def get_goal_progress(self, goal_id: str) -> dict:
        """Return total, completed, and percent complete for a goal's tasks."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM tasks WHERE goal_id = ?", (goal_id,)
            )
            total = (await cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM tasks WHERE goal_id = ? AND status = ?",
                (goal_id, TaskStatus.COMPLETED.value),
            )
            completed = (await cursor.fetchone())[0]
            percent = (completed / total * 100) if total > 0 else 0.0
            return {
                "total": total,
                "completed": completed,
                "percent": percent,
            }

    async def log_decision(
        self,
        goal_id: str,
        iteration: int,
        action: str,
        reasoning: str,
    ) -> str:
        """Record a brain decision for auditability."""
        dec_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO decisions (id, goal_id, iteration, action, reasoning) VALUES (?, ?, ?, ?, ?)",
                (dec_id, goal_id, iteration, action, reasoning),
            )
            await db.commit()
        return dec_id
