"""Tavily tool provider — web search and content extraction for workers."""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

from airees.tools.registry import ToolDefinition


@dataclass
class TavilyToolProvider:
    """Wraps the Tavily API as tools workers can call via tool_use.

    Exposes web_search and web_extract. If api_key is empty, get_tools()
    returns an empty list (graceful degradation).
    """

    api_key: str
    _client: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.api_key:
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=self.api_key)

    @classmethod
    def from_env(cls) -> TavilyToolProvider | None:
        """Create a provider from TAVILY_API_KEY env var. Returns None if not set."""
        key = os.environ.get("TAVILY_API_KEY", "")
        if not key:
            return None
        return cls(api_key=key)

    def get_tools(self) -> list[ToolDefinition]:
        """Return tool definitions for LLM tool_use. Empty list if no key."""
        if not self.api_key:
            return []
        return [
            ToolDefinition(
                name="web_search",
                description=(
                    "Search the web for current information. Returns ranked "
                    "results with titles, URLs, and content snippets."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results (default 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            ToolDefinition(
                name="web_extract",
                description=(
                    "Extract content from one or more URLs. Returns the full "
                    "page content as text."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs to extract (max 20)",
                        },
                    },
                    "required": ["urls"],
                },
            ),
        ]

    async def execute(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call and return JSON string result."""
        if tool_name == "web_search":
            result = await asyncio.to_thread(self._client.search, **tool_input)
            return json.dumps(result.get("results", []), indent=2)
        elif tool_name == "web_extract":
            result = await asyncio.to_thread(
                self._client.extract, urls=tool_input["urls"]
            )
            return json.dumps(result.get("results", []), indent=2)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
