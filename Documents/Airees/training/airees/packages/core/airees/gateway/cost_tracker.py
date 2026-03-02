"""Cost tracker for monitoring API spend across models and channels.

Records token usage per call, computes dollar costs using per-model
pricing tables, and provides breakdowns by model tier and channel.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelCost:
    """Immutable per-model pricing in dollars per million tokens.

    Attributes:
        input_per_mtok: Cost in USD per 1 million input tokens.
        output_per_mtok: Cost in USD per 1 million output tokens.
    """

    input_per_mtok: float
    output_per_mtok: float

    @staticmethod
    def defaults() -> dict[str, ModelCost]:
        """Return the default pricing table for supported model tiers."""
        return {
            "haiku": ModelCost(input_per_mtok=1.0, output_per_mtok=5.0),
            "sonnet": ModelCost(input_per_mtok=3.0, output_per_mtok=15.0),
            "opus": ModelCost(input_per_mtok=5.0, output_per_mtok=25.0),
        }


@dataclass(frozen=True)
class _CostRecord:
    """Internal immutable record of a single API call."""

    model_key: str
    input_tokens: int
    output_tokens: int
    cost: float
    channel: str


@dataclass
class CostTracker:
    """Tracks API usage costs across models and channels.

    Attributes:
        _records: Internal list of cost records.
        _costs: Pricing table mapping model tier to :class:`ModelCost`.
    """

    _records: list[_CostRecord] = field(default_factory=list)
    _costs: dict[str, ModelCost] = field(default_factory=ModelCost.defaults)

    def record(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        channel: str = "unknown",
    ) -> float:
        """Record an API call and return its cost in USD.

        Args:
            model: The model identifier string (e.g. ``"claude-haiku-4-5"``).
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
            channel: Originating channel name for per-channel tracking.

        Returns:
            The computed cost in USD for this single call.
        """
        model_key = self._resolve_model_key(model)
        pricing = self._costs[model_key]

        cost = (
            (input_tokens / 1_000_000) * pricing.input_per_mtok
            + (output_tokens / 1_000_000) * pricing.output_per_mtok
        )

        self._records.append(
            _CostRecord(
                model_key=model_key,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                channel=channel,
            )
        )

        log.debug(
            "Recorded %s call: %d in / %d out tokens = $%.6f (%s)",
            model_key,
            input_tokens,
            output_tokens,
            cost,
            channel,
        )

        return cost

    @property
    def total_cost(self) -> float:
        """Total cost in USD across all recorded calls."""
        return sum(r.cost for r in self._records)

    @property
    def total_turns(self) -> int:
        """Number of recorded API calls."""
        return len(self._records)

    def breakdown(self) -> dict[str, float]:
        """Return cost grouped by model tier.

        Returns:
            Dictionary mapping model tier name to total cost in USD.
        """
        result: dict[str, float] = {}
        for r in self._records:
            result[r.model_key] = result.get(r.model_key, 0.0) + r.cost
        return result

    def by_channel(self) -> dict[str, float]:
        """Return cost grouped by channel.

        Returns:
            Dictionary mapping channel name to total cost in USD.
        """
        result: dict[str, float] = {}
        for r in self._records:
            result[r.channel] = result.get(r.channel, 0.0) + r.cost
        return result

    def reset(self) -> None:
        """Clear all recorded cost data."""
        self._records.clear()
        log.info("CostTracker reset — all records cleared")

    def _resolve_model_key(self, model: str) -> str:
        """Map a model identifier string to a pricing tier key.

        Checks if the model string contains ``"haiku"``, ``"sonnet"``, or
        ``"opus"`` (case-insensitive).  Falls back to ``"sonnet"`` for
        unrecognised models.
        """
        lower = model.lower()
        for tier in ("haiku", "sonnet", "opus"):
            if tier in lower:
                return tier
        log.warning("Unknown model '%s' — defaulting to sonnet pricing", model)
        return "sonnet"
