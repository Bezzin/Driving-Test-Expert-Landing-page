"""Tests for the GoalDaemon background polling system."""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from airees.goal_daemon import GoalDaemon
from airees.scheduler import Scheduler, SchedulerConfig
from airees.state import ProjectState, save_state


@pytest.mark.asyncio
async def test_daemon_finds_pending_goals():
    """Daemon should find pending goals from the store and return their IDs."""
    mock_orch = MagicMock()
    mock_orch.store = AsyncMock()
    mock_orch.store.get_pending_goals = AsyncMock(return_value=[
        {"id": "g1", "description": "Test goal"},
    ])
    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        poll_interval=1,
        state_dir=Path("/nonexistent"),
    )
    pending = await daemon._find_pending_goals()
    assert len(pending) == 1
    assert pending[0] == "g1"


@pytest.mark.asyncio
async def test_daemon_finds_interrupted_goals(tmp_path):
    """Daemon should find interrupted goals from state files."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()

    state = ProjectState(
        project_id="g2",
        name="Interrupted goal",
        phases=["planning", "executing", "evaluating", "completing"],
    )
    state = state.advance()  # Move to "executing"
    save_state(state, state_dir / "g2.json")

    mock_orch = MagicMock()
    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        state_dir=state_dir,
    )
    interrupted = daemon._find_interrupted_goals()
    assert "g2" in interrupted


@pytest.mark.asyncio
async def test_daemon_skips_completed_goals(tmp_path):
    """Completed goals should not be resumed."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()

    state = ProjectState(
        project_id="g3",
        name="Done goal",
        phases=["planning", "executing", "evaluating", "completing"],
    )
    for _ in range(4):
        state = state.advance()
    save_state(state, state_dir / "g3.json")

    mock_orch = MagicMock()
    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        state_dir=state_dir,
    )
    interrupted = daemon._find_interrupted_goals()
    assert "g3" not in interrupted


@pytest.mark.asyncio
async def test_daemon_resets_stale_tasks_on_resume(tmp_path):
    """When resuming an interrupted goal, stale RUNNING tasks should be reset."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()

    state = ProjectState(
        project_id="g4",
        name="Crashed goal",
        phases=["planning", "executing", "evaluating", "completing"],
    )
    state = state.advance()
    save_state(state, state_dir / "g4.json")

    mock_orch = MagicMock()
    mock_orch.store = AsyncMock()
    mock_orch.store.get_pending_goals = AsyncMock(return_value=[])
    mock_orch.store.reset_stale_running_tasks = AsyncMock(return_value=2)
    mock_orch.execute_goal = AsyncMock()
    mock_orch.event_bus = MagicMock()
    mock_orch.event_bus.emit_async = AsyncMock()

    scheduler = Scheduler(config=SchedulerConfig(max_concurrent=5))

    daemon = GoalDaemon(
        orchestrator=mock_orch,
        scheduler=scheduler,
        poll_interval=1,
        state_dir=state_dir,
    )
    await daemon._poll_once()
    mock_orch.store.reset_stale_running_tasks.assert_called_once_with("g4")
