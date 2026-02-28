"""Tests for project state machine."""
import json
from pathlib import Path
import pytest
from airees.state import PhaseStatus, ProjectState, load_state, save_state


def test_project_state_creation():
    state = ProjectState(project_id="proj-001", name="Test Project", phases=["research", "build", "review"])
    assert state.project_id == "proj-001"
    assert state.name == "Test Project"
    assert state.current_phase == "research"
    assert state.phase_statuses == {"research": PhaseStatus.PENDING, "build": PhaseStatus.PENDING, "review": PhaseStatus.PENDING}
    assert state.retry_counts == {}
    assert state.metadata == {}


def test_advance_phase():
    state = ProjectState(project_id="proj-001", name="Test", phases=["research", "build", "review"])
    next_state = state.advance()
    assert next_state.current_phase == "build"
    assert next_state.phase_statuses["research"] == PhaseStatus.COMPLETED


def test_advance_past_last_phase():
    state = ProjectState(project_id="proj-001", name="Test", phases=["research"])
    next_state = state.advance()
    assert next_state.current_phase is None
    assert next_state.phase_statuses["research"] == PhaseStatus.COMPLETED


def test_fail_phase():
    state = ProjectState(project_id="proj-001", name="Test", phases=["research", "build"])
    failed = state.fail_phase("API error")
    assert failed.phase_statuses["research"] == PhaseStatus.FAILED
    assert failed.retry_counts["research"] == 1
    assert failed.metadata["last_error"] == "API error"


def test_fail_phase_increments_retry():
    state = ProjectState(project_id="proj-001", name="Test", phases=["research"], retry_counts={"research": 2})
    failed = state.fail_phase("Again")
    assert failed.retry_counts["research"] == 3


def test_needs_human_after_max_retries():
    state = ProjectState(project_id="proj-001", name="Test", phases=["research"], retry_counts={"research": 3})
    assert state.needs_human("research") is True


def test_does_not_need_human_under_max():
    state = ProjectState(project_id="proj-001", name="Test", phases=["research"], retry_counts={"research": 1})
    assert state.needs_human("research") is False


def test_is_complete():
    state = ProjectState(project_id="proj-001", name="Test", phases=["a"], current_phase=None, phase_statuses={"a": PhaseStatus.COMPLETED})
    assert state.is_complete is True


def test_is_not_complete():
    state = ProjectState(project_id="proj-001", name="Test", phases=["a", "b"])
    assert state.is_complete is False


def test_save_and_load(tmp_path):
    state = ProjectState(project_id="proj-001", name="Test", phases=["research", "build"])
    state_file = tmp_path / "proj-001.json"
    save_state(state, state_file)
    assert state_file.exists()
    loaded = load_state(state_file)
    assert loaded.project_id == state.project_id
    assert loaded.name == state.name
    assert loaded.phases == state.phases
    assert loaded.current_phase == state.current_phase
    assert loaded.phase_statuses == state.phase_statuses


def test_save_preserves_progress(tmp_path):
    state = ProjectState(project_id="proj-001", name="Test", phases=["research", "build"])
    advanced = state.advance()
    state_file = tmp_path / "proj-001.json"
    save_state(advanced, state_file)
    loaded = load_state(state_file)
    assert loaded.current_phase == "build"
    assert loaded.phase_statuses["research"] == PhaseStatus.COMPLETED


def test_load_nonexistent_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_state(tmp_path / "nope.json")
