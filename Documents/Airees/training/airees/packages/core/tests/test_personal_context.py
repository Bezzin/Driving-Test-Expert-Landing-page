"""Tests for PersonalContext (USER.md) loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from airees.gateway.personal_context import PersonalContext, load_personal_context


# -- Frozen -------------------------------------------------------------------


def test_personal_context_frozen():
    ctx = PersonalContext(name="Alice", timezone="UTC", content="", raw="")
    with pytest.raises(AttributeError):
        ctx.name = "Bob"


# -- Parsing ------------------------------------------------------------------


def test_parses_frontmatter(tmp_path: Path):
    user_md = tmp_path / "USER.md"
    user_md.write_text(
        "---\nname: Alice\ntimezone: Europe/London\n---\n\nAlice likes cats.",
        encoding="utf-8",
    )

    ctx = load_personal_context(user_md)
    assert ctx.name == "Alice"
    assert ctx.timezone == "Europe/London"
    assert ctx.content == "Alice likes cats."


# -- Default when missing -----------------------------------------------------


def test_default_when_missing(tmp_path: Path):
    missing = tmp_path / "NONEXISTENT.md"
    ctx = load_personal_context(missing)

    assert ctx.name == "User"
    assert ctx.timezone == "UTC"
    assert ctx.content == ""
    assert ctx.raw == ""


# -- to_prompt ----------------------------------------------------------------


def test_to_prompt_format():
    ctx = PersonalContext(
        name="Alice",
        timezone="Europe/London",
        content="Alice likes cats.",
        raw="ignored",
    )
    prompt = ctx.to_prompt()
    assert "The user's name is Alice." in prompt
    assert "Their timezone is Europe/London." in prompt
    assert "Alice likes cats." in prompt


# -- No frontmatter -----------------------------------------------------------


def test_no_frontmatter_handling(tmp_path: Path):
    user_md = tmp_path / "USER.md"
    user_md.write_text("Just plain content, no YAML.", encoding="utf-8")

    ctx = load_personal_context(user_md)
    assert ctx.name == "User"
    assert ctx.timezone == "UTC"
    assert ctx.content == "Just plain content, no YAML."
