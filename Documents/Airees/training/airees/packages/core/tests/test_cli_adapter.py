"""Tests for CLIAdapter channel implementation."""
from __future__ import annotations

import pytest

from airees.gateway.adapter import ChannelAdapter
from airees.gateway.adapters.cli_adapter import CLIAdapter
from airees.gateway.types import InboundMessage, OutboundMessage


# -- Basic properties ---------------------------------------------------------


def test_cli_adapter_name():
    adapter = CLIAdapter()
    assert adapter.name == "cli"


def test_cli_adapter_satisfies_protocol():
    adapter = CLIAdapter()
    assert isinstance(adapter, ChannelAdapter)


# -- set_message_handler ------------------------------------------------------


def test_set_message_handler():
    adapter = CLIAdapter()

    async def handler(msg: InboundMessage) -> None:
        pass

    adapter.set_message_handler(handler)
    assert adapter._handler is handler


# -- _process_line ------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_line_creates_inbound_message():
    adapter = CLIAdapter()
    received: list[InboundMessage] = []

    async def handler(msg: InboundMessage) -> None:
        received.append(msg)

    adapter.set_message_handler(handler)
    await adapter._process_line("hello world")

    assert len(received) == 1
    msg = received[0]
    assert msg.channel == "cli"
    assert msg.sender_id == "local"
    assert msg.text == "hello world"


@pytest.mark.asyncio
async def test_process_line_empty_ignored():
    adapter = CLIAdapter()
    received: list[InboundMessage] = []

    async def handler(msg: InboundMessage) -> None:
        received.append(msg)

    adapter.set_message_handler(handler)
    await adapter._process_line("")
    await adapter._process_line("   ")

    assert len(received) == 0


@pytest.mark.asyncio
async def test_process_line_no_handler_no_crash():
    adapter = CLIAdapter()
    # Should not raise even without a handler set
    await adapter._process_line("test input")


# -- send ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_prints_to_stdout(capsys):
    adapter = CLIAdapter()
    msg = OutboundMessage(channel="cli", recipient_id="local", text="hello back")
    await adapter.send(msg)
    captured = capsys.readouterr()
    assert "airees>" in captured.out
    assert "hello back" in captured.out


# -- start / stop -------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_sets_running():
    adapter = CLIAdapter()
    await adapter.start()
    assert adapter._running is True


@pytest.mark.asyncio
async def test_stop_clears_running():
    adapter = CLIAdapter()
    await adapter.start()
    await adapter.stop()
    assert adapter._running is False
