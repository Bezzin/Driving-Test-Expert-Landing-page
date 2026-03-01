"""Concurrency manager -- rate-limits parallel worker execution per provider and model."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class ConcurrencyManager:
    """Controls how many workers can hit each provider/model simultaneously.

    Uses asyncio.Semaphore per concurrency key. Both provider-level and
    model-level limits are enforced -- a worker must acquire both before
    executing.
    """

    provider_limits: dict[str, int] = field(default_factory=dict)
    model_limits: dict[str, int] = field(default_factory=dict)
    default_limit: int = 5
    _semaphores: dict[str, asyncio.Semaphore] = field(
        default_factory=dict, init=False, repr=False
    )

    def _get_semaphore(self, key: str, limit: int) -> asyncio.Semaphore:
        if key not in self._semaphores:
            self._semaphores[key] = asyncio.Semaphore(limit)
        return self._semaphores[key]

    async def acquire(self, provider: str, model: str) -> None:
        """Acquire provider and model semaphores before executing a worker."""
        provider_limit = self.provider_limits.get(provider, self.default_limit)
        provider_sem = self._get_semaphore(f"provider:{provider}", provider_limit)
        await provider_sem.acquire()

        if model in self.model_limits:
            model_sem = self._get_semaphore(f"model:{model}", self.model_limits[model])
            try:
                await model_sem.acquire()
            except Exception:
                provider_sem.release()
                raise

    async def release(self, provider: str, model: str) -> None:
        """Release provider and model semaphores after worker completes."""
        provider_key = f"provider:{provider}"
        if provider_key in self._semaphores:
            self._semaphores[provider_key].release()

        model_key = f"model:{model}"
        if model_key in self._semaphores:
            self._semaphores[model_key].release()
