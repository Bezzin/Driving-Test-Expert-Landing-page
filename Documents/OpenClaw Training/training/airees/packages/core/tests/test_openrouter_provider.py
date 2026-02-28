"""Tests for the OpenRouter provider.

Verifies that OpenRouterProvider correctly initialises, constructs
payloads for the OpenRouter chat-completions endpoint, and delegates
HTTP calls to httpx.AsyncClient.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from airees.router.openrouter_provider import OpenRouterProvider
from airees.router.types import ModelConfig, ProviderType


@pytest.fixture
def provider():
    return OpenRouterProvider(api_key="test-or-key")


def test_provider_creation(provider: OpenRouterProvider):
    assert provider.api_key == "test-or-key"
    assert provider.provider_type == ProviderType.OPENROUTER


def test_provider_has_http_client(provider: OpenRouterProvider):
    """The provider should initialise an httpx.AsyncClient internally."""
    import httpx

    assert isinstance(provider._client, httpx.AsyncClient)


@pytest.mark.asyncio
async def test_create_message_calls_openrouter(provider: OpenRouterProvider):
    mock_json = {
        "choices": [{"message": {"content": "Hello from DeepSeek"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "deepseek/deepseek-r1",
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_json
    mock_response.raise_for_status = MagicMock()

    with patch.object(
        provider._client,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await provider.create_message(
            model=ModelConfig(
                model_id="deepseek/deepseek-r1",
                provider=ProviderType.OPENROUTER,
            ),
            system="You are helpful",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result["choices"][0]["message"]["content"] == "Hello from DeepSeek"


@pytest.mark.asyncio
async def test_create_message_includes_system_prompt(provider: OpenRouterProvider):
    """The system prompt should be prepended as the first message."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        "model": "deepseek/deepseek-r1",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(
        provider._client,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_post:
        await provider.create_message(
            model=ModelConfig(
                model_id="deepseek/deepseek-r1",
                provider=ProviderType.OPENROUTER,
            ),
            system="Be concise",
            messages=[{"role": "user", "content": "Hi"}],
        )
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["messages"][0] == {
            "role": "system",
            "content": "Be concise",
        }
        assert payload["messages"][1] == {"role": "user", "content": "Hi"}


@pytest.mark.asyncio
async def test_create_message_forwards_tools(provider: OpenRouterProvider):
    """When tools are provided they should appear in the request payload."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "tool call"}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3},
        "model": "deepseek/deepseek-r1",
    }
    mock_response.raise_for_status = MagicMock()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a city",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    with patch.object(
        provider._client,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_post:
        await provider.create_message(
            model=ModelConfig(
                model_id="deepseek/deepseek-r1",
                provider=ProviderType.OPENROUTER,
            ),
            system="You are helpful",
            messages=[{"role": "user", "content": "Weather?"}],
            tools=tools,
        )
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["tools"] == tools


@pytest.mark.asyncio
async def test_create_message_omits_tools_when_none(provider: OpenRouterProvider):
    """When tools is None, the payload should not contain a 'tools' key."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        "model": "deepseek/deepseek-r1",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(
        provider._client,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_post:
        await provider.create_message(
            model=ModelConfig(
                model_id="deepseek/deepseek-r1",
                provider=ProviderType.OPENROUTER,
            ),
            system="You are helpful",
            messages=[{"role": "user", "content": "Hi"}],
        )
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "tools" not in payload


@pytest.mark.asyncio
async def test_create_message_respects_max_tokens(provider: OpenRouterProvider):
    """An explicit max_tokens argument should override the ModelConfig default."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        "model": "deepseek/deepseek-r1",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(
        provider._client,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_post:
        await provider.create_message(
            model=ModelConfig(
                model_id="deepseek/deepseek-r1",
                provider=ProviderType.OPENROUTER,
            ),
            system="You are helpful",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=2048,
        )
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_close_closes_http_client(provider: OpenRouterProvider):
    """Calling close() should close the underlying httpx client."""
    with patch.object(
        provider._client, "aclose", new_callable=AsyncMock
    ) as mock_aclose:
        await provider.close()
        mock_aclose.assert_awaited_once()
