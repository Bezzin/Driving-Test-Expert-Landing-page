"""Tests for brain reflection and soul updates."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from airees.brain.reflection import (
    compute_genesis_hash,
    update_soul_file,
    write_daily_log,
)
from airees.soul import load_soul


@pytest.fixture
def soul_path(tmp_path: Path) -> Path:
    path = tmp_path / "SOUL.md"
    path.write_text(
        "---\n"
        "format: soul/v1\n"
        "name: Airees\n"
        "version: 1\n"
        "---\n\n"
        "# Core Purpose\n\n"
        "I am Airees — an autonomous orchestrator.\n\n"
        "# Values\n\n1. Autonomy\n2. Quality\n\n"
        "# Capabilities\n\n"
        "- Skills mastered: 0\n"
        "- Goals completed: 0\n\n"
        "# Strategy\n\n"
        "- Current focus: Learning\n",
        encoding="utf-8",
    )
    return path


def test_compute_genesis_hash(soul_path: Path):
    h = compute_genesis_hash(soul_path)
    assert isinstance(h, str)
    assert len(h) == 64


def test_update_soul_bumps_version(soul_path: Path):
    update_soul_file(
        soul_path,
        capabilities_update={"goals_completed": 5},
    )
    soul = load_soul(soul_path)
    assert soul.version == 2


def test_update_soul_capabilities(soul_path: Path):
    update_soul_file(
        soul_path,
        capabilities_update={"skills_mastered": 3, "goals_completed": 7},
    )
    content = soul_path.read_text(encoding="utf-8")
    assert "Skills mastered: 3" in content
    assert "Goals completed: 7" in content


def test_update_soul_strategy(soul_path: Path):
    update_soul_file(
        soul_path,
        strategy_update="Focus on SaaS applications",
    )
    content = soul_path.read_text(encoding="utf-8")
    assert "Focus on SaaS applications" in content


def test_update_soul_appends_lesson(soul_path: Path):
    update_soul_file(
        soul_path,
        lesson="Clerk is better than NextAuth for SaaS",
    )
    content = soul_path.read_text(encoding="utf-8")
    assert "Clerk is better than NextAuth" in content


def test_write_daily_log(tmp_path: Path):
    memory_dir = tmp_path / "memory"
    write_daily_log(
        memory_dir=memory_dir,
        goal_id="goal-123",
        iterations=2,
        skills_created=["api-builder"],
        total_cost=1.50,
        key_decisions=["Used FastAPI over Flask"],
        lesson="FastAPI is faster for async APIs",
    )
    logs = list(memory_dir.glob("*.md"))
    assert len(logs) == 1
    content = logs[0].read_text(encoding="utf-8")
    assert "goal-123" in content
    assert "Iterations:** 2" in content
    assert "api-builder" in content
    assert "1.50" in content or "1.5" in content


def test_write_daily_log_appends(tmp_path: Path):
    memory_dir = tmp_path / "memory"
    write_daily_log(memory_dir=memory_dir, goal_id="goal-1")
    write_daily_log(memory_dir=memory_dir, goal_id="goal-2")
    logs = list(memory_dir.glob("*.md"))
    assert len(logs) == 1
    content = logs[0].read_text(encoding="utf-8")
    assert "goal-1" in content
    assert "goal-2" in content
