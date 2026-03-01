"""Intent classifier — lightweight pre-processing before Brain planning."""
from __future__ import annotations

from enum import Enum
from typing import Any

from airees.router.types import ModelConfig


class GoalIntent(Enum):
    """Classification of what kind of work a goal requires."""

    RESEARCH = "research"
    BUILD = "build"
    FIX = "fix"
    INVESTIGATE = "investigate"
    OPTIMIZE = "optimize"


_INTENT_MAP = {v.value: v for v in GoalIntent}


async def classify_intent(router: Any, goal_description: str) -> GoalIntent:
    """Classify a goal's intent using a cheap model (~100 tokens).

    Args:
        router: The model router for LLM calls.
        goal_description: The raw goal text from the user.

    Returns:
        The classified GoalIntent. Defaults to BUILD if unrecognized.
    """
    model = ModelConfig(model_id="anthropic/claude-haiku-4-5")
    response = await router.create_message(
        model=model,
        system=(
            "Classify this goal into exactly one category: "
            "research, build, fix, investigate, optimize. "
            "Reply with only the category name, nothing else."
        ),
        messages=[{"role": "user", "content": goal_description}],
    )

    text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text = block.text.strip().lower()
            break

    return _INTENT_MAP.get(text, GoalIntent.BUILD)


_INTENT_HINTS: dict[GoalIntent, str] = {
    GoalIntent.RESEARCH: (
        "This is a RESEARCH goal. Prioritize information gathering. "
        "Assign web_search tools to workers. Focus on finding, summarizing, "
        "and synthesizing information rather than building artifacts."
    ),
    GoalIntent.BUILD: (
        "This is a BUILD goal. Focus on creating deliverables — code, "
        "documents, designs. Use a structured approach: plan, implement, test."
    ),
    GoalIntent.FIX: (
        "This is a FIX goal. Focus on debugging and repair. Start by "
        "investigating the root cause, then implement a targeted fix. "
        "Prioritize tasks that reproduce and diagnose the issue."
    ),
    GoalIntent.INVESTIGATE: (
        "This is an INVESTIGATION goal. Focus on understanding why something "
        "is happening. Gather evidence, form hypotheses, test them. "
        "Report findings clearly."
    ),
    GoalIntent.OPTIMIZE: (
        "This is an OPTIMIZATION goal. Focus on measuring current performance, "
        "identifying bottlenecks, and implementing targeted improvements. "
        "Benchmark before and after."
    ),
}


def intent_to_prompt_hint(intent: GoalIntent) -> str:
    """Return a prompt hint for the Brain based on the classified intent."""
    return _INTENT_HINTS.get(intent, _INTENT_HINTS[GoalIntent.BUILD])
