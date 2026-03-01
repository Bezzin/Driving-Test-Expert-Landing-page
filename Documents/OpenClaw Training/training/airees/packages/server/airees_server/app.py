from __future__ import annotations

import asyncio
from pathlib import Path

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from airees.db.schema import GoalStore
from airees_server.routes.agents import create_agents_router
from airees_server.routes.archetypes import create_archetypes_router
from airees_server.routes.chat import create_chat_router
from airees_server.routes.goals import router as goals_router
from airees_server.routes.runs import create_runs_router
from airees_server.routes.dashboard import router as dashboard_router
from airees_server.routes.scheduler import router as scheduler_router
from airees_server.routes.state import router as state_router
from airees_server.routes.templates import router as templates_router


def create_app(data_dir: Path | None = None) -> FastAPI:
    load_dotenv()
    data_dir = data_dir or Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Airees", version="0.1.0")

    cors_origins = os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3004"
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.data_dir = data_dir
    app.state.agents = {}

    goal_store = GoalStore(db_path=data_dir / "airees.db")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(goal_store.initialize())
    loop.close()
    app.state.goal_store = goal_store

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(create_agents_router(), prefix="/api")
    app.include_router(create_archetypes_router(), prefix="/api")
    app.include_router(create_chat_router(), prefix="/api")
    app.include_router(goals_router, prefix="/api")
    app.include_router(create_runs_router(), prefix="/api")
    app.include_router(state_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(scheduler_router, prefix="/api")
    app.include_router(templates_router, prefix="/api")

    return app
