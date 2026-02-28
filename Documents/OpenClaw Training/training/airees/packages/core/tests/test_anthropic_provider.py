"""Tests for the Anthropic provider — wraps AsyncAnthropic for Claude API calls.

Validates provider creation, type assignment, message creation delegation,
tool forwarding, and custom max_tokens override behavior.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from airees.router.anthropic_provider import AnthropicProvider
from airees.router.types import ModelConfig, ProviderType


@pytest.fixture
def provider():
    return AnthropicProvider(api_key="test-key")


def test_provider_creation(provider):
    assert provider.api_key == "test-key"
    assert provider.provider_type == ProviderType.ANTHROPIC


def test_provider_creates_async_client(provider):
    import anthropic

    assert isinstance(provider._client, anthropic.AsyncAnthropic)


@pytest.mark.asyncio
async def test_create_message_calls_anthropic(provider):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Hello")]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
    mock_response.stop_reason = "end_turn"
    mock_response.model = "claude-sonnet-4-6"

    with patch.object(
        provider._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await provider.create_message(
            model=ModelConfig(model_id="claude-sonnet-4-6"),
            system="You are helpful",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result.content[0].text == "Hello"


@pytest.mark.asyncio
async def test_create_message_passes_model_id(provider):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="OK")]

    with patch.object(
        provider._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_create:
        await provider.create_message(
            model=ModelConfig(model_id="claude-sonnet-4-6"),
            system="system prompt",
            messages=[{"role": "user", "content": "ping"}],
        )
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"
        assert call_kwargs["system"] == "system prompt"
        assert call_kwargs["messages"] == [{"role": "user", "content": "ping"}]


@pytest.mark.asyncio
async def test_create_message_uses_model_default_max_tokens(provider):
    mock_response = MagicMock()

    with patch.object(
        provider._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_create:
        await provider.create_message(
            model=ModelConfig(model_id="claude-sonnet-4-6", max_tokens=8192),
            system="sys",
            messages=[{"role": "user", "content": "test"}],
        )
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["max_tokens"] == 8192


@pytest.mark.asyncio
async def test_create_message_override_max_tokens(provider):
    mock_response = MagicMock()

    with patch.object(
        provider._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_create:
        await provider.create_message(
            model=ModelConfig(model_id="claude-sonnet-4-6", max_tokens=4096),
            system="sys",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=2048,
        )
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_create_message_forwards_tools(provider):
    mock_response = MagicMock()
    tools = [{"name": "get_weather", "description": "Get weather", "input_schema": {}}]

    with patch.object(
        provider._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_create:
        await provider.create_message(
            model=ModelConfig(model_id="claude-sonnet-4-6"),
            system="sys",
            messages=[{"role": "user", "content": "weather?"}],
            tools=tools,
        )
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["tools"] == tools


@pytest.mark.asyncio
async def test_create_message_omits_tools_when_none(provider):
    mock_response = MagicMock()

    with patch.object(
        provider._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_create:
        await provider.create_message(
            model=ModelConfig(model_id="claude-sonnet-4-6"),
            system="sys",
            messages=[{"role": "user", "content": "hello"}],
        )
        call_kwargs = mock_create.call_args[1]
        assert "tools" not in call_kwargs
