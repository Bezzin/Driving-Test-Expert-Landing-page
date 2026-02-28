from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass
class SQLiteRunStore:
    """SQLite-based run history store for persisting run metadata.

    Stores run_id, agent_name, task, output, turn count, and token
    usage so users can review past runs, outputs, and costs.
    """

    db_path: Path

    async def initialize(self) -> None:
        """Create the runs table if it does not already exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    task TEXT NOT NULL,
                    output TEXT NOT NULL,
                    turns INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def save_run(
        self,
        run_id: str,
        agent_name: str,
        task: str,
        output: str,
        turns: int,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Persist a single run record to the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO runs
                   (run_id, agent_name, task, output, turns, input_tokens, output_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, agent_name, task, output, turns, input_tokens, output_tokens),
            )
            await db.commit()

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve a single run by its ID. Returns None if not found."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        """List runs ordered by most recent first, up to *limit* rows."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
