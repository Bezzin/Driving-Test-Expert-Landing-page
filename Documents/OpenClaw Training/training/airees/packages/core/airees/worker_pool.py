"""Priority-aware worker pool for parallel task execution."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from airees.concurrency import ConcurrencyManager


@dataclass
class WorkerPool:
    """Executes tasks in priority order, respecting concurrency limits.

    Tasks are submitted with a priority value (lower = higher priority).
    The pool uses an asyncio.PriorityQueue internally and launches workers
    up to the concurrency limit, processing highest-priority tasks first.
    """

    concurrency: ConcurrencyManager
    _queue: asyncio.PriorityQueue = field(init=False)
    _counter: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._queue = asyncio.PriorityQueue()

    def submit(self, task: dict) -> None:
        """Add a task to the priority queue.

        Uses (priority, counter) as the sort key so tasks with equal
        priority preserve insertion order.
        """
        priority = task.get("priority", 2)
        self._queue.put_nowait((priority, self._counter, task))
        self._counter += 1

    async def run_all(
        self,
        executor: Callable[[dict], Coroutine[Any, Any, Any]],
        provider: str,
        model: str,
    ) -> list[Any]:
        """Process all queued tasks and return results.

        Args:
            executor: Async function that takes a task dict and returns a result.
            provider: Provider name for concurrency limiting.
            model: Model ID for concurrency limiting.

        Returns:
            List of results (or Exception objects for failed tasks).
        """
        tasks: list[asyncio.Task] = []

        async def _run(task_dict: dict) -> Any:
            await self.concurrency.acquire(provider, model)
            try:
                return await executor(task_dict)
            except Exception as e:
                return e
            finally:
                await self.concurrency.release(provider, model)

        while not self._queue.empty():
            _, _, task_dict = self._queue.get_nowait()
            tasks.append(asyncio.create_task(_run(task_dict)))

        if not tasks:
            return []

        return list(await asyncio.gather(*tasks))
