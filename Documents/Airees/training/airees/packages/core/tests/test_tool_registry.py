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


def test_trust_level_enum_exists():
    """TrustLevel enum should have BUILTIN, MCP, CLI values."""
    from airees.tools.registry import TrustLevel
    assert TrustLevel.BUILTIN.value == "builtin"
    assert TrustLevel.MCP.value == "mcp"
    assert TrustLevel.CLI.value == "cli"


def test_tool_definition_has_trust_level():
    """ToolDefinition should have trust_level and source fields."""
    from airees.tools.registry import ToolDefinition, TrustLevel
    tool = ToolDefinition(
        name="test",
        description="test tool",
        input_schema={"type": "object"},
        trust_level=TrustLevel.MCP,
        source="mcp://test-server",
    )
    assert tool.trust_level == TrustLevel.MCP
    assert tool.source == "mcp://test-server"


def test_tool_definition_defaults_to_builtin():
    """ToolDefinition should default to BUILTIN trust level."""
    from airees.tools.registry import ToolDefinition, TrustLevel
    tool = ToolDefinition(
        name="test",
        description="test",
        input_schema={"type": "object"},
    )
    assert tool.trust_level == TrustLevel.BUILTIN
    assert tool.source == ""


def test_filter_by_role_allow_list():
    """filter_for_role should return only allowed tools."""
    from airees.tools.registry import ToolRegistry, ToolDefinition
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="web_search", description="", input_schema={}))
    registry.register(ToolDefinition(name="delete_file", description="", input_schema={}))
    registry.register(ToolDefinition(name="read_file", description="", input_schema={}))

    access_config = {
        "researcher": {"allow": ["web_search", "read_file"]},
    }
    filtered = registry.filter_for_role("researcher", access_config)
    names = [t.name for t in filtered]
    assert "web_search" in names
    assert "read_file" in names
    assert "delete_file" not in names


def test_filter_by_role_block_list():
    """filter_for_role should exclude blocked tools when allow is wildcard."""
    from airees.tools.registry import ToolRegistry, ToolDefinition
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="web_search", description="", input_schema={}))
    registry.register(ToolDefinition(name="delete_file", description="", input_schema={}))

    access_config = {
        "coder": {"allow": ["*"], "block": ["delete_file"]},
    }
    filtered = registry.filter_for_role("coder", access_config)
    names = [t.name for t in filtered]
    assert "web_search" in names
    assert "delete_file" not in names


def test_filter_by_role_unknown_role_returns_empty():
    """Unknown role with no config returns empty list."""
    from airees.tools.registry import ToolRegistry, ToolDefinition
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="web_search", description="", input_schema={}))
    filtered = registry.filter_for_role("unknown", {})
    assert filtered == []
