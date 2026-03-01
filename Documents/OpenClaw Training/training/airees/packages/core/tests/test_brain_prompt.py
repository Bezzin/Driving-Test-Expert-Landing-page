"""Tests for Brain system prompt builder."""
import pytest
from airees.brain.prompt import build_brain_prompt
from airees.soul import Soul


def test_build_prompt_includes_soul():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app")
    assert "Airees" in prompt
    assert "COO" in prompt
    assert "Build a todo app" in prompt


def test_build_prompt_includes_coordinator_report():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    report = "3/5 tasks complete. Auth task failed twice."
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app", coordinator_report=report)
    assert "Auth task failed" in prompt


def test_build_prompt_includes_skill():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    skill = "# Todo App Pipeline\n1. Scaffold\n2. Database\n3. Auth"
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app", active_skill=skill)
    assert "Todo App Pipeline" in prompt


def test_build_prompt_includes_iteration():
    soul = Soul(name="Airees", version=1, content="I am the COO.", raw="")
    prompt = build_brain_prompt(soul=soul, goal="Build a todo app", iteration=3)
    assert "iteration 3" in prompt.lower() or "Iteration: 3" in prompt
