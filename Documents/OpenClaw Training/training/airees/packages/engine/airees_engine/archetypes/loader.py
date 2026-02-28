# airees/packages/engine/airees_engine/archetypes/loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ARCHETYPES_DIR = Path(__file__).parent


def load_archetype(name: str) -> dict[str, Any]:
    path = ARCHETYPES_DIR / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"Archetype not found: {name}")
    content = path.read_text(encoding="utf-8")
    return yaml.safe_load(content)


def load_all_archetypes() -> dict[str, dict[str, Any]]:
    archetypes = {}
    for path in ARCHETYPES_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        archetypes[data["name"]] = data
    return archetypes
