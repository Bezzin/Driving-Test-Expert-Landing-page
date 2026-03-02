"""Build worker sub-agents with appropriate models and prompts."""
from __future__ import annotations

MODEL_DEFAULTS: dict[str, str] = {
    "researcher": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "coder": "anthropic/claude-haiku-4-5",
    "reviewer": "anthropic/claude-haiku-4-5",
    "writer": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "tester": "anthropic/claude-haiku-4-5",
    "security": "anthropic/claude-sonnet-4-6",
    "architect": "anthropic/claude-sonnet-4-6",
}

ESCALATION_MODELS: dict[str, str] = {
    "researcher": "anthropic/claude-haiku-4-5",
    "coder": "anthropic/claude-sonnet-4-6",
    "reviewer": "anthropic/claude-sonnet-4-6",
    "writer": "anthropic/claude-haiku-4-5",
    "tester": "anthropic/claude-sonnet-4-6",
    "security": "anthropic/claude-opus-4-6",
    "architect": "anthropic/claude-opus-4-6",
}

ROLE_TOOLS: dict[str, list[str]] = {
    "researcher": ["web_search", "web_extract"],
    "coder": [],
    "reviewer": ["web_search"],
    "writer": ["web_search", "web_extract"],
    "planner": ["web_search"],
    "tester": [],
    "security": ["web_search"],
    "architect": ["web_search"],
}


def get_tools_for_role(agent_role: str) -> list[str]:
    """Return the list of tool names available to the given agent role."""
    return list(ROLE_TOOLS.get(agent_role, []))


def select_model(agent_role: str, recommended: str | None = None, escalate: bool = False) -> str:
    """Select the best model for a given agent role.

    Priority:
    1. If escalating, use the escalation model for the role.
    2. If a recommended model is provided (and not escalating), use it.
    3. Otherwise, fall back to the default model for the role.
    """
    if recommended and not escalate:
        return recommended
    if escalate:
        return ESCALATION_MODELS.get(agent_role, "anthropic/claude-sonnet-4-6")
    return MODEL_DEFAULTS.get(agent_role, "anthropic/claude-haiku-4-5")


def build_worker_prompt(
    *,
    task_title: str,
    task_description: str,
    agent_role: str,
    skill_content: str | None = None,
    previous_output: str | None = None,
    available_tools: list[str] | None = None,
    corpus_context: str | None = None,
) -> str:
    """Assemble a complete system prompt for a worker sub-agent.

    Combines the task details, agent role, optional skill reference,
    and any context from previously completed tasks into a single prompt.
    """
    sections = [
        f"You are a specialist {agent_role} agent. Complete the following task thoroughly.",
        f"\n## Task: {task_title}\n\n{task_description}",
    ]

    if previous_output:
        sections.append(f"\n## Context From Previous Task\n\n{previous_output}")

    if skill_content:
        sections.append(f"\n## Relevant Skill Reference\n\n{skill_content}")

    if corpus_context:
        sections.append(f"\n## Training Corpus Reference\n\n{corpus_context}")

    if available_tools:
        tool_list = ", ".join(available_tools)
        sections.append(
            f"\n## Available Tools\n\n"
            f"You have access to the following tools: {tool_list}\n"
            f"Use these tools when you need external information. "
            f"Call tools via tool_use blocks. You can call multiple tools "
            f"in sequence to gather information before producing your final output.\n"
        )

    sections.append(
        "\n## Output Requirements\n\n"
        "Return your work product clearly. Include:\n"
        "- The actual output (code, text, analysis, etc.)\n"
        "- A confidence score (0-10) for your work quality\n"
        "- Any discoveries or unexpected findings\n"
    )

    return "\n".join(sections)
