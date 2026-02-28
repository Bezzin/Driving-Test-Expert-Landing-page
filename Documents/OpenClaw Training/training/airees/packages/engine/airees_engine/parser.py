# airees/packages/engine/airees_engine/parser.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from airees_engine.schema import validate_agent_config, validate_workflow_config


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML mapping, got {type(data).__name__}")
        return data
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e


def parse_agent_file(path: Path) -> dict[str, Any]:
    config = _load_yaml(path)
    errors = validate_agent_config(config)
    if errors:
        raise ValueError(f"Invalid agent config in {path}: {'; '.join(errors)}")
    return config


def parse_workflow_file(path: Path) -> dict[str, Any]:
    config = _load_yaml(path)
    errors = validate_workflow_config(config)
    if errors:
        raise ValueError(f"Invalid workflow config in {path}: {'; '.join(errors)}")
    return config
