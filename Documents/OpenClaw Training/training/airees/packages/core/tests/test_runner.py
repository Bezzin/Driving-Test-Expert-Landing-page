# tests/test_runner.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from airees.runner import Runner, RunResult, TokenUsage
from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus


@pytest.fixture
def runner():
    router = ModelRouter(anthropic_api_key="test-key")
    return Runner(router=router, tool_registry=ToolRegistry(), event_bus=EventBus())


@pytest.fixture
def agent():
    return Agent(
        name="test-agent",
        instructions="You are a test assistant.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )


def test_runner_creation(runner):
    assert runner.router is not None
    assert runner.tool_registry is not None


def test_token_usage():
    usage = TokenUsage(input_tokens=100, output_tokens=50)
    assert usage.total_tokens == 150


def test_run_result_creation():
    result = RunResult(
        output="Hello",
        turns=1,
        token_usage=TokenUsage(input_tokens=10, output_tokens=5),
        run_id="r1",
        agent_name="test",
    )
    assert result.output == "Hello"
    assert result.turns == 1
    assert result.token_usage.total_tokens == 15


@pytest.mark.asyncio
async def test_run_simple_agent(runner, agent):
    """Agent responds with text (no tool calls) = single turn."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Hello world")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = MagicMock(input_tokens=50, output_tokens=10)
    mock_response.model = "claude-sonnet-4-6"

    with patch.object(
        runner.router, "create_message",
        new_callable=AsyncMock, return_value=mock_response,
    ):
        result = await runner.run(agent=agent, task="Say hello")
        assert isinstance(result, RunResult)
        assert result.output == "Hello world"
        assert result.turns == 1
        assert result.token_usage.input_tokens == 50


@pytest.mark.asyncio
async def test_run_emits_events(runner, agent):
    """Verify events are emitted during run."""
    events_received = []

    def handler(event):
        events_received.append(event.event_type.value)

    runner.event_bus.subscribe_all(handler)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Done")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)

    with patch.object(
        runner.router, "create_message",
        new_callable=AsyncMock, return_value=mock_response,
    ):
        await runner.run(agent=agent, task="Test")

    assert "run.start" in events_received
    assert "agent.start" in events_received
    assert "agent.complete" in events_received
    assert "run.complete" in events_received


@pytest.mark.asyncio
async def test_runner_emits_context_warning(runner):
    """Runner should emit CONTEXT_WARNING when budget threshold exceeded."""
    from airees.context_budget import ContextBudget
    from airees.events import EventType

    agent_with_budget = Agent(
        name="budget-agent",
        instructions="You are a test assistant.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        context_budget=ContextBudget(
            max_tokens=1000,
            max_usage_percent=50.0,
        ),
    )

    warnings_received = []

    def warning_handler(event):
        warnings_received.append(event)

    runner.event_bus.subscribe(EventType.CONTEXT_WARNING, warning_handler)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Done")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = MagicMock(input_tokens=600, output_tokens=100)

    with patch.object(
        runner.router, "create_message",
        new_callable=AsyncMock, return_value=mock_response,
    ):
        await runner.run(agent=agent_with_budget, task="Test budget")

    assert len(warnings_received) >= 1
    warning = warnings_received[0]
    assert warning.event_type == EventType.CONTEXT_WARNING
    assert warning.agent_name == "budget-agent"
    assert warning.data["used_tokens"] == 700
    assert warning.data["effective_max"] == 500
