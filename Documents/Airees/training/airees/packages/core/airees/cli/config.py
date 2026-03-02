"""Configuration management for Airees CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: Path) -> dict[str, Any]:
    """Load YAML config file. Returns empty dict if file doesn't exist."""
    if not config_path.exists():
        return {}
    text = config_path.read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def save_config(config_path: Path, config: dict[str, Any]) -> None:
    """Write config dict back to YAML file."""
    config_path.write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
