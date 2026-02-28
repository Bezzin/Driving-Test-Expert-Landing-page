from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    model: str
    instructions: str
    tools: list[str] = []
    description: str = ""
    max_turns: int = 10


def create_agents_router() -> APIRouter:
    router = APIRouter()

    @router.get("/agents")
    def list_agents(request: Request):
        return list(request.app.state.agents.values())

    @router.post("/agents", status_code=201)
    def create_agent(request: Request, agent: AgentCreate):
        if agent.name in request.app.state.agents:
            raise HTTPException(400, "Agent already exists")
        request.app.state.agents[agent.name] = agent.model_dump()
        return agent.model_dump()

    @router.get("/agents/{name}")
    def get_agent(request: Request, name: str):
        if name not in request.app.state.agents:
            raise HTTPException(404, "Agent not found")
        return request.app.state.agents[name]

    return router
