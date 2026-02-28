import pytest
from unittest.mock import AsyncMock, patch
from airees.orchestration.pipeline import Pipeline, PipelineStep
from airees.agent import Agent
from airees.quality_gate import GateAction, QualityGate
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
        "researcher": Agent(
            name="researcher",
            instructions="Research the topic.",
            model=ModelConfig(model_id="claude-sonnet-4-6"),
        ),
        "writer": Agent(
            name="writer",
            instructions="Write a report.",
            model=ModelConfig(model_id="claude-sonnet-4-6"),
        ),
    }


def test_pipeline_creation(agents):
    pipeline = Pipeline(
        name="research-pipeline",
        steps=[
            PipelineStep(agent=agents["researcher"], task_template="Research {{topic}}"),
            PipelineStep(agent=agents["writer"], task_template="Write report based on: {{previous_output}}"),
        ],
    )
    assert len(pipeline.steps) == 2


@pytest.mark.asyncio
async def test_pipeline_runs_sequentially(runner, agents):
    pipeline = Pipeline(
        name="test",
        steps=[
            PipelineStep(agent=agents["researcher"], task_template="Research AI"),
            PipelineStep(agent=agents["writer"], task_template="Write about: {{previous_output}}"),
        ],
    )

    run_result_1 = RunResult(
        output="AI is transformative",
        turns=1,
        token_usage=TokenUsage(input_tokens=50, output_tokens=20),
        run_id="r1",
        agent_name="researcher",
    )
    run_result_2 = RunResult(
        output="Report: AI is transformative and growing.",
        turns=1,
        token_usage=TokenUsage(input_tokens=60, output_tokens=30),
        run_id="r2",
        agent_name="writer",
    )

    with patch.object(
        runner, "run",
        new_callable=AsyncMock,
        side_effect=[run_result_1, run_result_2],
    ):
        result = await pipeline.execute(runner=runner, variables={"topic": "AI"})

    assert result.output == "Report: AI is transformative and growing."
    assert result.total_turns == 2
    assert len(result.step_results) == 2


@pytest.mark.asyncio
async def test_pipeline_with_gate_pass(runner, agents):
    """Pipeline step with passing quality gate continues normally."""
    scorer = Agent(
        name="scorer",
        instructions="Score the output.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    gate = QualityGate(name="quality-check", min_score=7.0, max_retries=2)

    pipeline = Pipeline(
        name="gated",
        steps=[
            PipelineStep(agent=agents["researcher"], task_template="Research AI"),
            PipelineStep(
                agent=scorer,
                task_template="Score this: {{previous_output}}",
                quality_gate=gate,
            ),
            PipelineStep(
                agent=agents["writer"],
                task_template="Write about: {{previous_output}}",
            ),
        ],
    )

    result_research = RunResult(
        output="AI findings",
        turns=1,
        token_usage=TokenUsage(input_tokens=50, output_tokens=20),
        run_id="r1",
        agent_name="researcher",
    )
    result_score = RunResult(
        output="Score: 9",
        turns=1,
        token_usage=TokenUsage(input_tokens=30, output_tokens=10),
        run_id="r1",
        agent_name="scorer",
    )
    result_write = RunResult(
        output="Final report on AI",
        turns=1,
        token_usage=TokenUsage(input_tokens=60, output_tokens=30),
        run_id="r1",
        agent_name="writer",
    )

    with patch.object(
        runner, "run",
        new_callable=AsyncMock,
        side_effect=[result_research, result_score, result_write],
    ):
        result = await pipeline.execute(runner=runner, variables={})

    assert result.output == "Final report on AI"
    assert len(result.step_results) == 3
    assert result.total_turns == 3


@pytest.mark.asyncio
async def test_pipeline_with_gate_fail_and_retry(runner, agents):
    """Failing quality gate retries the previous step."""
    scorer = Agent(
        name="scorer",
        instructions="Score the output.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    gate = QualityGate(name="quality-check", min_score=8.0, max_retries=2)

    pipeline = Pipeline(
        name="gated-retry",
        steps=[
            PipelineStep(agent=agents["researcher"], task_template="Research AI"),
            PipelineStep(
                agent=scorer,
                task_template="Score this: {{previous_output}}",
                quality_gate=gate,
            ),
        ],
    )

    result_research_1 = RunResult(
        output="AI findings v1",
        turns=1,
        token_usage=TokenUsage(input_tokens=50, output_tokens=20),
        run_id="r1",
        agent_name="researcher",
    )
    result_score_fail = RunResult(
        output="Score: 5",
        turns=1,
        token_usage=TokenUsage(input_tokens=30, output_tokens=10),
        run_id="r1",
        agent_name="scorer",
    )
    result_research_2 = RunResult(
        output="AI findings v2 improved",
        turns=1,
        token_usage=TokenUsage(input_tokens=55, output_tokens=25),
        run_id="r1",
        agent_name="researcher",
    )
    result_score_pass = RunResult(
        output="Score: 9",
        turns=1,
        token_usage=TokenUsage(input_tokens=30, output_tokens=10),
        run_id="r1",
        agent_name="scorer",
    )

    with patch.object(
        runner, "run",
        new_callable=AsyncMock,
        side_effect=[
            result_research_1,
            result_score_fail,
            result_research_2,
            result_score_pass,
        ],
    ):
        result = await pipeline.execute(runner=runner, variables={})

    # 4 steps executed: research, score(fail), research(retry), score(pass)
    assert len(result.step_results) == 4
    assert result.total_turns == 4
    assert result.output == "Score: 9"
