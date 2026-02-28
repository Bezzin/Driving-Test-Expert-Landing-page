from __future__ import annotations

from fastapi import APIRouter


def create_runs_router() -> APIRouter:
    router = APIRouter()

    @router.get("/runs")
    def list_runs():
        return []

    return router
