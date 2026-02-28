# tests/test_tool_registry.py
import pytest
from airees.tools.registry import ToolRegistry, ToolDefinition


def test_register_tool():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    registry.register(tool)
    assert "web_search" in registry


def test_scope_returns_only_requested_tools():
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="a", description="A", input_schema={}))
    registry.register(ToolDefinition(name="b", description="B", input_schema={}))
    registry.register(ToolDefinition(name="c", description="C", input_schema={}))

    scoped = registry.scope(["a", "c"])
    assert len(scoped) == 2
    names = [t.name for t in scoped]
    assert "a" in names
    assert "c" in names
    assert "b" not in names


def test_scope_raises_for_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="unknown_tool"):
        registry.scope(["unknown_tool"])


def test_to_anthropic_format():
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ))
    tools = registry.to_anthropic_format(["web_search"])
    assert tools[0]["name"] == "web_search"
    assert tools[0]["description"] == "Search the web"
    assert "input_schema" in tools[0]


def test_registry_length():
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="a", description="A", input_schema={}))
    registry.register(ToolDefinition(name="b", description="B", input_schema={}))
    assert len(registry) == 2
