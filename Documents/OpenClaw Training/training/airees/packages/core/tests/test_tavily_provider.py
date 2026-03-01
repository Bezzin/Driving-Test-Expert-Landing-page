"""Tests for the Tavily tool provider."""
import json
import os
import pytest
from unittest.mock import MagicMock, patch
from airees.tools.providers.tavily import TavilyToolProvider


def test_get_tools_returns_definitions():
    provider = TavilyToolProvider(api_key="test-key")
    tools = provider.get_tools()
    assert len(tools) == 2
    names = [t.name for t in tools]
    assert "web_search" in names
    assert "web_extract" in names


def test_get_tools_empty_when_no_key():
    provider = TavilyToolProvider(api_key="")
    tools = provider.get_tools()
    assert tools == []


def test_web_search_tool_schema():
    provider = TavilyToolProvider(api_key="test-key")
    tools = provider.get_tools()
    search_tool = next(t for t in tools if t.name == "web_search")
    assert "query" in search_tool.input_schema["properties"]
    assert "max_results" in search_tool.input_schema["properties"]


def test_web_extract_tool_schema():
    provider = TavilyToolProvider(api_key="test-key")
    tools = provider.get_tools()
    extract_tool = next(t for t in tools if t.name == "web_extract")
    assert "urls" in extract_tool.input_schema["properties"]


@pytest.mark.asyncio
async def test_execute_web_search():
    provider = TavilyToolProvider(api_key="test-key")
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [{"title": "Result 1", "url": "https://example.com", "content": "Info"}]
    }
    provider._client = mock_client
    result = await provider.execute("web_search", {"query": "test"})
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Result 1"
    mock_client.search.assert_called_once_with(query="test")


@pytest.mark.asyncio
async def test_execute_web_extract():
    provider = TavilyToolProvider(api_key="test-key")
    mock_client = MagicMock()
    mock_client.extract.return_value = {
        "results": [{"url": "https://example.com", "raw_content": "Page content"}]
    }
    provider._client = mock_client
    result = await provider.execute("web_extract", {"urls": ["https://example.com"]})
    parsed = json.loads(result)
    assert parsed[0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    provider = TavilyToolProvider(api_key="test-key")
    with pytest.raises(ValueError, match="Unknown tool"):
        await provider.execute("unknown_tool", {})


def test_from_env_returns_none_when_not_set():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("TAVILY_API_KEY", None)
        provider = TavilyToolProvider.from_env()
        assert provider is None


def test_from_env_returns_provider_when_set():
    with patch.dict(os.environ, {"TAVILY_API_KEY": "tvly-test"}):
        provider = TavilyToolProvider.from_env()
        assert provider is not None
        assert provider.api_key == "tvly-test"
