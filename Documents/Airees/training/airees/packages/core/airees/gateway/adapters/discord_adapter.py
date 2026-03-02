"""Discord channel adapter — bridges discord.py to the Airees gateway.

The ``discord.py`` library is an optional dependency.  Importing this module
is safe, but calling :meth:`DiscordAdapter.start` without the library
installed will raise a clear :class:`ImportError`.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from airees.gateway.adapter import MessageHandler
from airees.gateway.types import InboundMessage, OutboundMessage

log = logging.getLogger(__name__)


@dataclass
class DiscordAdapter:
    """Channel adapter for Discord via ``discord.py``.

    Attributes:
        bot_token: Discord bot token (from Discord Developer Portal).
        name: Channel identifier, always ``"discord"``.
    """

    bot_token: str = field(repr=False)
    name: str = field(default="discord", init=False)
    _handler: MessageHandler | None = field(default=None, init=False, repr=False)
    _bot: Any = field(default=None, init=False, repr=False)
    _task: Any = field(default=None, init=False, repr=False)

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Register the callback invoked for each inbound message."""
        self._handler = handler

    def _build_inbound(self, message: Any) -> InboundMessage:
        """Convert a ``discord.Message`` object to an :class:`InboundMessage`."""
        return InboundMessage(
            channel="discord",
            sender_id=str(message.author.id),
            text=message.content,
            metadata={
                "guild_id": str(message.guild.id) if message.guild else "dm",
                "channel_id": str(message.channel.id),
            },
        )

    async def start(self) -> None:
        """Initialize the Discord bot and begin listening.

        Raises:
            ImportError: If ``discord.py`` is not installed.
        """
        try:
            import discord  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "discord.py is required for the Discord adapter. "
                "Install it with: pip install 'airees-core[discord]'"
            ) from exc

        intents = discord.Intents.default()
        intents.message_content = True
        self._bot = discord.Client(intents=intents)

        adapter = self

        @self._bot.event
        async def on_message(message: discord.Message) -> None:
            if message.author == adapter._bot.user:
                return
            if adapter._handler is not None:
                inbound = adapter._build_inbound(message)
                await adapter._handler(inbound)

        # Run bot in background (non-blocking)
        self._task = asyncio.create_task(self._bot.start(self.bot_token))
        self._task.add_done_callback(self._on_bot_done)
        log.info("Discord adapter started")

    def _on_bot_done(self, task: Any) -> None:
        """Log errors from the background bot task."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            log.error("Discord bot crashed: %s", exc)

    async def stop(self) -> None:
        """Stop the Discord bot and clean up."""
        if self._bot is not None:
            await self._bot.close()
        if self._task is not None and not self._task.done():
            self._task.cancel()
        log.info("Discord adapter stopped")

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to a Discord channel or user DM.

        If ``message.metadata`` contains a ``channel_id``, the adapter
        attempts to send to that channel first.  If the channel cannot be
        resolved, it falls back to a direct message to ``recipient_id``.

        Args:
            message: Outbound message to deliver.
        """
        if self._bot is None:
            log.warning("Discord bot not started — cannot send message")
            return

        try:
            channel_id = message.metadata.get("channel_id")
            channel = (
                self._bot.get_channel(int(channel_id))
                if channel_id
                else None
            )
            if channel is None:
                user = await self._bot.fetch_user(int(message.recipient_id))
                channel = await user.create_dm()
            await channel.send(message.text)
        except Exception as exc:
            log.error("Failed to send Discord message: %s", exc, exc_info=True)
