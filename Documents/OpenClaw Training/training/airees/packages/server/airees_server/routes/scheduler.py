"""Scheduler status and config API routes."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

_config = {"interval_seconds": 300, "max_concurrent": 3}


class SchedulerConfigUpdate(BaseModel):
    interval_seconds: int | None = None
    max_concurrent: int | None = None


@router.get("/status")
def get_status():
    return {**_config, "running": False}


@router.put("/config")
def update_config(body: SchedulerConfigUpdate):
    if body.interval_seconds is not None:
        _config["interval_seconds"] = body.interval_seconds
    if body.max_concurrent is not None:
        _config["max_concurrent"] = body.max_concurrent
    return _config
