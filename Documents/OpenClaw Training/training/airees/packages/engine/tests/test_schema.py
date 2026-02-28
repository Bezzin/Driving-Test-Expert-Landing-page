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


def test_valid_workflow_with_quality_gate():
    config = {
        "name": "gated-pipeline",
        "pattern": "pipeline",
        "steps": [
            {"agent": "builder", "task": "Build the app"},
            {
                "agent": "reviewer",
                "task": "Score: {{previous_output}}",
                "quality_gate": {
                    "min_score": 8,
                    "max_retries": 3,
                    "on_failure": "flag_human",
                },
            },
        ],
    }
    errors = validate_workflow_config(config)
    assert errors == []


def test_valid_agent_with_feedback():
    config = {
        "name": "builder",
        "model": "claude-sonnet-4-6",
        "instructions": "Build apps",
        "feedback": {
            "evaluate_after": True,
            "success_criteria": "score >= 8",
        },
    }
    errors = validate_agent_config(config)
    assert errors == []


def test_valid_agent_with_context_budget():
    config = {
        "name": "orchestrator",
        "model": "claude-haiku-4-5",
        "instructions": "Route tasks efficiently",
        "context_budget": {
            "max_tokens": 200000,
            "max_usage_percent": 5.0,
        },
    }
    errors = validate_agent_config(config)
    assert errors == []
