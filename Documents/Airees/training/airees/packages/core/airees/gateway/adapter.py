"""ChannelAdapter protocol and AdapterRegistry for multi-channel routing.

Every external communication channel (CLI, Telegram, Slack, etc.) implements
:class:`ChannelAdapter`.  The :class:`AdapterRegistry` acts as a central hub
for registering, starting, and stopping adapters by channel name.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol, runtime_checkable

from airees.gateway.types import InboundMessage, OutboundMessage

MessageHandler = Callable[[InboundMessage], Awaitable[None]]
"""Async callback invoked when an adapter receives a new inbound message."""


@runtime_checkable
class ChannelAdapter(Protocol):
    """Protocol that every channel adapter must satisfy.

    Implementations must expose a ``name`` attribute and the four async
    lifecycle methods below.
    """

    @property
    def name(self) -> str: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def send(self, message: OutboundMessage) -> None: ...

    def set_message_handler(self, handler: MessageHandler) -> None: ...


@dataclass
class AdapterRegistry:
    """Registry for :class:`ChannelAdapter` instances.

    Provides lookup by channel name and bulk start/stop lifecycle helpers.

    Raises :class:`ValueError` when attempting to register two adapters
    with the same ``name``.
    """

    _adapters: dict[str, ChannelAdapter] = field(default_factory=dict)

    def register(self, adapter: ChannelAdapter) -> None:
        """Register *adapter*, keyed by its ``name``."""
        if adapter.name in self._adapters:
            raise ValueError(
                f"Adapter already registered for channel '{adapter.name}'"
            )
        self._adapters[adapter.name] = adapter

    def get(self, channel: str) -> ChannelAdapter | None:
        """Return the adapter for *channel*, or ``None`` if not found."""
        return self._adapters.get(channel)

    @property
    def channels(self) -> list[str]:
        """Sorted list of registered channel names."""
        return sorted(self._adapters)

    async def start_all(self) -> None:
        """Call ``start()`` on every registered adapter."""
        for adapter in self._adapters.values():
            await adapter.start()

    async def stop_all(self) -> None:
        """Call ``stop()`` on every registered adapter."""
        for adapter in self._adapters.values():
            await adapter.stop()
