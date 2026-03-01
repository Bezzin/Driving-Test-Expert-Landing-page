from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from airees.agent import Agent
from airees.router.types import ModelConfig, ProviderType
from airees.runner import Runner, TokenUsage
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus


class RunCreate(BaseModel):
    agent_name: str
    task: str
    model: str = "openrouter/arcee-ai/trinity-large-preview:free"
    max_turns: int = 10


def create_runs_router() -> APIRouter:
    router = APIRouter()

    @router.get("/runs")
    def list_runs():
        return []

    @router.post("/runs", status_code=201)
    async def create_run(request: Request, run_config: RunCreate):
        run_id = str(uuid.uuid4())

        agent_configs = getattr(request.app.state, "agents", {})
        agent_data = agent_configs.get(run_config.agent_name)

        if agent_data:
            agent = Agent(
                name=agent_data["name"],
                instructions=agent_data.get("instructions", ""),
                model=ModelConfig(model_id=agent_data.get("model", run_config.model)),
                tools=agent_data.get("tools", []),
                max_turns=agent_data.get("max_turns", run_config.max_turns),
            )
        else:
            agent = Agent(
                name=run_config.agent_name,
                instructions=f"You are {run_config.agent_name}. Be helpful and concise.",
                model=ModelConfig(model_id=run_config.model),
                max_turns=run_config.max_turns,
            )

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

        # At least one provider must be configured
        if agent.model.provider == ProviderType.OPENROUTER and not openrouter_key:
            raise HTTPException(400, "OPENROUTER_API_KEY not set")
        if agent.model.provider == ProviderType.ANTHROPIC and not anthropic_key:
            raise HTTPException(400, "ANTHROPIC_API_KEY not set")

        router_instance = ModelRouter(
            anthropic_api_key=anthropic_key or "unused",
            openrouter_api_key=openrouter_key or None,
        )
        event_bus = EventBus()
        tool_registry = ToolRegistry()
        runner = Runner(
            router=router_instance,
            tool_registry=tool_registry,
            event_bus=event_bus,
        )

        try:
            result = await runner.run(
                agent=agent,
                task=run_config.task,
                run_id=run_id,
            )
            return {
                "run_id": run_id,
                "agent": result.agent_name,
                "output": result.output,
                "turns": result.turns,
                "tokens": {
                    "input": result.token_usage.input_tokens,
                    "output": result.token_usage.output_tokens,
                },
            }
        except Exception as e:
            raise HTTPException(500, f"Run failed: {e}")

    return router
