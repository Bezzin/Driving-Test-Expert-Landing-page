"""Tests for runtime bootstrap from config."""
import pytest
from pathlib import Path

from airees.cli.bootstrap import load_airees_config, bootstrap_from_config


def test_load_config_returns_defaults(tmp_path):
    """load_airees_config should return defaults when file doesn't exist."""
    config = load_airees_config(tmp_path / "missing.yaml")
    assert config["brain_model"] == "anthropic/claude-opus-4-6"
    assert config["data_dir"] == "data"


def test_load_config_reads_yaml(tmp_path):
    """load_airees_config should parse YAML and merge with defaults."""
    config_file = tmp_path / "airees.yaml"
    config_file.write_text("brain_model: custom/model\ndata_dir: custom\n", encoding="utf-8")

    config = load_airees_config(config_file)
    assert config["brain_model"] == "custom/model"
    assert config["data_dir"] == "custom"


@pytest.mark.asyncio
async def test_bootstrap_creates_store_and_orchestrator(tmp_path):
    """bootstrap_from_config should return a working orchestrator and heartbeat."""
    config_file = tmp_path / "airees.yaml"
    config_file.write_text(
        f"brain_model: anthropic/claude-opus-4-6\ndata_dir: {tmp_path / 'data'}\n",
        encoding="utf-8",
    )

    orch, heartbeat = await bootstrap_from_config(config_file)

    assert orch is not None
    assert orch.brain_model == "anthropic/claude-opus-4-6"
    assert heartbeat is not None
