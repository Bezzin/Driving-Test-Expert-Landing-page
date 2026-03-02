"""MCP tool provider — discovers and executes tools from MCP servers.

Currently supports stdio transport. SSE and streamable HTTP transport
support is planned for a future release. Tools are cached by default
for static servers. Each tool gets TrustLevel.MCP.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from airees.tools.registry import ToolDefinition, TrustLevel

logger = logging.getLogger(__name__)

_SAFE_COMMAND_RE = re.compile(r"^[a-zA-Z0-9_./@: -]+$")

TOOL_EXECUTION_TIMEOUT = 30.0


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for a single MCP server connection."""

    name: str
    transport: str  # "stdio" | "sse" | "streamable_http"
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    env: tuple[tuple[str, str], ...] = ()
    cache_tools: bool = True


@dataclass
class MCPToolProvider:
    """Connects to MCP servers, discovers tools, provides execution.

    Tools are discovered via list_tools() on each server session.
    Execution is routed to the server that owns the requested tool.
    """

    servers: list[MCPServerConfig]
    _sessions: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _transports: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
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
                    _validate_command(server.command)
                    env_dict = dict(server.env) if server.env else None
                    params = StdioServerParameters(
                        command=server.command,
                        args=list(server.args),
                        env=env_dict,
                    )
                    transport_cm = stdio_client(params)
                    read_stream, write_stream = await transport_cm.__aenter__()
                    try:
                        session = ClientSession(read_stream, write_stream)
                        await session.__aenter__()
                        try:
                            await session.initialize()
                        except Exception:
                            await session.__aexit__(None, None, None)
                            raise
                    except Exception:
                        await transport_cm.__aexit__(None, None, None)
                        raise
                    self._transports[server.name] = transport_cm
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
                    existing = self._tool_to_server.get(tool.name)
                    if existing is not None and existing != server.name:
                        logger.warning(
                            "Tool '%s' from server '%s' shadows same-named tool from '%s'",
                            tool.name, server.name, existing,
                        )
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
            TimeoutError: If the tool execution exceeds the timeout.
        """
        server_name = self._tool_to_server.get(tool_name)
        if server_name is None:
            raise ValueError(f"Tool '{tool_name}' not found on any MCP server")

        session = self._sessions.get(server_name)
        if session is None:
            raise ValueError(f"No active session for server '{server_name}'")

        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments=tool_input),
                timeout=TOOL_EXECUTION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Tool '{tool_name}' on server '{server_name}' "
                f"timed out after {TOOL_EXECUTION_TIMEOUT}s"
            )

        # Extract text from result content blocks
        texts = []
        for content in result.content:
            if hasattr(content, "text"):
                texts.append(content.text)
        return "\n".join(texts) if texts else str(result)

    def get_tools(self) -> list[ToolDefinition]:
        """Return all cached tool definitions (sync accessor)."""
        tools: list[ToolDefinition] = []
        for server_tools in self._tool_cache.values():
            tools.extend(server_tools)
        return tools

    async def close(self) -> None:
        """Disconnect all MCP server sessions and transports."""
        sessions = dict(self._sessions)
        transports = dict(self._transports)
        try:
            for name, session in sessions.items():
                try:
                    await session.__aexit__(None, None, None)
                    logger.info("Disconnected from MCP server: %s", name)
                except Exception as e:
                    logger.warning("Error closing session '%s': %s", name, e)
                transport = transports.get(name)
                if transport:
                    try:
                        await transport.__aexit__(None, None, None)
                    except Exception as e:
                        logger.warning("Error closing transport '%s': %s", name, e)
        finally:
            self._sessions.clear()
            self._transports.clear()
            self._tool_cache.clear()
            self._tool_to_server.clear()


def _validate_command(command: str) -> None:
    """Validate that command is a simple executable path, not a shell expression."""
    if not _SAFE_COMMAND_RE.match(command):
        raise ValueError(
            f"MCP server command contains disallowed characters: {command!r}. "
            "Use args for parameters instead of embedding them in command."
        )
