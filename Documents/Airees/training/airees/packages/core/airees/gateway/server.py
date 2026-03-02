"""Gateway server — top-level entry point for multi-channel message routing.

The :class:`Gateway` wires adapters to the :class:`ConversationManager`,
forwarding inbound messages, sending outbound replies, and managing the
adapter lifecycle.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from airees.gateway.adapter import AdapterRegistry
from airees.gateway.conversation import ConversationManager
from airees.gateway.types import InboundMessage, OutboundMessage

log = logging.getLogger(__name__)


@dataclass
class Gateway:
    """Multi-channel gateway that routes messages through the conversation pipeline.

    Attributes:
        conversation_manager: Orchestrates message handling and model routing.
        adapters: Registry of channel adapters (CLI, Telegram, etc.).
    """

    conversation_manager: ConversationManager
    adapters: AdapterRegistry = field(default_factory=AdapterRegistry)

    async def start(self) -> None:
        """Wire message handlers and start all registered adapters."""
        for channel in self.adapters.channels:
            adapter = self.adapters.get(channel)
            if adapter is not None:
                adapter.set_message_handler(self._make_handler())
        await self.adapters.start_all()
        log.info(
            "Gateway started with %d adapter(s): %s",
            len(self.adapters.channels),
            ", ".join(self.adapters.channels),
        )

    async def stop(self) -> None:
        """Stop all registered adapters."""
        await self.adapters.stop_all()
        log.info("Gateway stopped")

    async def handle_message(self, message: InboundMessage) -> OutboundMessage:
        """Process an inbound message and deliver the response.

        1. Delegate to :meth:`ConversationManager.handle` for routing.
        2. Look up the channel adapter and call ``send`` if found.
        3. Return the response regardless of adapter availability.
        """
        response = await self.conversation_manager.handle(message)

        adapter = self.adapters.get(message.channel)
        if adapter is not None:
            await adapter.send(response)
        else:
            log.warning(
                "No adapter registered for channel '%s' — response not delivered",
                message.channel,
            )

        return response

    def _make_handler(self):
        """Create an async handler closure for adapter message callbacks."""

        async def _handler(message: InboundMessage) -> None:
            await self.handle_message(message)

        return _handler
