"""Tests for CLI commands."""
import pytest
from click.testing import CliRunner

from airees.cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


# ── Task 11: Config commands ────────────────────────────────────────


def test_config_set_and_get(runner, tmp_path):
    """config set then config get should return the value."""
    config_file = tmp_path / "airees.yaml"
    config_file.write_text("name: test\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["config", "set", "brain_model", "claude-opus-4-6", "--config", str(config_file)],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        ["config", "get", "brain_model", "--config", str(config_file)],
    )
    assert result.exit_code == 0
    assert "claude-opus-4-6" in result.output


def test_config_list(runner, tmp_path):
    """config list should show all config values."""
    config_file = tmp_path / "airees.yaml"
    config_file.write_text("name: test\nversion: 0.1.0\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["config", "list", "--config", str(config_file)],
    )
    assert result.exit_code == 0
    assert "name" in result.output
    assert "test" in result.output


# ── Task 12: Goal commands ──────────────────────────────────────────


def test_goal_submit(runner, tmp_path):
    """goal submit should create a goal and print its ID."""
    result = runner.invoke(
        app,
        ["goal", "submit", "Build a chatbot", "--data-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Goal created" in result.output


def test_goal_list(runner, tmp_path):
    """goal list should show submitted goals."""
    runner.invoke(
        app,
        ["goal", "submit", "Test goal", "--data-dir", str(tmp_path)],
    )
    result = runner.invoke(
        app,
        ["goal", "list", "--data-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Test goal" in result.output


def test_goal_status(runner, tmp_path):
    """goal status should show details for a specific goal."""
    submit_result = runner.invoke(
        app,
        ["goal", "submit", "Status test", "--data-dir", str(tmp_path)],
    )
    # Extract goal ID from output
    goal_id = None
    for line in submit_result.output.strip().split("\n"):
        if "id:" in line.lower():
            goal_id = line.split(":")[-1].strip()
    assert goal_id is not None

    result = runner.invoke(
        app,
        ["goal", "status", goal_id, "--data-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Status test" in result.output


# ── Task 13: Skill, doctor, daemon stop/status ──────────────────────


def test_skill_list(runner):
    """skill list should not error even with no skills."""
    result = runner.invoke(app, ["skill", "list", "--skills-dir", "/nonexistent"])
    assert result.exit_code == 0


def test_doctor_runs(runner, tmp_path):
    """doctor should run basic health checks."""
    config_file = tmp_path / "airees.yaml"
    config_file.write_text("name: test\n", encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "config" in result.output.lower()


def test_daemon_stop(runner):
    """daemon stop should output a message (no daemon running is OK)."""
    result = runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 0


def test_daemon_status(runner):
    """daemon status should report not running."""
    result = runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0
