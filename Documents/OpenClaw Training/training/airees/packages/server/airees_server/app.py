from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from airees_server.routes.agents import create_agents_router
from airees_server.routes.archetypes import create_archetypes_router
from airees_server.routes.runs import create_runs_router
from airees_server.routes.state import router as state_router


def create_app(data_dir: Path | None = None) -> FastAPI:
    data_dir = data_dir or Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Airees", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.data_dir = data_dir
    app.state.agents = {}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(create_agents_router(), prefix="/api")
    app.include_router(create_archetypes_router(), prefix="/api")
    app.include_router(create_runs_router(), prefix="/api")
    app.include_router(state_router, prefix="/api")

    return app
