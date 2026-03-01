"""Dashboard metrics API routes."""
from __future__ import annotations

from fastapi import APIRouter, Request

from airees.state import load_state

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _state_files(request: Request):
    state_dir = request.app.state.data_dir / "states"
    if not state_dir.exists():
        return []
    return [f for f in sorted(state_dir.glob("*.json")) if not f.name.endswith("-decisions.json")]


@router.get("/metrics")
def get_metrics(request: Request):
    files = _state_files(request)
    states = [load_state(f) for f in files]

    active = sum(1 for s in states if not s.is_complete)
    needs_attention = 0
    for s in states:
        for phase in s.phases:
            if s.needs_human(phase):
                needs_attention += 1
                break
    completed = sum(1 for s in states if s.is_complete)

    return {
        "active_projects": active,
        "needs_attention": needs_attention,
        "queue_length": 0,
        "completed": completed,
    }
