"""CLI channel adapter — interactive terminal interface for Airees.

Reads user input from stdin and prints agent responses to stdout.
The blocking ``input()`` call is offloaded to a thread via
``asyncio.to_thread`` so the async event loop stays responsive.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from airees.gateway.adapter import MessageHandler
from airees.gateway.types import InboundMessage, OutboundMessage


@dataclass
class CLIAdapter:
    """Terminal-based channel adapter.

    Attributes:
        name: Channel identifier, always ``"cli"``.
        prompt: The string shown before user input.
    """

    name: str = field(default="cli", init=False)
    prompt: str = "you> "
    _running: bool = field(default=False, init=False, repr=False)
    _handler: MessageHandler | None = field(default=None, init=False, repr=False)

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Register the callback invoked for each inbound message."""
        self._handler = handler

    async def start(self) -> None:
        """Mark the adapter as running."""
        self._running = True

    async def stop(self) -> None:
        """Mark the adapter as stopped."""
        self._running = False

    async def send(self, message: OutboundMessage) -> None:
        """Print *message* to stdout with the ``airees>`` prefix."""
        print(f"airees> {message.text}")

    async def _process_line(self, line: str) -> None:
        """Turn a raw input line into an :class:`InboundMessage`.

        Empty or whitespace-only lines are silently ignored.  If no handler
        has been set, the line is discarded without error.
        """
        stripped = line.strip()
        if not stripped:
            return
        if self._handler is None:
            return
        msg = InboundMessage(channel="cli", sender_id="local", text=stripped)
        await self._handler(msg)

    async def run_interactive(self) -> None:
        """Blocking interactive loop reading stdin until exit/quit.

        Uses ``asyncio.to_thread(input, ...)`` so the event loop is never
        blocked by waiting for user input.
        """
        self._running = True
        try:
            while self._running:
                try:
                    line = await asyncio.to_thread(input, self.prompt)
                except EOFError:
                    break
                if line.strip().lower() in ("exit", "quit", "/quit"):
                    break
                await self._process_line(line)
        finally:
            self._running = False
