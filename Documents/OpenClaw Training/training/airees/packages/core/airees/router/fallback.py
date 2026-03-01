"""Fallback router -- retries across multiple providers with exponential backoff."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from airees.router.types import ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class FallbackRouter:
    """Wraps multiple provider routers with retry and failover logic.

    Attributes:
        providers: Ordered list of (name, router) tuples. First = preferred.
        model_compatibility: Maps model IDs to lists of compatible provider names.
        max_retries: Max retry attempts across all providers.
        backoff_base: Base delay in seconds for exponential backoff.
    """

    providers: list[tuple[str, Any]]
    model_compatibility: dict[str, list[str]] = field(default_factory=dict)
    max_retries: int = 3
    backoff_base: float = 1.0

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Any:
        compatible = self.model_compatibility.get(model.model_id)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            for provider_name, router in self.providers:
                if compatible and provider_name not in compatible:
                    continue
                try:
                    return await router.create_message(
                        model=model, system=system, messages=messages,
                        tools=tools, **kwargs,
                    )
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "Provider %s failed (attempt %d): %s",
                        provider_name, attempt + 1, e,
                    )
                    continue

            if attempt < self.max_retries - 1:
                delay = self.backoff_base * (2 ** attempt)
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise RuntimeError("No providers configured")
