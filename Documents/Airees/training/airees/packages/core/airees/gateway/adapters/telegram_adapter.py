"""Telegram channel adapter — bridges python-telegram-bot to the Airees gateway.

The ``python-telegram-bot`` library is an optional dependency.  Importing
this module is safe, but calling :meth:`TelegramAdapter.start` without the
library installed will raise a clear :class:`ImportError`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from airees.gateway.adapter import MessageHandler
from airees.gateway.types import InboundMessage, OutboundMessage

log = logging.getLogger(__name__)


@dataclass
class TelegramAdapter:
    """Channel adapter for Telegram via ``python-telegram-bot``.

    Attributes:
        bot_token: Telegram Bot API token (from @BotFather).
        name: Channel identifier, always ``"telegram"``.
        allowed_user_ids: Tuple of Telegram user IDs permitted to interact.
            An empty tuple means all users are allowed.
        voice_enabled: When ``True``, the adapter will accept voice messages
            and route them through the STT/TTS pipeline.  Defaults to ``False``.
    """

    bot_token: str
    name: str = field(default="telegram", init=False)
    allowed_user_ids: tuple[int, ...] = ()
    voice_enabled: bool = False
    _handler: MessageHandler | None = field(default=None, init=False, repr=False)
    _bot: Any = field(default=None, init=False, repr=False)
    _application: Any = field(default=None, init=False, repr=False)
    _stt: Any = field(default=None, init=False, repr=False)
    _tts: Any = field(default=None, init=False, repr=False)

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Register the callback invoked for each inbound message."""
        self._handler = handler

    def _get_stt(self):
        """Lazy-load SpeechToText."""
        if self._stt is None:
            from airees.voice.stt import SpeechToText
            self._stt = SpeechToText()
        return self._stt

    def _get_tts(self):
        """Lazy-load TextToSpeech."""
        if self._tts is None:
            from airees.voice.tts import TextToSpeech
            self._tts = TextToSpeech()
        return self._tts

    async def start(self) -> None:
        """Initialize the Telegram bot and start polling.

        Raises:
            ImportError: If ``python-telegram-bot`` is not installed.
        """
        try:
            from telegram import Bot
            from telegram.ext import ApplicationBuilder, MessageHandler as TGHandler
            from telegram.ext.filters import TEXT
        except ImportError as exc:
            raise ImportError(
                "python-telegram-bot is required for TelegramAdapter. "
                "Install it with: pip install 'airees-core[telegram]'"
            ) from exc

        self._application = (
            ApplicationBuilder().token(self.bot_token).build()
        )
        self._bot = self._application.bot

        self._application.add_handler(
            TGHandler(TEXT, self._on_message)
        )

        log.info("TelegramAdapter starting with bot token %s****", self.bot_token[:4])
        await self._application.initialize()
        await self._application.start()
        await self._application.updater.start_polling()

    async def stop(self) -> None:
        """Stop the Telegram bot and clean up."""
        if self._application is not None:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
            log.info("TelegramAdapter stopped")

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to a Telegram chat.

        Args:
            message: Outbound message with ``recipient_id`` as the Telegram chat ID.
        """
        if self._bot is None:
            log.warning("Cannot send — bot not initialised")
            return
        await self._bot.send_message(
            chat_id=int(message.recipient_id), text=message.text
        )

    def _build_inbound(self, message: Any) -> InboundMessage:
        """Convert a ``telegram.Message`` object to an :class:`InboundMessage`."""
        return InboundMessage(
            channel="telegram",
            sender_id=str(message.chat.id),
            text=message.text or "",
            metadata={"message_id": message.message_id},
        )

    async def _on_message(self, update: Any, context: Any) -> None:
        """Handler called by python-telegram-bot for each incoming text message."""
        if update.message is None:
            return

        user_id = update.message.chat.id
        if self.allowed_user_ids and user_id not in self.allowed_user_ids:
            log.warning("Blocked message from unauthorised user %d", user_id)
            return

        inbound = self._build_inbound(update.message)
        if self._handler is not None:
            await self._handler(inbound)
