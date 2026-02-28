"""Tests for project state API routes."""
import pytest
from fastapi.testclient import TestClient
from airees_server.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(data_dir=tmp_path)
    return TestClient(app)


def test_create_project_state(client):
    resp = client.post("/api/state", json={
        "project_id": "proj-001", "name": "Test App",
        "phases": ["research", "build", "review"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == "proj-001"
    assert data["current_phase"] == "research"


def test_get_project_state(client):
    client.post("/api/state", json={
        "project_id": "proj-001", "name": "Test App", "phases": ["research", "build"],
    })
    resp = client.get("/api/state/proj-001")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test App"


def test_get_missing_state(client):
    resp = client.get("/api/state/nope")
    assert resp.status_code == 404


def test_advance_state(client):
    client.post("/api/state", json={
        "project_id": "proj-001", "name": "Test", "phases": ["research", "build"],
    })
    resp = client.post("/api/state/proj-001/advance")
    assert resp.status_code == 200
    assert resp.json()["current_phase"] == "build"


def test_fail_state(client):
    client.post("/api/state", json={
        "project_id": "proj-001", "name": "Test", "phases": ["research"],
    })
    resp = client.post("/api/state/proj-001/fail", json={"error": "API down"})
    assert resp.status_code == 200
    assert resp.json()["retry_counts"]["research"] == 1


def test_list_states(client):
    client.post("/api/state", json={"project_id": "a", "name": "A", "phases": ["x"]})
    client.post("/api/state", json={"project_id": "b", "name": "B", "phases": ["y"]})
    resp = client.get("/api/state")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_needs_attention(client):
    client.post("/api/state", json={
        "project_id": "proj-001", "name": "Test", "phases": ["research"],
    })
    for _ in range(3):
        client.post("/api/state/proj-001/fail", json={"error": "fail"})
    resp = client.get("/api/state/needs-attention")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
