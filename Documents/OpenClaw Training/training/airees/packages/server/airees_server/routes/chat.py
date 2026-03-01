from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from airees.agent import Agent
from airees.events import Event, EventBus, EventType
from airees.orchestration.triage import Route, TriageRouter
from airees.router.model_router import ModelRouter
from airees.router.types import ModelConfig, ProviderType
from airees.runner import Runner
from airees.tools.registry import ToolRegistry
from airees_engine.archetypes.loader import load_all_archetypes

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=32_000)
    model: str = Field(
        default="openrouter/arcee-ai/trinity-large-preview:free",
        pattern=r"^[a-zA-Z0-9/_:.\-]+$",
    )


@functools.lru_cache(maxsize=1)
def _cached_archetypes() -> dict:
    return load_all_archetypes()


def create_chat_router() -> APIRouter:
    router = APIRouter()

    @router.post("/chat")
    async def chat(body: ChatMessage):
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

        model_config = ModelConfig(model_id=body.model)

        if model_config.provider == ProviderType.OPENROUTER and not openrouter_key:
            raise HTTPException(400, "OPENROUTER_API_KEY not set")
        if model_config.provider == ProviderType.ANTHROPIC and not anthropic_key:
            raise HTTPException(400, "ANTHROPIC_API_KEY not set")

        archetypes = _cached_archetypes()

        routes: list[Route] = []
        for name, data in archetypes.items():
            if name == "router":
                continue
            agent = Agent(
                name=data["name"],
                instructions=data.get("instructions", ""),
                model=model_config,
                tools=[],
                max_turns=data.get("max_turns", 10),
                description=data.get("description", ""),
            )
            routes.append(Route(
                intent=data.get("description", name),
                agent=agent,
            ))

        if not routes:
            raise HTTPException(500, "No agent archetypes found")

        router_archetype = archetypes.get("router", {})
        router_model_id = router_archetype.get("model", body.model)
        router_model = ModelConfig(model_id=router_model_id)

        # Fall back to user's model if the router archetype's provider key isn't available
        router_key_missing = (
            (router_model.provider == ProviderType.OPENROUTER and not openrouter_key)
            or (router_model.provider == ProviderType.ANTHROPIC and not anthropic_key)
        )
        if router_key_missing:
            router_model = model_config

        triage = TriageRouter(
            name="chat-router",
            router_model=router_model,
            routes=routes,
        )

        model_router = ModelRouter(
            anthropic_api_key=anthropic_key or "unused",
            openrouter_api_key=openrouter_key or None,
        )
        event_bus = EventBus()
        tool_registry = ToolRegistry()
        runner = Runner(
            router=model_router,
            tool_registry=tool_registry,
            event_bus=event_bus,
        )

        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def event_handler(event: Event) -> None:
            payload = {
                "type": event.event_type.value,
                "agent": event.agent_name,
                "data": event.data,
                "run_id": event.run_id,
            }
            await queue.put(payload)

        event_bus.subscribe_all(event_handler)

        run_id = str(uuid.uuid4())

        async def run_triage() -> None:
            try:
                result = await triage.execute(
                    runner=runner, task=body.message, run_id=run_id,
                )
                await queue.put({
                    "type": "chat.response",
                    "agent": result.selected_agent,
                    "data": {"output": result.output},
                    "run_id": run_id,
                })
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Chat run failed for run_id=%s", run_id)
                await queue.put({
                    "type": "chat.error",
                    "agent": "",
                    "data": {"error": "An internal error occurred. Please try again."},
                    "run_id": run_id,
                })
            finally:
                await model_router.close()
                await queue.put(None)

        task = asyncio.create_task(run_triage())

        async def event_stream():
            try:
                while True:
                    payload = await queue.get()
                    if payload is None:
                        break
                    yield f"data: {json.dumps(payload)}\n\n"
            finally:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return router
