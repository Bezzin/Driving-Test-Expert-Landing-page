"""Tests for ChannelAdapter protocol and AdapterRegistry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from airees.gateway.adapter import AdapterRegistry, ChannelAdapter, MessageHandler
from airees.gateway.types import InboundMessage, OutboundMessage


# -- Fake adapter for testing -------------------------------------------------


@dataclass
class FakeAdapter:
    """Minimal ChannelAdapter implementation for tests."""

    name: str = "fake"
    _started: bool = field(default=False, init=False)
    _stopped: bool = field(default=False, init=False)
    _sent: list[OutboundMessage] = field(default_factory=list, init=False)
    _handler: MessageHandler | None = field(default=None, init=False)

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._stopped = True

    async def send(self, message: OutboundMessage) -> None:
        self._sent.append(message)

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._handler = handler


# -- ChannelAdapter protocol --------------------------------------------------


def test_fake_adapter_satisfies_protocol():
    """FakeAdapter must be recognised as a ChannelAdapter at runtime."""
    adapter = FakeAdapter()
    assert isinstance(adapter, ChannelAdapter)


# -- AdapterRegistry ----------------------------------------------------------


def test_register_and_get():
    registry = AdapterRegistry()
    adapter = FakeAdapter(name="test")
    registry.register(adapter)
    assert registry.get("test") is adapter


def test_get_unknown_returns_none():
    registry = AdapterRegistry()
    assert registry.get("nonexistent") is None


def test_channels_property():
    registry = AdapterRegistry()
    registry.register(FakeAdapter(name="alpha"))
    registry.register(FakeAdapter(name="beta"))
    channels = registry.channels
    assert set(channels) == {"alpha", "beta"}


def test_duplicate_name_raises():
    registry = AdapterRegistry()
    registry.register(FakeAdapter(name="dup"))
    with pytest.raises(ValueError, match="dup"):
        registry.register(FakeAdapter(name="dup"))


@pytest.mark.asyncio
async def test_start_all_calls_start():
    registry = AdapterRegistry()
    a = FakeAdapter(name="a")
    b = FakeAdapter(name="b")
    registry.register(a)
    registry.register(b)
    await registry.start_all()
    assert a._started is True
    assert b._started is True


@pytest.mark.asyncio
async def test_stop_all_calls_stop():
    registry = AdapterRegistry()
    a = FakeAdapter(name="a")
    b = FakeAdapter(name="b")
    registry.register(a)
    registry.register(b)
    await registry.stop_all()
    assert a._stopped is True
    assert b._stopped is True


def test_channels_empty_by_default():
    registry = AdapterRegistry()
    assert registry.channels == []
