import pytest
from fastapi.testclient import TestClient
from airees_server.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(data_dir=tmp_path)
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_archetypes(client):
    response = client.get("/api/archetypes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8
    assert any(a["name"] == "researcher" for a in data)


def test_create_and_get_agent(client):
    agent_config = {
        "name": "my-researcher",
        "model": "claude-sonnet-4-6",
        "instructions": "You research things.",
        "tools": ["web_search"],
    }
    response = client.post("/api/agents", json=agent_config)
    assert response.status_code == 201

    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()
    assert any(a["name"] == "my-researcher" for a in agents)
