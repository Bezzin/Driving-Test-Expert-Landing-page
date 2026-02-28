"""Quality gate system for scoring, gating, and escalation between pipeline steps."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateAction(Enum):
    RETRY = "retry"
    FLAG_HUMAN = "flag_human"
    SKIP = "skip"


@dataclass(frozen=True)
class GateResult:
    score: float
    passed: bool
    feedback: str = ""


@dataclass(frozen=True)
class QualityGate:
    name: str
    min_score: float = 7.0
    max_retries: int = 3
    on_failure: GateAction = GateAction.RETRY

    def evaluate(self, score: float, feedback: str = "") -> GateResult:
        return GateResult(score=score, passed=score >= self.min_score, feedback=feedback)

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_retries

    def should_escalate(self, attempt: int) -> bool:
        return attempt >= self.max_retries and self.on_failure == GateAction.FLAG_HUMAN
