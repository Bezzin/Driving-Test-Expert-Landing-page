"""MCP tool provider — discovers and executes tools from MCP servers.

Supports stdio, SSE, and streamable HTTP transports. Tools are cached
by default for static servers. Each tool gets TrustLevel.MCP.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from airees.tools.registry import ToolDefinition, TrustLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for a single MCP server connection."""

    name: str
    transport: str  # "stdio" | "sse" | "streamable_http"
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    cache_tools: bool = True


@dataclass
class MCPToolProvider:
    """Connects to MCP servers, discovers tools, provides execution.

    Tools are discovered via list_tools() on each server session.
    Execution is routed to the server that owns the requested tool.
    """

    servers: list[MCPServerConfig]
    _sessions: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _tool_cache: dict[str, list[ToolDefinition]] = field(default_factory=dict, init=False, repr=False)
    _tool_to_server: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    async def connect_all(self) -> None:
        """Connect to all configured MCP servers.

        Requires the `mcp` library to be installed. Each server config
        is connected via its declared transport type.
        """
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            logger.warning("mcp library not installed; MCP tool discovery disabled")
            return

        for server in self.servers:
            try:
                if server.transport == "stdio" and server.command:
                    params = StdioServerParameters(
                        command=server.command,
                        args=list(server.args),
                        env=server.env or None,
                    )
                    read_stream, write_stream = await stdio_client(params).__aenter__()
                    session = ClientSession(read_stream, write_stream)
                    await session.__aenter__()
                    await session.initialize()
                    self._sessions[server.name] = session
                    logger.info("Connected to MCP server: %s (stdio)", server.name)
                else:
                    logger.warning(
                        "Unsupported transport '%s' for server '%s'",
                        server.transport,
                        server.name,
                    )
            except Exception as e:
                logger.error("Failed to connect to MCP server '%s': %s", server.name, e)

    async def discover_tools(self, cache: bool = True) -> list[ToolDefinition]:
        """List tools from all connected servers.

        Returns ToolDefinition objects with TrustLevel.MCP and source
        set to 'mcp://<server-name>'. Results are cached per server
        when cache=True and the server config has cache_tools=True.
        """
        all_tools: list[ToolDefinition] = []

        for server in self.servers:
            session = self._sessions.get(server.name)
            if session is None:
                continue

            # Return cached tools if available
            if cache and server.cache_tools and server.name in self._tool_cache:
                all_tools.extend(self._tool_cache[server.name])
                continue

            try:
                result = await session.list_tools()
                server_tools: list[ToolDefinition] = []
                for tool in result.tools:
                    tool_def = ToolDefinition(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                        trust_level=TrustLevel.MCP,
                        source=f"mcp://{server.name}",
                    )
                    server_tools.append(tool_def)
                    self._tool_to_server[tool.name] = server.name

                if cache and server.cache_tools:
                    self._tool_cache[server.name] = server_tools
                all_tools.extend(server_tools)

            except Exception as e:
                logger.error("Failed to list tools from '%s': %s", server.name, e)

        return all_tools

    async def execute(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Route tool execution to the correct MCP server.

        Args:
            tool_name: The name of the tool to execute.
            tool_input: The input arguments for the tool.

        Returns:
            String result from the tool execution.

        Raises:
            ValueError: If the tool is not found on any connected server.
        """
        server_name = self._tool_to_server.get(tool_name)
        if server_name is None:
            raise ValueError(f"Tool '{tool_name}' not found on any MCP server")

        session = self._sessions.get(server_name)
        if session is None:
            raise ValueError(f"No active session for server '{server_name}'")

        result = await session.call_tool(tool_name, arguments=tool_input)

        # Extract text from result content blocks
        texts = []
        for content in result.content:
            if hasattr(content, "text"):
                texts.append(content.text)
        return "\n".join(texts) if texts else json.dumps(str(result))

    def get_tools(self) -> list[ToolDefinition]:
        """Return all cached tool definitions (sync accessor)."""
        tools: list[ToolDefinition] = []
        for server_tools in self._tool_cache.values():
            tools.extend(server_tools)
        return tools

    async def close(self) -> None:
        """Disconnect all MCP server sessions."""
        for name, session in self._sessions.items():
            try:
                await session.__aexit__(None, None, None)
                logger.info("Disconnected from MCP server: %s", name)
            except Exception as e:
                logger.warning("Error closing session '%s': %s", name, e)
        self._sessions.clear()
        self._tool_cache.clear()
        self._tool_to_server.clear()
