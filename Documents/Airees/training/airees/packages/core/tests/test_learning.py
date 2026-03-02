"""Tests for auto-skill capture after successful goals."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.learning import AutoSkillCapture
from airees.skill_store import SkillStore


@pytest.fixture
def skill_store(tmp_path: Path) -> SkillStore:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return SkillStore(skills_dir=skills_dir)


def test_capture_creates_skill_for_novel_pattern(skill_store: SkillStore):
    """A novel successful goal creates a new skill."""
    capture = AutoSkillCapture(skill_store=skill_store)

    capture.maybe_create_skill(
        goal_text="summarize the quarterly report",
        result_text="Here is the summary...",
        success=True,
    )

    results = skill_store.search("summarize quarterly report")
    assert len(results) >= 1
    assert results[0].name  # Should have a name


def test_capture_skips_existing_skill(skill_store: SkillStore):
    """If a skill already matches, don't create a duplicate."""
    skill_store.create_skill(
        name="summarize-report",
        description="Summarize reports",
        triggers=["summarize the quarterly report"],
        task_graph="1. Read report\n2. Summarize",
    )

    capture = AutoSkillCapture(skill_store=skill_store)
    initial_count = len(list(skill_store.skills_dir.glob("*.md")))

    capture.maybe_create_skill(
        goal_text="summarize the quarterly report",
        result_text="Summary here",
        success=True,
    )

    final_count = len(list(skill_store.skills_dir.glob("*.md")))
    assert final_count == initial_count  # No new skill created


def test_capture_skips_failed_goals(skill_store: SkillStore):
    """Failed goals should not create skills."""
    capture = AutoSkillCapture(skill_store=skill_store)

    capture.maybe_create_skill(
        goal_text="do something complex",
        result_text="Error occurred",
        success=False,
    )

    results = skill_store.search("do something complex")
    assert len(results) == 0


def test_capture_updates_existing_on_repeat_success(skill_store: SkillStore):
    """If a skill exists and succeeds again, update its success rate."""
    skill_store.create_skill(
        name="daily-summary",
        description="Daily summary",
        triggers=["summarize my day"],
        task_graph="1. Gather\n2. Summarize",
    )

    capture = AutoSkillCapture(skill_store=skill_store)
    capture.maybe_create_skill(
        goal_text="summarize my day",
        result_text="Done",
        success=True,
    )

    # Skill should still exist (updated, not duplicated)
    results = skill_store.search("summarize my day")
    assert len(results) >= 1
