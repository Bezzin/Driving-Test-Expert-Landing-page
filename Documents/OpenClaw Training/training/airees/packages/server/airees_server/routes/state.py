"""Project state management API routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from airees.state import PhaseStatus, ProjectState, load_state, save_state

router = APIRouter(prefix="/state", tags=["state"])


class StateCreate(BaseModel):
    project_id: str
    name: str
    phases: list[str]
    max_retries: int = 3


class FailRequest(BaseModel):
    error: str


def _state_dir(request: Request) -> Path:
    return request.app.state.data_dir / "states"


def _state_path(request: Request, project_id: str) -> Path:
    return _state_dir(request) / f"{project_id}.json"


def _serialize(state: ProjectState) -> dict:
    return {
        "project_id": state.project_id,
        "name": state.name,
        "phases": state.phases,
        "current_phase": state.current_phase,
        "phase_statuses": {k: v.value for k, v in state.phase_statuses.items()},
        "retry_counts": state.retry_counts,
        "metadata": state.metadata,
        "max_retries": state.max_retries,
        "is_complete": state.is_complete,
    }


@router.post("", status_code=201)
def create_state(body: StateCreate, request: Request):
    path = _state_path(request, body.project_id)
    if path.exists():
        raise HTTPException(400, f"State already exists: {body.project_id}")
    state = ProjectState(
        project_id=body.project_id,
        name=body.name,
        phases=body.phases,
        max_retries=body.max_retries,
    )
    save_state(state, path)
    return _serialize(state)


@router.get("")
def list_states(request: Request):
    state_dir = _state_dir(request)
    if not state_dir.exists():
        return []
    return [_serialize(load_state(f)) for f in sorted(state_dir.glob("*.json"))]


@router.get("/needs-attention")
def list_needs_attention(request: Request):
    state_dir = _state_dir(request)
    if not state_dir.exists():
        return []
    results = []
    for f in sorted(state_dir.glob("*.json")):
        s = load_state(f)
        for phase in s.phases:
            if s.needs_human(phase):
                results.append(_serialize(s))
                break
    return results


@router.get("/{project_id}")
def get_state(project_id: str, request: Request):
    path = _state_path(request, project_id)
    if not path.exists():
        raise HTTPException(404, f"State not found: {project_id}")
    return _serialize(load_state(path))


@router.post("/{project_id}/advance")
def advance_state(project_id: str, request: Request):
    path = _state_path(request, project_id)
    if not path.exists():
        raise HTTPException(404, f"State not found: {project_id}")
    state = load_state(path)
    advanced = state.advance()
    save_state(advanced, path)
    return _serialize(advanced)


@router.post("/{project_id}/fail")
def fail_state(project_id: str, body: FailRequest, request: Request):
    path = _state_path(request, project_id)
    if not path.exists():
        raise HTTPException(404, f"State not found: {project_id}")
    state = load_state(path)
    failed = state.fail_phase(body.error)
    save_state(failed, path)
    return _serialize(failed)
