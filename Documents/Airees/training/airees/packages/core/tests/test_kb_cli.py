"""Tests for knowledge base CLI commands."""
from __future__ import annotations

from click.testing import CliRunner

from airees.cli.main import app


def test_kb_group_exists():
    """The 'kb' command group exists."""
    runner = CliRunner()
    result = runner.invoke(app, ["kb", "--help"])
    assert result.exit_code == 0
    assert "ingest" in result.output
    assert "search" in result.output
    assert "stats" in result.output
