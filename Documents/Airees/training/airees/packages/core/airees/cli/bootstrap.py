"""Runtime bootstrap — create all Airees components from config."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from airees.brain.orchestrator import BrainOrchestrator
from airees.db.schema import GoalStore
from airees.events import EventBus
from airees.gateway.adapters.cli_adapter import CLIAdapter
from airees.gateway.conversation import ConversationManager
from airees.gateway.cost_tracker import CostTracker
from airees.gateway.model_preference import ModelPreference
from airees.gateway.server import Gateway
from airees.heartbeat import HeartbeatDaemon
from airees.router.model_router import ModelRouter
from airees.scheduler import Scheduler, SchedulerConfig
from airees.skill_store import SkillStore


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


async def bootstrap_gateway(config_path: Path) -> Gateway:
    """Create a fully-wired Gateway from airees.yaml config.

    1. Bootstrap the core runtime (orchestrator, heartbeat).
    2. Load config to resolve data_dir.
    3. Create a ConversationManager wired to the orchestrator's router.
    4. Create a Gateway and register the CLI adapter.

    Returns:
        A :class:`Gateway` ready to ``start()``.
    """
    orch, _heartbeat = await bootstrap_from_config(config_path)
    config = load_airees_config(config_path)
    data_dir = Path(config["data_dir"])

    skill_store = SkillStore(skills_dir=data_dir / "skills")
    cost_tracker = CostTracker()
    model_preference = ModelPreference()

    manager = ConversationManager(
        router=orch.router,
        event_bus=orch.event_bus,
        soul_path=data_dir / "SOUL.md",
        user_path=data_dir / "USER.md",
        orchestrator=orch,
        skill_store=skill_store,
        cost_tracker=cost_tracker,
        model_preference=model_preference,
    )

    gateway = Gateway(conversation_manager=manager)
    gateway.adapters.register(CLIAdapter())
    return gateway
