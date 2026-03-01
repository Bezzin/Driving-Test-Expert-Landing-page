import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from airees_server.app import create_app
from airees.runner import RunResult, TokenUsage


@pytest.fixture
def client(tmp_path):
    app = create_app(data_dir=tmp_path)
    return TestClient(app)


def test_create_run_without_api_key(client, monkeypatch):
    # Default model is openrouter/... so missing OPENROUTER_API_KEY triggers 400
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post("/api/runs", json={
        "agent_name": "researcher",
        "task": "What is AI?",
    })
    assert response.status_code == 400
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_create_run_with_mocked_runner(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")

    mock_result = RunResult(
        output="AI is artificial intelligence.",
        turns=1,
        token_usage=TokenUsage(input_tokens=50, output_tokens=20),
        run_id="test-run",
        agent_name="researcher",
    )

    with patch("airees_server.routes.runs.Runner") as MockRunner:
        instance = MockRunner.return_value
        instance.run = AsyncMock(return_value=mock_result)

        response = client.post("/api/runs", json={
            "agent_name": "researcher",
            "task": "What is AI?",
        })

    assert response.status_code == 201
    data = response.json()
    assert data["output"] == "AI is artificial intelligence."
    assert data["turns"] == 1
