from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable definition of a tool that can be invoked by an agent.

    Attributes:
        name: Unique identifier for the tool.
        description: Human-readable description sent to the model.
        input_schema: JSON Schema describing the tool's expected input.
        handler: Optional async callable that executes the tool logic.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Any = None  # Optional async callable


@dataclass
class ToolRegistry:
    """Central registry for tool definitions with per-agent scoping.

    Agents declare which tools they need by name. The registry provides
    scoped access (Principle of Least Privilege) and converts tool
    definitions into the format the Anthropic API expects for tool_use.
    """

    _tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition in the registry."""
        self._tools[tool.name] = tool

    def __contains__(self, name: str) -> bool:
        """Check whether a tool name is registered."""
        return name in self._tools

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def scope(self, tool_names: list[str]) -> list[ToolDefinition]:
        """Return only the requested tools, enforcing least-privilege scoping.

        Args:
            tool_names: List of tool names the caller is allowed to use.

        Returns:
            List of matching ToolDefinition objects.

        Raises:
            KeyError: If any requested tool name is not registered.
        """
        result: list[ToolDefinition] = []
        for name in tool_names:
            if name not in self._tools:
                raise KeyError(f"Tool not registered: {name}")
            result.append(self._tools[name])
        return result

    def to_anthropic_format(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Convert scoped tools into the Anthropic API tool_use format.

        Args:
            tool_names: List of tool names to include.

        Returns:
            List of dicts matching the Anthropic API tools schema.
        """
        tools = self.scope(tool_names)
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]
