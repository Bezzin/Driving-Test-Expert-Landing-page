import pytest
from unittest.mock import AsyncMock, patch
from airees.orchestration.parallel import ParallelTeam, ParallelTask
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
        "analyst_a": Agent(name="analyst_a", instructions="Analyze A.", model=ModelConfig(model_id="claude-sonnet-4-6")),
        "analyst_b": Agent(name="analyst_b", instructions="Analyze B.", model=ModelConfig(model_id="claude-sonnet-4-6")),
    }


@pytest.mark.asyncio
async def test_parallel_runs_concurrently(runner, agents):
    team = ParallelTeam(
        name="analysis-team",
        tasks=[
            ParallelTask(agent=agents["analyst_a"], task="Analyze market trends"),
            ParallelTask(agent=agents["analyst_b"], task="Analyze competitor data"),
        ],
    )

    result_a = RunResult(output="Trends up", turns=1, token_usage=TokenUsage(10, 5), run_id="r1", agent_name="analyst_a")
    result_b = RunResult(output="Competitor strong", turns=1, token_usage=TokenUsage(10, 5), run_id="r2", agent_name="analyst_b")

    with patch.object(runner, "run", new_callable=AsyncMock, side_effect=[result_a, result_b]):
        result = await team.execute(runner=runner)

    assert len(result.task_results) == 2
    assert result.total_turns == 2
