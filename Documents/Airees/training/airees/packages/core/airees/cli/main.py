from __future__ import annotations

from pathlib import Path

import click

from airees import __version__


@click.group()
@click.version_option(version=__version__, prog_name="Airees")
def app() -> None:
    """Airees - Multi-agent orchestration platform."""
    pass


@app.command()
@click.option("--path", type=click.Path(), default=".", help="Project directory")
def init(path: str) -> None:
    """Initialize a new Airees project."""
    project_path = Path(path)
    project_path.mkdir(parents=True, exist_ok=True)

    config = project_path / "airees.yaml"
    config.write_text(
        "# Airees project configuration\n"
        "name: my-project\n"
        "version: 0.1.0\n\n"
        "providers:\n"
        "  anthropic:\n"
        "    # Set ANTHROPIC_API_KEY env var\n"
        "  openrouter:\n"
        "    # Set OPENROUTER_API_KEY env var (optional)\n\n"
        "agents: {}\n"
        "workflows: {}\n",
        encoding="utf-8",
    )

    agents_dir = project_path / "agents"
    agents_dir.mkdir(exist_ok=True)

    workflows_dir = project_path / "workflows"
    workflows_dir.mkdir(exist_ok=True)

    click.echo(f"Initialized Airees project at {project_path.resolve()}")


@app.group()
def daemon() -> None:
    """Manage the background goal daemon."""
    pass


@daemon.command()
@click.option("--interval", type=int, default=30, help="Poll interval in seconds")
@click.option("--max-concurrent", type=int, default=5, help="Max concurrent goals")
@click.option("--data-dir", type=click.Path(), default="data", help="Data directory")
def start(interval: int, max_concurrent: int, data_dir: str) -> None:
    """Start the goal daemon (polls for pending and interrupted goals)."""
    click.echo(f"Starting GoalDaemon (interval={interval}s, max_concurrent={max_concurrent})")

    data_path = Path(data_dir)
    click.echo(f"Data dir: {data_path.resolve()}")
    click.echo(f"State dir: {(data_path / 'states').resolve()}")
    click.echo("GoalDaemon requires a configured BrainOrchestrator.")
    click.echo("Full runtime bootstrap will be added in a future release.")


if __name__ == "__main__":
    app()
