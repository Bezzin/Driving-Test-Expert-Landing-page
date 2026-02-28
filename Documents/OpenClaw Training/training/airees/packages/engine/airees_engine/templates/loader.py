"""Load and apply workflow templates."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

TEMPLATES_DIR = Path(__file__).parent


def load_template(name: str) -> dict[str, Any]:
    path = TEMPLATES_DIR / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"Template not found: {name}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_templates() -> dict[str, dict[str, Any]]:
    templates = {}
    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        templates[data.get("name", path.stem)] = data
    return templates


def apply_template(template: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    return {**template, **overrides}
