"""Context window budget tracking for agents."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    max_tokens: int = 200000
    used_tokens: int = 0
    max_usage_percent: float | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    @property
    def usage_percent(self) -> float:
        if self.max_tokens == 0:
            return 100.0
        return (self.used_tokens / self.max_tokens) * 100.0

    @property
    def effective_max(self) -> int:
        if self.max_usage_percent is not None:
            return int(self.max_tokens * (self.max_usage_percent / 100.0))
        return self.max_tokens

    @property
    def is_over_limit(self) -> bool:
        return self.used_tokens > self.effective_max

    def consume(self, tokens: int) -> ContextBudget:
        return ContextBudget(
            max_tokens=self.max_tokens,
            used_tokens=self.used_tokens + tokens,
            max_usage_percent=self.max_usage_percent,
        )

    def exceeds_threshold(self, percent: float) -> bool:
        return self.usage_percent > percent
