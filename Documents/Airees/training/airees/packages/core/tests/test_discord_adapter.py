"""Tests for DiscordAdapter — structural tests (no live Discord)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from airees.gateway.types import InboundMessage, OutboundMessage


# -- Structural tests ---------------------------------------------------------


def test_discord_adapter_name() -> None:
    """DiscordAdapter has name='discord'."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="fake-token")
    assert adapter.name == "discord"


def test_discord_adapter_requires_token() -> None:
    """DiscordAdapter() without bot_token raises TypeError."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    with pytest.raises(TypeError):
        DiscordAdapter()  # type: ignore[call-arg]


def test_discord_adapter_stores_token() -> None:
    """DiscordAdapter stores the bot_token."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="my-secret-token")
    assert adapter.bot_token == "my-secret-token"


def test_discord_set_message_handler() -> None:
    """set_message_handler stores the callback."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="fake-token")

    async def my_handler(msg: InboundMessage) -> None:
        pass

    adapter.set_message_handler(my_handler)
    assert adapter._handler is my_handler


def test_discord_build_inbound() -> None:
    """_build_inbound converts a discord-like message to InboundMessage."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="tok")

    mock_msg = MagicMock()
    mock_msg.author.id = 98765
    mock_msg.content = "Hello from Discord"
    mock_msg.guild.id = 11111
    mock_msg.channel.id = 22222

    result = adapter._build_inbound(mock_msg)
    assert isinstance(result, InboundMessage)
    assert result.channel == "discord"
    assert result.sender_id == "98765"
    assert result.text == "Hello from Discord"
    assert result.metadata["guild_id"] == "11111"
    assert result.metadata["channel_id"] == "22222"


def test_discord_build_inbound_dm() -> None:
    """_build_inbound handles DM (guild is None)."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="tok")

    mock_msg = MagicMock()
    mock_msg.author.id = 98765
    mock_msg.content = "DM message"
    mock_msg.guild = None
    mock_msg.channel.id = 33333

    result = adapter._build_inbound(mock_msg)
    assert result.metadata["guild_id"] == "dm"
    assert result.metadata["channel_id"] == "33333"


# -- Async tests --------------------------------------------------------------


@pytest.mark.asyncio
async def test_discord_send_without_bot() -> None:
    """send() before start() logs a warning but doesn't crash."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="fake-token")
    msg = OutboundMessage(channel="discord", recipient_id="12345", text="hello")
    # Should not raise
    await adapter.send(msg)


@pytest.mark.asyncio
async def test_discord_send_to_channel() -> None:
    """send() with a channel_id in metadata sends to that channel."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="tok")
    mock_channel = AsyncMock()
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel
    adapter._bot = mock_bot

    msg = OutboundMessage(
        channel="discord",
        recipient_id="12345",
        text="Reply!",
        metadata={"channel_id": "22222"},
    )
    await adapter.send(msg)

    mock_bot.get_channel.assert_called_once_with(22222)
    mock_channel.send.assert_awaited_once_with("Reply!")


@pytest.mark.asyncio
async def test_discord_send_falls_back_to_dm() -> None:
    """send() falls back to DM when get_channel returns None."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="tok")
    mock_dm_channel = AsyncMock()
    mock_user = AsyncMock()
    mock_user.create_dm.return_value = mock_dm_channel
    mock_bot = AsyncMock()
    mock_bot.get_channel.return_value = None
    mock_bot.fetch_user.return_value = mock_user
    adapter._bot = mock_bot

    msg = OutboundMessage(
        channel="discord",
        recipient_id="12345",
        text="DM fallback!",
    )
    await adapter.send(msg)

    mock_bot.fetch_user.assert_awaited_once_with(12345)
    mock_user.create_dm.assert_awaited_once()
    mock_dm_channel.send.assert_awaited_once_with("DM fallback!")


@pytest.mark.asyncio
async def test_discord_stop_before_start() -> None:
    """stop() before start() is a no-op."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="fake-token")
    # Should not raise
    await adapter.stop()


@pytest.mark.asyncio
async def test_discord_stop_closes_bot() -> None:
    """stop() closes the underlying bot client."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="tok")
    mock_bot = AsyncMock()
    adapter._bot = mock_bot

    await adapter.stop()
    mock_bot.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_discord_start_without_discordpy() -> None:
    """start() raises ImportError when discord.py is missing."""
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="tok")

    import sys
    # Temporarily block discord import
    original = sys.modules.get("discord")
    sys.modules["discord"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(ImportError, match="discord.py is required"):
            await adapter.start()
    finally:
        if original is not None:
            sys.modules["discord"] = original
        else:
            sys.modules.pop("discord", None)


def test_discord_satisfies_channel_adapter_protocol() -> None:
    """DiscordAdapter satisfies the ChannelAdapter runtime protocol."""
    from airees.gateway.adapter import ChannelAdapter
    from airees.gateway.adapters.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(bot_token="tok")
    assert isinstance(adapter, ChannelAdapter)
