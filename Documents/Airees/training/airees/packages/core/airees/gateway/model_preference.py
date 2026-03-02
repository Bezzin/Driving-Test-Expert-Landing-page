"""Adaptive model preference — learn which models work for which complexity."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_HINTS: dict[str, str] = {
    "quick": "haiku",
    "moderate": "sonnet",
    "complex": "opus",
}

_DOWNGRADE_MAP: dict[str, str] = {
    "sonnet": "haiku",
    "opus": "sonnet",
}


@dataclass
class ModelPreference:
    """Tracks success/failure rates and recommends model tiers.

    Attributes:
        downgrade_threshold: Consecutive successes at a cheaper tier
            needed before recommending it as default.
        upgrade_threshold: Consecutive failures at a tier before
            reverting to the original default.
    """

    downgrade_threshold: int = 3
    upgrade_threshold: int = 2
    _records: dict[str, dict[str, dict[str, int]]] = field(
        default_factory=dict, init=False
    )
    _overrides: dict[str, str] = field(default_factory=dict, init=False)

    def record(self, *, complexity: str, model_used: str, success: bool) -> None:
        """Record a success or failure for a complexity+model pair."""
        if complexity not in self._records:
            self._records[complexity] = {}
        if model_used not in self._records[complexity]:
            self._records[complexity][model_used] = {"successes": 0, "failures": 0}

        bucket = self._records[complexity][model_used]
        if success:
            bucket["successes"] += 1
        else:
            bucket["failures"] += 1

        self._recompute(complexity)

    def get_model(self, complexity: str) -> str:
        """Return the recommended model tier for this complexity."""
        return self._overrides.get(complexity, _DEFAULT_HINTS.get(complexity, "sonnet"))

    def stats(self) -> dict[str, Any]:
        """Return raw success/failure counts."""
        return dict(self._records)

    def _recompute(self, complexity: str) -> None:
        """Recompute the override for a complexity tier."""
        default = _DEFAULT_HINTS.get(complexity, "sonnet")
        cheaper = _DOWNGRADE_MAP.get(default)

        if cheaper and cheaper in self._records.get(complexity, {}):
            bucket = self._records[complexity][cheaper]
            if bucket["successes"] >= self.downgrade_threshold:
                failure_rate = bucket["failures"] / max(
                    bucket["successes"] + bucket["failures"], 1
                )
                if failure_rate < 0.3:
                    self._overrides[complexity] = cheaper
                    log.info(
                        "Downgraded %s from %s to %s",
                        complexity, default, cheaper,
                    )
                    return

        # Check if cheaper model is failing too much
        if cheaper and cheaper in self._records.get(complexity, {}):
            bucket = self._records[complexity][cheaper]
            if bucket["failures"] >= self.upgrade_threshold:
                self._overrides.pop(complexity, None)
                log.info("Reverted %s to default %s", complexity, default)
                return
