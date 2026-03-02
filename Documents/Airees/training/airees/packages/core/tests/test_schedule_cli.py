"""Tests for schedule CLI commands."""
from click.testing import CliRunner
from airees.cli.main import app


def test_schedule_group_exists():
    runner = CliRunner()
    result = runner.invoke(app, ["schedule", "--help"])
    assert result.exit_code == 0
    assert "add" in result.output
    assert "list" in result.output
    assert "remove" in result.output
