"""Zero-cost keyword-based complexity classifier.

Routes messages to the appropriate model tier without any LLM calls.
Short greetings go to Haiku, moderate requests to Sonnet, and complex
multi-step tasks to Opus.
"""
from __future__ import annotations

import logging
import re
from enum import Enum

log = logging.getLogger(__name__)

# -- Patterns ----------------------------------------------------------------

_QUICK_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^(hi|hello|hey|thanks|thank you|bye|goodbye|ok|yes|no|sure)\b",
        r"^(what|when|where|who)\b.{0,40}\??\s*$",
    )
)

_COMPLEX_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"plan\b.*\band\b",
        r"research\b.*\bcreate\b",
        r"multi[- ]?step",
        r"comprehensive",
        r"analyze\b.*\band\b.*\bthen\b",
        r"build\b.*\bdeploy\b",
    )
)

_SHORT_THRESHOLD = 30
_LONG_THRESHOLD = 200


class Complexity(Enum):
    """Message complexity tier for model routing."""

    QUICK = "quick"
    MODERATE = "moderate"
    COMPLEX = "complex"

    @property
    def model_hint(self) -> str:
        """Return the recommended model tier for this complexity."""
        return _MODEL_HINTS[self]


_MODEL_HINTS: dict[Complexity, str] = {
    Complexity.QUICK: "haiku",
    Complexity.MODERATE: "sonnet",
    Complexity.COMPLEX: "opus",
}


async def classify_complexity(text: str) -> Complexity:
    """Classify *text* into a complexity tier using keyword heuristics.

    This is intentionally zero-cost — no LLM calls, no network I/O.
    The function is async so it can be swapped for an LLM-based
    classifier in the future without changing call sites.
    """
    stripped = text.strip()

    # 1. Check quick patterns (greetings, simple questions) — unambiguous
    for pattern in _QUICK_PATTERNS:
        if pattern.search(stripped):
            log.debug("classify_complexity: QUICK pattern matched")
            return Complexity.QUICK

    # 2. Check complex patterns — before length thresholds so short complex
    #    messages like "plan and deploy" are not misclassified as QUICK
    for pattern in _COMPLEX_PATTERNS:
        if pattern.search(stripped):
            log.debug("classify_complexity: COMPLEX pattern matched")
            return Complexity.COMPLEX

    # 3. Short messages default to quick
    if len(stripped) < _SHORT_THRESHOLD:
        log.debug("classify_complexity: SHORT -> QUICK (%d chars)", len(stripped))
        return Complexity.QUICK

    # 4. Long messages default to complex
    if len(stripped) > _LONG_THRESHOLD:
        log.debug("classify_complexity: LONG -> COMPLEX (%d chars)", len(stripped))
        return Complexity.COMPLEX

    # 5. Everything else is moderate
    log.debug("classify_complexity: default -> MODERATE")
    return Complexity.MODERATE
