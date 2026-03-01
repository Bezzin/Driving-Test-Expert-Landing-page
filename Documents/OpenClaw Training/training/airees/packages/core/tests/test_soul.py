"""Tests for SOUL.md loader."""

import pytest
from pathlib import Path

from airees.soul import load_soul, Soul


@pytest.fixture
def soul_path(tmp_path):
    content = """---
format: soul/v1
name: Airees
version: 1
---

# Core Purpose
I am Airees — an autonomous orchestrator.

# Values
1. Autonomy
2. Quality over speed
"""
    path = tmp_path / "SOUL.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_soul(soul_path):
    soul = load_soul(soul_path)
    assert soul.name == "Airees"
    assert soul.version == 1
    assert "autonomous orchestrator" in soul.content


def test_load_soul_missing_file(tmp_path):
    soul = load_soul(tmp_path / "missing.md")
    assert soul.name == "Airees"
    assert soul.version == 0
    assert "autonomous orchestrator" in soul.content  # returns default


def test_soul_to_prompt(soul_path):
    soul = load_soul(soul_path)
    prompt = soul.to_prompt()
    assert isinstance(prompt, str)
    assert "Airees" in prompt
    assert len(prompt) > 50
