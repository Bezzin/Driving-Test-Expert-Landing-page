import pytest
from airees_engine.schema import validate_agent_config, validate_workflow_config


def test_valid_agent_config():
    config = {
        "name": "researcher",
        "description": "Finds info",
        "model": "claude-sonnet-4-6",
        "instructions": "You are a researcher.",
        "tools": ["web_search"],
    }
    errors = validate_agent_config(config)
    assert errors == []


def test_invalid_agent_config_missing_name():
    config = {
        "description": "Finds info",
        "model": "claude-sonnet-4-6",
        "instructions": "You are a researcher.",
    }
    errors = validate_agent_config(config)
    assert len(errors) > 0
    assert any("name" in e for e in errors)


def test_valid_workflow_config():
    config = {
        "name": "my-pipeline",
        "description": "A pipeline",
        "pattern": "pipeline",
        "steps": [
            {"agent": "researcher", "task": "Research {{topic}}"},
            {"agent": "writer", "task": "Write about {{previous_output}}"},
        ],
    }
    errors = validate_workflow_config(config)
    assert errors == []


def test_invalid_workflow_missing_pattern():
    config = {
        "name": "bad-workflow",
        "steps": [],
    }
    errors = validate_workflow_config(config)
    assert len(errors) > 0
