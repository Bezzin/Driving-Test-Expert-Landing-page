from __future__ import annotations

from fastapi import APIRouter
from airees_engine.archetypes.loader import load_all_archetypes


def create_archetypes_router() -> APIRouter:
    router = APIRouter()

    @router.get("/archetypes")
    def list_archetypes():
        archetypes = load_all_archetypes()
        return list(archetypes.values())

    return router
