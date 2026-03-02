"""Tests for gateway bootstrap — bootstrap_gateway function and CLI chat wiring."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from airees.gateway.adapters.cli_adapter import CLIAdapter
from airees.gateway.conversation import ConversationManager
from airees.gateway.server import Gateway


# -- Helpers -----------------------------------------------------------------


def _mock_bootstrap_from_config() -> AsyncMock:
    """Return an AsyncMock that mimics bootstrap_from_config."""
    mock_orch = MagicMock()
    mock_orch.router = MagicMock()
    mock_orch.event_bus = MagicMock()
    mock_heartbeat = MagicMock()

    mock_fn = AsyncMock(return_value=(mock_orch, mock_heartbeat))
    return mock_fn


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_gateway_creates_gateway(tmp_path: Path) -> None:
    """bootstrap_gateway returns a Gateway with a ConversationManager."""
    config_file = tmp_path / "airees.yaml"
    config_file.write_text(
        "name: test\ndata_dir: " + str(tmp_path / "data").replace("\\", "/") + "\n",
        encoding="utf-8",
    )

    mock_fn = _mock_bootstrap_from_config()

    with patch("airees.cli.bootstrap.bootstrap_from_config", mock_fn):
        from airees.cli.bootstrap import bootstrap_gateway

        gw = await bootstrap_gateway(config_file)

    assert isinstance(gw, Gateway)
    assert isinstance(gw.conversation_manager, ConversationManager)


@pytest.mark.asyncio
async def test_bootstrap_gateway_registers_cli_adapter(tmp_path: Path) -> None:
    """bootstrap_gateway registers a CLIAdapter in the gateway."""
    config_file = tmp_path / "airees.yaml"
    config_file.write_text(
        "name: test\ndata_dir: " + str(tmp_path / "data").replace("\\", "/") + "\n",
        encoding="utf-8",
    )

    mock_fn = _mock_bootstrap_from_config()

    with patch("airees.cli.bootstrap.bootstrap_from_config", mock_fn):
        from airees.cli.bootstrap import bootstrap_gateway

        gw = await bootstrap_gateway(config_file)

    cli = gw.adapters.get("cli")
    assert cli is not None
    assert isinstance(cli, CLIAdapter)
