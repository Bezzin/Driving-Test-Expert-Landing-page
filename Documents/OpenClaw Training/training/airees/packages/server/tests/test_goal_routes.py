"""Tests for goal submission API routes."""
import pytest
from httpx import AsyncClient, ASGITransport
from airees_server.app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(data_dir=tmp_path / "data")


@pytest.mark.asyncio
async def test_submit_goal(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/goals", json={"description": "Build a todo app"})
        assert resp.status_code == 201
        data = resp.json()
        assert "goal_id" in data


@pytest.mark.asyncio
async def test_get_goal(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/goals", json={"description": "Build a todo app"})
        goal_id = create_resp.json()["goal_id"]
        resp = await client.get(f"/api/goals/{goal_id}")
        assert resp.status_code == 200
        assert resp.json()["description"] == "Build a todo app"


@pytest.mark.asyncio
async def test_list_goals(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/goals", json={"description": "Goal 1"})
        await client.post("/api/goals", json={"description": "Goal 2"})
        resp = await client.get("/api/goals")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_goal_progress(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/goals", json={"description": "Build app"})
        goal_id = create_resp.json()["goal_id"]
        resp = await client.get(f"/api/goals/{goal_id}/progress")
        assert resp.status_code == 200
        assert "total" in resp.json()
