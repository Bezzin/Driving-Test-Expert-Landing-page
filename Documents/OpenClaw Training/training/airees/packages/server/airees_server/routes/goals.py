"""Goal submission and tracking API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airees.db.schema import GoalStore


router = APIRouter(prefix="/goals", tags=["goals"])


class GoalCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=32_000)


def _get_store(request: Request) -> GoalStore:
    return request.app.state.goal_store


@router.post("", status_code=201)
async def submit_goal(body: GoalCreate, request: Request):
    store = _get_store(request)
    goal_id = await store.create_goal(description=body.description)
    return {"goal_id": goal_id, "status": "pending"}


@router.get("")
async def list_goals(request: Request):
    store = _get_store(request)
    import aiosqlite
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM goals ORDER BY created_at DESC LIMIT 50"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/{goal_id}")
async def get_goal(goal_id: str, request: Request):
    store = _get_store(request)
    goal = await store.get_goal(goal_id)
    if not goal:
        raise HTTPException(404, f"Goal not found: {goal_id}")
    return goal


@router.get("/{goal_id}/progress")
async def get_progress(goal_id: str, request: Request):
    store = _get_store(request)
    goal = await store.get_goal(goal_id)
    if not goal:
        raise HTTPException(404, f"Goal not found: {goal_id}")
    return await store.get_goal_progress(goal_id)


@router.get("/{goal_id}/tasks")
async def get_tasks(goal_id: str, request: Request):
    store = _get_store(request)
    return await store.get_all_tasks(goal_id)
