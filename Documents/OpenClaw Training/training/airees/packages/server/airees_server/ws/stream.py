from __future__ import annotations

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


def create_ws_router() -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/runs/{run_id}")
    async def run_stream(websocket: WebSocket, run_id: str):
        await websocket.accept()
        await websocket.send_json({"type": "connected", "run_id": run_id})

        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass

    return router
