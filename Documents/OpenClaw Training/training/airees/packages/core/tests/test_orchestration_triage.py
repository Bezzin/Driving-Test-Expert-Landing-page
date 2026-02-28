import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from airees.orchestration.triage import TriageRouter, Route
from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.runner import Runner, RunResult, TokenUsage
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus


@pytest.fixture
def runner():
    router = ModelRouter(anthropic_api_key="test")
    return Runner(router=router, tool_registry=ToolRegistry(), event_bus=EventBus())


@pytest.fixture
def agents():
    return {
        "researcher": Agent(name="researcher", instructions="Research.", model=ModelConfig(model_id="claude-sonnet-4-6")),
        "coder": Agent(name="coder", instructions="Code.", model=ModelConfig(model_id="claude-sonnet-4-6")),
    }


@pytest.mark.asyncio
async def test_triage_routes_to_correct_agent(runner, agents):
    triage = TriageRouter(
        name="router",
        router_model=ModelConfig(model_id="claude-haiku-4-5"),
        routes=[
            Route(intent="needs research", agent=agents["researcher"]),
            Route(intent="needs coding", agent=agents["coder"]),
        ],
    )

    # Mock the router deciding "researcher"
    router_response = MagicMock()
    router_response.content = [MagicMock(type="text", text="researcher")]
    router_response.stop_reason = "end_turn"
    router_response.usage = MagicMock(input_tokens=20, output_tokens=5)

    agent_result = RunResult(
        output="Found the answer",
        turns=1,
        token_usage=TokenUsage(50, 20),
        run_id="r1",
        agent_name="researcher",
    )

    with patch.object(runner.router, "create_message", new_callable=AsyncMock, return_value=router_response):
        with patch.object(runner, "run", new_callable=AsyncMock, return_value=agent_result):
            result = await triage.execute(runner=runner, task="Find info about AI safety")

    assert result.selected_agent == "researcher"
    assert result.output == "Found the answer"
