"""Tests for gateway.adapters.telegram_adapter — TelegramAdapter (mocked)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from airees.gateway.types import InboundMessage, OutboundMessage


# -- Tests -------------------------------------------------------------------


def test_telegram_adapter_name() -> None:
    """TelegramAdapter has name='telegram'."""
    from airees.gateway.adapters.telegram_adapter import TelegramAdapter

    adapter = TelegramAdapter(bot_token="test-token-123")
    assert adapter.name == "telegram"


def test_telegram_adapter_requires_token() -> None:
    """TelegramAdapter requires a bot_token."""
    from airees.gateway.adapters.telegram_adapter import TelegramAdapter

    adapter = TelegramAdapter(bot_token="my-secret-token")
    assert adapter.bot_token == "my-secret-token"


def test_telegram_build_inbound() -> None:
    """_build_inbound converts a telegram-like message object to InboundMessage."""
    from airees.gateway.adapters.telegram_adapter import TelegramAdapter

    adapter = TelegramAdapter(bot_token="tok")

    # Create a mock telegram message
    mock_msg = MagicMock()
    mock_msg.chat.id = 12345
    mock_msg.text = "Hello from Telegram"
    mock_msg.message_id = 99

    result = adapter._build_inbound(mock_msg)
    assert isinstance(result, InboundMessage)
    assert result.channel == "telegram"
    assert result.sender_id == "12345"
    assert result.text == "Hello from Telegram"


@pytest.mark.asyncio
async def test_telegram_send_calls_bot() -> None:
    """send() calls self._bot.send_message with the right arguments."""
    from airees.gateway.adapters.telegram_adapter import TelegramAdapter

    adapter = TelegramAdapter(bot_token="tok")
    adapter._bot = AsyncMock()

    msg = OutboundMessage(channel="telegram", recipient_id="12345", text="Reply!")
    await adapter.send(msg)

    adapter._bot.send_message.assert_awaited_once_with(
        chat_id=12345, text="Reply!"
    )


def test_telegram_set_message_handler() -> None:
    """set_message_handler stores the callback."""
    from airees.gateway.adapters.telegram_adapter import TelegramAdapter

    adapter = TelegramAdapter(bot_token="tok")

    async def my_handler(msg: InboundMessage) -> None:
        pass

    adapter.set_message_handler(my_handler)
    assert adapter._handler is my_handler
