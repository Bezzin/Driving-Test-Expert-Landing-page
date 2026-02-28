"""JSON Schema definitions and validation for agent and workflow configs."""

from __future__ import annotations

import jsonschema

AGENT_SCHEMA = {
    "type": "object",
    "required": ["name", "instructions", "model"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "model": {"type": "string", "minLength": 1},
        "instructions": {"type": "string", "minLength": 1},
        "tools": {"type": "array", "items": {"type": "string"}},
        "max_turns": {"type": "integer", "minimum": 1, "maximum": 100},
        "memory": {
            "type": "object",
            "properties": {
                "personality": {"type": "string"},
                "context": {"type": "string"},
            },
        },
    },
}

WORKFLOW_SCHEMA = {
    "type": "object",
    "required": ["name", "pattern"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "pattern": {
            "type": "string",
            "enum": ["pipeline", "parallel", "shared_state", "triage"],
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["agent", "task"],
                "properties": {
                    "agent": {"type": "string"},
                    "task": {"type": "string"},
                },
            },
        },
        "agents": {"type": "object"},
        "variables": {"type": "object"},
    },
}


def validate_agent_config(config: dict) -> list[str]:
    """Validate an agent configuration dict against the AGENT_SCHEMA.

    Returns a list of error messages. An empty list means the config is valid.
    """
    validator = jsonschema.Draft7Validator(AGENT_SCHEMA)
    return [e.message for e in validator.iter_errors(config)]


def validate_workflow_config(config: dict) -> list[str]:
    """Validate a workflow configuration dict against the WORKFLOW_SCHEMA.

    Returns a list of error messages. An empty list means the config is valid.
    """
    validator = jsonschema.Draft7Validator(WORKFLOW_SCHEMA)
    return [e.message for e in validator.iter_errors(config)]
