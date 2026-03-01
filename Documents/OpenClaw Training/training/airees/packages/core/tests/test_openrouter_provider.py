"""Tests for the OpenRouter provider.

Verifies that OpenRouterProvider correctly initialises, constructs
payloads for the OpenRouter chat-completions endpoint, and delegates
HTTP calls to httpx.AsyncClient.  Asserts on the normalised response
shape (_NormalisedResponse) rather than raw OpenAI JSON.
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
async def test_create_message_returns_normalised_response(provider: OpenRouterProvider):
    mock_json = {
        "choices": [{"message": {"content": "Hello from DeepSeek"}, "finish_reason": "stop"}],
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
        assert result.content[0].text == "Hello from DeepSeek"
        assert result.content[0].type == "text"
        assert result.stop_reason == "end_turn"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 5


@pytest.mark.asyncio
async def test_create_message_includes_system_prompt(provider: OpenRouterProvider):
    """The system prompt should be prepended as the first message."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
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
async def test_create_message_converts_tools_to_openai_format(provider: OpenRouterProvider):
    """Anthropic-format tools should be converted to OpenAI function-calling format."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "tool call"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3},
    }
    mock_response.raise_for_status = MagicMock()

    # Anthropic tool format (input from Runner)
    anthropic_tools = [
        {
            "name": "get_weather",
            "description": "Get weather for a city",
            "input_schema": {"type": "object", "properties": {}},
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
            tools=anthropic_tools,
        )
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        # Should be converted to OpenAI format
        assert payload["tools"] == [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]


@pytest.mark.asyncio
async def test_create_message_omits_tools_when_none(provider: OpenRouterProvider):
    """When tools is None, the payload should not contain a 'tools' key."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
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
async def test_create_message_includes_provider_preferences(provider: OpenRouterProvider):
    """Payload should include OpenRouter provider preferences."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
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
        assert payload["provider"]["sort"] == "price"
        assert payload["provider"]["allow_fallbacks"] is True


@pytest.mark.asyncio
async def test_create_message_respects_max_tokens(provider: OpenRouterProvider):
    """An explicit max_tokens argument should override the ModelConfig default."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
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
async def test_normalises_tool_use_response(provider: OpenRouterProvider):
    """Tool call responses should be normalised to Anthropic-style tool_use blocks."""
    mock_json = {
        "choices": [{
            "message": {
                "content": None,
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "London"}',
                    },
                }],
            },
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8},
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
            messages=[{"role": "user", "content": "Weather?"}],
        )
        assert result.stop_reason == "tool_use"
        assert len(result.content) == 1
        block = result.content[0]
        assert block.type == "tool_use"
        assert block.id == "call_123"
        assert block.name == "get_weather"
        assert block.input == {"city": "London"}


@pytest.mark.asyncio
async def test_close_closes_http_client(provider: OpenRouterProvider):
    """Calling close() should close the underlying httpx client."""
    with patch.object(
        provider._client, "aclose", new_callable=AsyncMock
    ) as mock_aclose:
        await provider.close()
        mock_aclose.assert_awaited_once()
