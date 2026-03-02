"""Tests for MCP tool provider."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from airees.mcp_client import MCPServerConfig, MCPToolProvider, _validate_command
from airees.tools.registry import TrustLevel


def test_mcp_server_config_creates():
    """MCPServerConfig should be a frozen dataclass."""
    config = MCPServerConfig(
        name="test",
        transport="stdio",
        command="python",
    )
    assert config.name == "test"
    assert config.transport == "stdio"
    assert config.cache_tools is True


def test_mcp_server_config_env_is_immutable_tuple():
    """MCPServerConfig env should be a tuple of tuples, not a mutable dict."""
    config = MCPServerConfig(
        name="test",
        transport="stdio",
        command="echo",
        env=(("KEY", "VALUE"),),
    )
    assert config.env == (("KEY", "VALUE"),)


def test_mcp_tool_provider_creates():
    """MCPToolProvider should be instantiable with server configs."""
    config = MCPServerConfig(name="test", transport="stdio", command="echo")
    provider = MCPToolProvider(servers=[config])
    assert len(provider.servers) == 1


@pytest.mark.asyncio
async def test_discover_tools_returns_tool_definitions():
    """discover_tools should return ToolDefinitions with MCP trust level."""
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"
    mock_tool.inputSchema = {"type": "object", "properties": {}}

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[mock_tool]))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    config = MCPServerConfig(name="test", transport="stdio", command="echo")
    provider = MCPToolProvider(servers=[config])
    provider._sessions = {"test": mock_session}

    tools = await provider.discover_tools()
    assert len(tools) == 1
    assert tools[0].name == "test_tool"
    assert tools[0].trust_level == TrustLevel.MCP
    assert tools[0].source == "mcp://test"


@pytest.mark.asyncio
async def test_discover_tools_caches_results():
    """Second call to discover_tools should use cache."""
    mock_tool = MagicMock()
    mock_tool.name = "cached_tool"
    mock_tool.description = "A cached tool"
    mock_tool.inputSchema = {"type": "object"}

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[mock_tool]))

    config = MCPServerConfig(name="test", transport="stdio", command="echo", cache_tools=True)
    provider = MCPToolProvider(servers=[config])
    provider._sessions = {"test": mock_session}

    tools1 = await provider.discover_tools()
    tools2 = await provider.discover_tools()

    # list_tools should only be called once (cached)
    assert mock_session.list_tools.call_count == 1
    assert len(tools2) == 1


@pytest.mark.asyncio
async def test_discover_tools_handles_list_error():
    """discover_tools should gracefully degrade when list_tools raises."""
    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock(side_effect=RuntimeError("connection lost"))

    config = MCPServerConfig(name="flaky", transport="stdio", command="echo")
    provider = MCPToolProvider(servers=[config])
    provider._sessions = {"flaky": mock_session}

    tools = await provider.discover_tools()
    assert tools == []


@pytest.mark.asyncio
async def test_execute_routes_to_correct_server():
    """execute should route to the server that owns the tool."""
    mock_result = MagicMock()
    mock_result.content = [MagicMock(text="result data")]

    mock_session = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    config = MCPServerConfig(name="test-server", transport="stdio", command="echo")
    provider = MCPToolProvider(servers=[config])
    provider._sessions = {"test-server": mock_session}
    provider._tool_to_server = {"remote_tool": "test-server"}

    result = await provider.execute("remote_tool", {"key": "value"})
    mock_session.call_tool.assert_called_once_with("remote_tool", arguments={"key": "value"})


@pytest.mark.asyncio
async def test_execute_unknown_tool_raises():
    """execute for an unknown tool should raise ValueError."""
    provider = MCPToolProvider(servers=[])
    with pytest.raises(ValueError, match="not found"):
        await provider.execute("nonexistent", {})


@pytest.mark.asyncio
async def test_execute_missing_session_raises():
    """execute should raise ValueError when session is disconnected."""
    provider = MCPToolProvider(servers=[])
    provider._tool_to_server = {"orphan_tool": "dead-server"}

    with pytest.raises(ValueError, match="No active session"):
        await provider.execute("orphan_tool", {})


@pytest.mark.asyncio
async def test_close_cleans_up_sessions():
    """close() should disconnect sessions and clear all internal state."""
    mock_session = AsyncMock()
    mock_session.__aexit__ = AsyncMock(return_value=None)

    provider = MCPToolProvider(servers=[])
    provider._sessions = {"srv": mock_session}
    provider._tool_cache = {"srv": []}
    provider._tool_to_server = {"tool": "srv"}

    await provider.close()

    assert len(provider._sessions) == 0
    assert len(provider._tool_cache) == 0
    assert len(provider._tool_to_server) == 0
    mock_session.__aexit__.assert_called_once()


def test_validate_command_accepts_safe_paths():
    """_validate_command should accept normal executable paths."""
    _validate_command("python")
    _validate_command("node")
    _validate_command("/usr/bin/python3")
    _validate_command("C:/Python312/python.exe")


def test_validate_command_rejects_shell_injection():
    """_validate_command should reject commands with shell metacharacters."""
    with pytest.raises(ValueError, match="disallowed characters"):
        _validate_command("echo hello; rm -rf /")
    with pytest.raises(ValueError, match="disallowed characters"):
        _validate_command("python && malicious")
    with pytest.raises(ValueError, match="disallowed characters"):
        _validate_command("cmd | evil")


def test_mcp_types_exported_from_package():
    """MCPToolProvider and MCPServerConfig should be importable from airees."""
    from airees import MCPToolProvider, MCPServerConfig, TrustLevel
    assert MCPToolProvider is not None
    assert MCPServerConfig is not None
    assert TrustLevel is not None
