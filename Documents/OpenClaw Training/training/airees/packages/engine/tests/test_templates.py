"""Tests for workflow template system."""
import pytest
from airees_engine.templates.loader import load_template, load_all_templates, apply_template


def test_load_all_templates():
    templates = load_all_templates()
    assert len(templates) >= 1
    assert "base-pipeline" in templates


def test_load_single_template():
    tpl = load_template("base-pipeline")
    assert tpl["name"] == "base-pipeline"
    assert "steps" in tpl


def test_load_missing_template():
    with pytest.raises(ValueError, match="not found"):
        load_template("does-not-exist")


def test_apply_template_merges_overrides():
    base = {"name": "base", "pattern": "pipeline", "steps": [{"agent": "a", "task": "b"}]}
    overrides = {"name": "my-pipeline", "variables": {"topic": "fitness"}}
    result = apply_template(base, overrides)
    assert result["name"] == "my-pipeline"
    assert result["pattern"] == "pipeline"
    assert "variables" in result
