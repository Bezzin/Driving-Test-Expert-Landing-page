# airees/packages/engine/airees_engine/resolver.py
from __future__ import annotations

import re
from typing import Any


def resolve_variables(template: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))
    return re.sub(r"\{\{(\w+)\}\}", replace, template)


def resolve_agent_config(
    config: dict[str, Any],
    archetypes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    archetype_name = config.get("archetype")
    if archetype_name is None:
        return dict(config)

    if archetype_name not in archetypes:
        raise ValueError(f"Unknown archetype: {archetype_name}")

    base = dict(archetypes[archetype_name])
    overrides = {k: v for k, v in config.items() if k != "archetype"}
    return {**base, **overrides}
