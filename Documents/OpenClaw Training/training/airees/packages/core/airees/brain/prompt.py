"""Build the Brain's system prompt from components."""
from __future__ import annotations

from airees.soul import Soul


def build_brain_prompt(
    *,
    soul: Soul,
    goal: str,
    intent: str | None = None,
    coordinator_report: str | None = None,
    active_skill: str | None = None,
    iteration: int = 0,
) -> str:
    """Assemble the Brain's system prompt from SOUL + goal context + reports.

    The prompt is built from discrete sections that are conditionally included
    based on the current state of execution. This keeps the Brain's context
    focused on what matters for the current iteration.

    Args:
        soul: The parsed SOUL.md identity.
        goal: The user's top-level goal.
        intent: The classified intent string (e.g. "fix", "research").
        coordinator_report: Status report from the Coordinator (if any).
        active_skill: Relevant skill/pipeline markdown (if any).
        iteration: Current iteration number (0 = first pass).

    Returns:
        The fully assembled system prompt string.
    """
    sections: list[str] = [soul.to_prompt()]

    sections.append(
        "\n## Your Role\n\n"
        "You are the strategic brain of a multi-agent system. You PLAN, EVALUATE, "
        "and DECIDE. You never do the work yourself — you delegate everything to "
        "workers via the Coordinator.\n\n"
        "When planning, break the goal into a task graph with dependencies. "
        "Assign agent roles and recommend models for each task.\n\n"
        "When evaluating, think holistically: does the whole thing work together? "
        "Is there a better approach? Did workers discover anything useful?\n\n"
        "You have three actions after evaluation:\n"
        "- **satisfied**: goal is complete, report to user\n"
        "- **adapt**: modify the task graph (add/remove/change tasks)\n"
        "- **rewrite**: scrap parts of the plan based on what was learned\n"
    )

    sections.append(f"\n## Current Goal\n\n{goal}\n")

    if intent:
        from airees.brain.intent import GoalIntent, intent_to_prompt_hint
        try:
            goal_intent = GoalIntent(intent)
            sections.append(f"\n## Goal Intent\n\n{intent_to_prompt_hint(goal_intent)}\n")
        except ValueError:
            pass

    if iteration > 0:
        sections.append(
            f"\n## Iteration: {iteration}\n\n"
            f"This goal has been through {iteration} iteration(s). "
            "Review what changed and why.\n"
        )

    if active_skill:
        sections.append(f"\n## Relevant Skill (Proven Pipeline)\n\n{active_skill}\n")

    if coordinator_report:
        sections.append(f"\n## Coordinator Report\n\n{coordinator_report}\n")

    sections.append(
        "\n## Output Rules\n\n"
        "- Use the `create_plan` tool to output your task graph\n"
        "- Use the `evaluate_result` tool to judge completed work\n"
        "- Use the `adapt_plan` tool to modify the plan mid-execution\n"
        "- Use the `message_user` tool ONLY to report final results or ask for "
        "input you genuinely need\n"
        "- NEVER output a plain text plan — always use tools\n"
    )

    return "\n".join(sections)
