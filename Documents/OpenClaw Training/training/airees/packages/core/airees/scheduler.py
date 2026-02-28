"""Cron-like scheduler for polling pending work with capacity management."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class SchedulerConfig:
    interval_seconds: int = 300
    max_concurrent: int = 5


@dataclass
class Scheduler:
    config: SchedulerConfig
    _active: dict[str, asyncio.Task] = field(default_factory=dict)
    _pending: list[tuple[str, Callable[[str], Awaitable[Any]]]] = field(default_factory=list)

    @property
    def active_count(self) -> int:
        self._cleanup_done()
        return len(self._active)

    @property
    def has_capacity(self) -> bool:
        self._cleanup_done()
        return self.active_count < self.config.max_concurrent

    async def submit(self, project_id: str, work_fn: Callable[[str], Awaitable[Any]]) -> None:
        self._cleanup_done()
        if self.has_capacity:
            self._start(project_id, work_fn)
        else:
            self._pending.append((project_id, work_fn))

    def _start(self, project_id: str, work_fn: Callable[[str], Awaitable[Any]]) -> None:
        async def _wrapper():
            try:
                await work_fn(project_id)
            finally:
                self._active.pop(project_id, None)
                self._drain_pending()

        task = asyncio.create_task(_wrapper())
        self._active[project_id] = task

    def _drain_pending(self) -> None:
        while self._pending and self.has_capacity:
            pid, fn = self._pending.pop(0)
            self._start(pid, fn)

    def _cleanup_done(self) -> None:
        done = [k for k, t in self._active.items() if t.done()]
        for k in done:
            del self._active[k]

    async def stop(self) -> None:
        for task in self._active.values():
            task.cancel()
        self._active.clear()
        self._pending.clear()
