"""Tests for gateway.server — Gateway dataclass."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock

import pytest

from airees.gateway.adapter import AdapterRegistry, MessageHandler
from airees.gateway.conversation import ConversationManager
from airees.gateway.server import Gateway
from airees.gateway.types import InboundMessage, OutboundMessage


# -- Helpers -----------------------------------------------------------------


def _make_manager_stub() -> AsyncMock:
    """Return an AsyncMock that behaves like ConversationManager.handle."""
    manager = AsyncMock(spec=ConversationManager)
    manager.handle.return_value = OutboundMessage(
        channel="cli", recipient_id="user1", text="hello back"
    )
    return manager


@dataclass
class FakeAdapter:
    """Minimal adapter for testing."""

    name: str = "fake"
    _handler: MessageHandler | None = field(default=None, init=False, repr=False)

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send(self, message: OutboundMessage) -> None:
        pass


# -- Tests -------------------------------------------------------------------


def test_gateway_creates_with_defaults() -> None:
    """Gateway can be created with a ConversationManager and default registry."""
    manager = _make_manager_stub()
    gw = Gateway(conversation_manager=manager)
    assert gw.conversation_manager is manager
    assert isinstance(gw.adapters, AdapterRegistry)


@pytest.mark.asyncio
async def test_handle_message_routes_to_manager() -> None:
    """handle_message delegates to ConversationManager.handle."""
    manager = _make_manager_stub()
    gw = Gateway(conversation_manager=manager)

    msg = InboundMessage(channel="cli", sender_id="user1", text="hi")
    result = await gw.handle_message(msg)

    manager.handle.assert_awaited_once_with(msg)
    assert result.text == "hello back"


@pytest.mark.asyncio
async def test_handle_message_sends_via_adapter() -> None:
    """handle_message calls adapter.send when the channel adapter is registered."""
    manager = _make_manager_stub()
    adapter = FakeAdapter(name="cli")
    adapter.send = AsyncMock()

    registry = AdapterRegistry()
    registry.register(adapter)

    gw = Gateway(conversation_manager=manager, adapters=registry)
    msg = InboundMessage(channel="cli", sender_id="user1", text="hi")
    await gw.handle_message(msg)

    adapter.send.assert_awaited_once()
    sent_msg = adapter.send.call_args[0][0]
    assert sent_msg.text == "hello back"


@pytest.mark.asyncio
async def test_handle_message_unknown_adapter_does_not_crash() -> None:
    """handle_message still returns response when adapter is missing."""
    manager = _make_manager_stub()
    gw = Gateway(conversation_manager=manager)

    msg = InboundMessage(channel="unknown_channel", sender_id="u1", text="hi")
    result = await gw.handle_message(msg)

    assert result.text == "hello back"


@pytest.mark.asyncio
async def test_start_wires_handlers() -> None:
    """start() sets the message handler on all registered adapters."""
    manager = _make_manager_stub()
    adapter = FakeAdapter(name="test")
    adapter.start = AsyncMock()

    registry = AdapterRegistry()
    registry.register(adapter)

    gw = Gateway(conversation_manager=manager, adapters=registry)
    await gw.start()

    assert adapter._handler is not None
    adapter.start.assert_awaited_once()
