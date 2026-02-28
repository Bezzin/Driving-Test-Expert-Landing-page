# tests/test_resolver.py
import pytest
from airees_engine.resolver import resolve_agent_config, resolve_variables


def test_resolve_variables():
    template = "Research {{topic}} and summarize findings about {{topic}}"
    result = resolve_variables(template, {"topic": "AI safety"})
    assert result == "Research AI safety and summarize findings about AI safety"


def test_resolve_variables_missing():
    template = "Research {{topic}}"
    result = resolve_variables(template, {})
    assert result == "Research {{topic}}"


def test_resolve_agent_with_archetype():
    archetypes = {
        "researcher": {
            "name": "researcher",
            "model": "claude-sonnet-4-6",
            "instructions": "You are a researcher.",
            "tools": ["web_search", "web_fetch"],
            "max_turns": 15,
        },
    }
    override = {
        "archetype": "researcher",
        "model": "openrouter/deepseek/deepseek-r1",
        "tools": ["web_search", "web_fetch", "arxiv_search"],
    }
    resolved = resolve_agent_config(override, archetypes)
    assert resolved["model"] == "openrouter/deepseek/deepseek-r1"
    assert "arxiv_search" in resolved["tools"]
    assert resolved["instructions"] == "You are a researcher."
    assert resolved["max_turns"] == 15
