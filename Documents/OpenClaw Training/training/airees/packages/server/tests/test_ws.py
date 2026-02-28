import pytest
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from airees_server.ws.stream import create_ws_router


@pytest.fixture
def app():
    app = FastAPI()
    app.state.active_runs = {}
    app.include_router(create_ws_router())
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_ws_connect_and_receive(client):
    with client.websocket_connect("/ws/runs/test-run-123") as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "connected"
        assert data["run_id"] == "test-run-123"
