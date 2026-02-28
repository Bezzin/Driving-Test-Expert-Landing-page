"""Agent dataclass - the core representation of an AI agent in Airees.

Each Agent is an immutable (frozen) record that pairs a name and
instructions with a :class:`~airees.router.types.ModelConfig`, an
optional list of tool names, and runtime constraints such as
``max_turns``.

The ``memory_files`` dict allows agents to declare external files
(e.g. ``SOUL.md``, ``MEMORY.md``) that should be loaded into context
at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from airees.router.types import ModelConfig


@dataclass(frozen=True)
class Agent:
    """Immutable representation of a single AI agent.

    Attributes:
        name: Unique identifier for the agent (e.g. ``"researcher"``).
        instructions: System prompt that defines the agent's behaviour.
        model: The :class:`ModelConfig` that determines which LLM backs
            this agent.
        tools: Tool names available to the agent.  Each name must map to
            a registered entry in the ``ToolRegistry``.
        max_turns: Upper bound on agentic loop iterations before the
            agent yields control.  Defaults to ``10``.
        description: Short human-readable summary of the agent's role,
            useful for orchestrator handoff decisions.
        memory_files: Mapping of semantic labels to file paths that
            should be loaded into the agent's context window at
            runtime (e.g. ``{"personality": "SOUL.md"}``).
    """

    name: str
    instructions: str
    model: ModelConfig
    tools: list[str] = field(default_factory=list)
    max_turns: int = 10
    description: str = ""
    memory_files: dict[str, str] = field(default_factory=dict)
