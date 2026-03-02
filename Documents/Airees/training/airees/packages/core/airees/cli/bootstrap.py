"""Runtime bootstrap — create all Airees components from config."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus
from airees.heartbeat import HeartbeatDaemon
from airees.router.model_router import ModelRouter
from airees.scheduler import Scheduler, SchedulerConfig


_DEFAULTS: dict[str, Any] = {
    "brain_model": "anthropic/claude-opus-4-6",
    "data_dir": "data",
    "max_concurrent": 5,
    "poll_interval": 15,
}


def load_airees_config(config_path: Path) -> dict[str, Any]:
    """Load airees.yaml and merge with defaults."""
    config = dict(_DEFAULTS)
    if config_path.exists():
        import yaml

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        config.update(raw)
    return config


async def bootstrap_from_config(
    config_path: Path,
) -> tuple[BrainOrchestrator, HeartbeatDaemon]:
    """Create all runtime components from airees.yaml config.

    Returns:
        Tuple of (BrainOrchestrator, HeartbeatDaemon) ready to run.
    """
    config = load_airees_config(config_path)

    data_dir = Path(config["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)

    # GoalStore
    store = GoalStore(db_path=data_dir / "goals.db")
    await store.initialize()

    # Router
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    router = ModelRouter(anthropic_api_key=api_key)

    # EventBus
    event_bus = EventBus()

    # Scheduler
    scheduler = Scheduler(
        config=SchedulerConfig(max_concurrent=config.get("max_concurrent", 5))
    )

    # BrainOrchestrator
    orch = BrainOrchestrator(
        store=store,
        brain_model=config["brain_model"],
        router=router,
        event_bus=event_bus,
        soul_path=data_dir / "SOUL.md",
        state_dir=data_dir / "states",
        decisions_dir=data_dir / "decisions",
        memory_dir=data_dir / "memory",
        skills_dir=data_dir / "skills",
    )

    # HeartbeatDaemon
    heartbeat = HeartbeatDaemon(
        store=store,
        scheduler=scheduler,
        event_bus=event_bus,
    )

    return orch, heartbeat
