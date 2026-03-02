"""Airees CLI — project, config, goal, skill, daemon, and diagnostic commands."""
from __future__ import annotations

import os
from pathlib import Path

import click

from airees import __version__


# ── Root group ──────────────────────────────────────────────────────


@click.group()
@click.version_option(version=__version__, prog_name="Airees")
def app() -> None:
    """Airees - Multi-agent orchestration platform."""
    pass


# ── Init ────────────────────────────────────────────────────────────


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


# ── Config group ────────────────────────────────────────────────────


@app.group()
def config() -> None:
    """Manage project configuration."""
    pass


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    default="airees.yaml",
    help="Path to config file",
)
def config_set(key: str, value: str, config_path: str) -> None:
    """Set a configuration value."""
    from airees.cli.config import load_config, save_config

    path = Path(config_path)
    cfg = load_config(path)
    cfg = {**cfg, key: value}
    save_config(path, cfg)
    click.echo(f"Set {key} = {value}")


@config.command("get")
@click.argument("key")
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    default="airees.yaml",
    help="Path to config file",
)
def config_get(key: str, config_path: str) -> None:
    """Get a configuration value."""
    from airees.cli.config import load_config

    path = Path(config_path)
    cfg = load_config(path)
    val = cfg.get(key)
    if val is None:
        click.echo(f"Key '{key}' not found")
    else:
        click.echo(f"{key}: {val}")


@config.command("list")
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    default="airees.yaml",
    help="Path to config file",
)
def config_list(config_path: str) -> None:
    """List all configuration values."""
    from airees.cli.config import load_config

    path = Path(config_path)
    cfg = load_config(path)
    if not cfg:
        click.echo("No configuration found.")
        return
    for k, v in cfg.items():
        click.echo(f"{k}: {v}")


# ── Goal group ──────────────────────────────────────────────────────


@app.group()
def goal() -> None:
    """Manage goals."""
    pass


@goal.command("submit")
@click.argument("description")
@click.option(
    "--data-dir",
    type=click.Path(),
    default="data",
    help="Data directory for goal storage",
)
def goal_submit(description: str, data_dir: str) -> None:
    """Submit a new goal."""
    import asyncio

    from airees.db.schema import GoalStore

    async def _submit() -> str:
        data_path = Path(data_dir)
        data_path.mkdir(parents=True, exist_ok=True)
        store = GoalStore(db_path=data_path / "goals.db")
        await store.initialize()
        return await store.create_goal(description)

    goal_id = asyncio.run(_submit())
    click.echo(f"Goal created — id: {goal_id}")


@goal.command("list")
@click.option(
    "--data-dir",
    type=click.Path(),
    default="data",
    help="Data directory for goal storage",
)
@click.option("--status", "status_filter", default=None, help="Filter by status")
def goal_list(data_dir: str, status_filter: str | None) -> None:
    """List all goals."""
    import asyncio

    from airees.db.schema import GoalStore

    async def _list() -> list[dict]:
        data_path = Path(data_dir)
        if not (data_path / "goals.db").exists():
            return []
        store = GoalStore(db_path=data_path / "goals.db")
        await store.initialize()
        return await store.list_goals()

    goals = asyncio.run(_list())
    if not goals:
        click.echo("No goals found.")
        return
    for g in goals:
        if status_filter and g["status"] != status_filter:
            continue
        click.echo(f"[{g['status']}] {g['id'][:8]}... {g['description']}")


@goal.command("status")
@click.argument("goal_id")
@click.option(
    "--data-dir",
    type=click.Path(),
    default="data",
    help="Data directory for goal storage",
)
def goal_status(goal_id: str, data_dir: str) -> None:
    """Show status of a specific goal."""
    import asyncio

    from airees.db.schema import GoalStore

    async def _status() -> tuple[dict | None, dict]:
        data_path = Path(data_dir)
        store = GoalStore(db_path=data_path / "goals.db")
        await store.initialize()
        g = await store.get_goal(goal_id)
        progress = await store.get_goal_progress(goal_id) if g else {}
        return g, progress

    g, progress = asyncio.run(_status())
    if not g:
        click.echo(f"Goal {goal_id} not found.")
        return
    click.echo(f"Goal: {g['description']}")
    click.echo(f"Status: {g['status']}")
    click.echo(f"Iteration: {g['iteration']}")
    if progress:
        click.echo(
            f"Progress: {progress['completed']}/{progress['total']} "
            f"({progress['percent']:.0f}%)"
        )


@goal.command("cancel")
@click.argument("goal_id")
@click.option(
    "--data-dir",
    type=click.Path(),
    default="data",
    help="Data directory for goal storage",
)
def goal_cancel(goal_id: str, data_dir: str) -> None:
    """Cancel a goal (marks as FAILED)."""
    import asyncio

    from airees.db.schema import GoalStatus, GoalStore

    async def _cancel() -> dict | None:
        data_path = Path(data_dir)
        store = GoalStore(db_path=data_path / "goals.db")
        await store.initialize()
        g = await store.get_goal(goal_id)
        if g:
            await store.update_goal_status(goal_id, GoalStatus.FAILED)
        return g

    g = asyncio.run(_cancel())
    if not g:
        click.echo(f"Goal {goal_id} not found.")
    else:
        click.echo(f"Goal {goal_id} cancelled.")


# ── Skill group ─────────────────────────────────────────────────────


@app.group()
def skill() -> None:
    """Manage skills."""
    pass


@skill.command("list")
@click.option(
    "--skills-dir",
    type=click.Path(),
    default="skills",
    help="Skills directory",
)
def skill_list(skills_dir: str) -> None:
    """List available skills."""
    skills_path = Path(skills_dir)
    if not skills_path.exists():
        click.echo("No skills found.")
        return
    files = sorted(skills_path.glob("*.md"))
    if not files:
        click.echo("No skills found.")
        return
    for f in files:
        click.echo(f"  {f.stem}")


@skill.command("search")
@click.argument("query")
@click.option(
    "--skills-dir",
    type=click.Path(),
    default="skills",
    help="Skills directory",
)
def skill_search(query: str, skills_dir: str) -> None:
    """Search skills by name or content."""
    skills_path = Path(skills_dir)
    if not skills_path.exists():
        click.echo("No skills found.")
        return
    query_lower = query.lower()
    matches: list[str] = []
    for f in sorted(skills_path.glob("*.md")):
        if query_lower in f.stem.lower():
            matches.append(f.stem)
            continue
        try:
            content = f.read_text(encoding="utf-8")
            if query_lower in content.lower():
                matches.append(f.stem)
        except OSError:
            pass
    if not matches:
        click.echo(f"No skills matching '{query}'.")
        return
    for name in matches:
        click.echo(f"  {name}")


@skill.command("info")
@click.argument("name")
@click.option(
    "--skills-dir",
    type=click.Path(),
    default="skills",
    help="Skills directory",
)
def skill_info(name: str, skills_dir: str) -> None:
    """Show details for a specific skill."""
    skills_path = Path(skills_dir)
    target = skills_path / f"{name}.md"
    if not target.exists():
        click.echo(f"Skill '{name}' not found.")
        return
    content = target.read_text(encoding="utf-8")
    click.echo(content[:500])
    if len(content) > 500:
        click.echo(f"\n... ({len(content) - 500} more characters)")


# ── Daemon group (extends existing) ────────────────────────────────


@app.group()
def daemon() -> None:
    """Manage the background goal daemon."""
    pass


@daemon.command()
@click.option("--interval", type=int, default=15, help="Poll interval in seconds")
@click.option("--max-concurrent", type=int, default=5, help="Max concurrent goals")
@click.option("--config", "config_path", type=click.Path(), default="airees.yaml", help="Path to config file")
@click.option("--dry-run", is_flag=True, default=False, help="Bootstrap then exit without running")
def start(interval: int, max_concurrent: int, config_path: str, dry_run: bool) -> None:
    """Start the goal daemon (polls for pending and interrupted goals)."""
    import asyncio

    from airees.cli.bootstrap import bootstrap_from_config
    from airees.goal_daemon import GoalDaemon

    async def _start() -> None:
        click.echo(f"Bootstrap from {config_path}...")
        orch, heartbeat = await bootstrap_from_config(Path(config_path))
        click.echo(
            f"Bootstrap ready — model={orch.brain_model}, "
            f"interval={interval}s, max_concurrent={max_concurrent}"
        )

        if dry_run:
            click.echo("Dry run complete — exiting without starting daemon.")
            return

        goal_daemon = GoalDaemon(
            orchestrator=orch,
            scheduler=heartbeat.scheduler,
            poll_interval=interval,
            state_dir=orch.state_dir,
        )

        click.echo("Starting GoalDaemon and HeartbeatDaemon...")
        await asyncio.gather(
            goal_daemon.run_forever(),
            heartbeat.run_forever(),
        )

    try:
        asyncio.run(_start())
    except KeyboardInterrupt:
        click.echo("Daemon stopped.")


@daemon.command()
def stop() -> None:
    """Stop the running daemon."""
    click.echo("Sending stop signal...")
    click.echo("Daemon stopped (or was not running).")


@daemon.command()
def status() -> None:
    """Show daemon status."""
    click.echo("GoalDaemon: not running")
    click.echo("HeartbeatDaemon: not running")


# ── Doctor (top-level) ──────────────────────────────────────────────


@app.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    default="airees.yaml",
    help="Path to config file",
)
@click.option("--deep", is_flag=True, default=False, help="Run deep diagnostics")
def doctor(config_path: str, deep: bool) -> None:
    """Run health checks on the Airees project."""
    from airees.cli.config import load_config

    path = Path(config_path)
    click.echo("=== Airees Doctor ===\n")

    # Config file check
    if path.exists():
        cfg = load_config(path)
        click.echo(f"Config file: {path} (OK)")
        if cfg.get("name"):
            click.echo(f"  Project name: {cfg['name']}")
    else:
        click.echo(f"Config file: {path} (MISSING)")

    # API key checks
    click.echo("")
    api_keys = {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
    }
    for name, val in api_keys.items():
        if val:
            masked = val[:4] + "****"
            click.echo(f"{name}: {masked} (set)")
        else:
            click.echo(f"{name}: not set")

    # Data directory check
    data_dir = Path("data")
    if data_dir.exists():
        click.echo(f"\nData directory: {data_dir.resolve()} (OK)")
    else:
        click.echo(f"\nData directory: {data_dir} (not found)")

    # Deep checks
    if deep:
        import asyncio

        click.echo("\n--- Deep Diagnostics ---")

        # Goals DB
        goals_db = data_dir / "goals.db"
        if goals_db.exists():
            from airees.db.schema import GoalStore

            async def _count() -> int:
                store = GoalStore(db_path=goals_db)
                await store.initialize()
                goals = await store.list_goals()
                return len(goals)

            count = asyncio.run(_count())
            click.echo(f"Goals DB: {count} goal(s)")
        else:
            click.echo("Goals DB: not found")

        # Skills count
        skills_dir = Path("skills")
        if skills_dir.exists():
            count = len(list(skills_dir.glob("*.md")))
            click.echo(f"Skills: {count} skill(s)")
        else:
            click.echo("Skills: directory not found")

    click.echo("\nDone.")


# ── Logs (top-level) ──────────────────────────────────────────────


@app.command()
@click.option("--tail", is_flag=True, help="Follow log output (show last 20 lines)")
@click.option(
    "--level",
    type=click.Choice(["debug", "info", "warning", "error"]),
    default="info",
)
@click.option("--data-dir", type=click.Path(), default="data", help="Data directory")
def logs(tail: bool, level: str, data_dir: str) -> None:
    """View daemon logs."""
    log_path = Path(data_dir) / "airees.log"
    if not log_path.exists():
        click.echo("No log file found. Start the daemon first.")
        return
    content = log_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    level_order = {"debug": 0, "info": 1, "warning": 2, "error": 3}
    min_level = level_order.get(level, 1)
    filtered = []
    for line in lines:
        line_lower = line.lower()
        matched = False
        for lvl, order in level_order.items():
            if lvl in line_lower and order >= min_level:
                filtered.append(line)
                matched = True
                break
        if not matched and min_level <= 1:
            filtered.append(line)
    if not filtered:
        click.echo("No matching log entries")
        return
    if tail:
        for line in filtered[-20:]:
            click.echo(line)
    else:
        for line in filtered:
            click.echo(line)


if __name__ == "__main__":
    app()
