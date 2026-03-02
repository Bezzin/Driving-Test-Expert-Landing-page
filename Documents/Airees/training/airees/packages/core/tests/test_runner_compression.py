"""Tests for Runner + ContextCompressor integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from airees.agent import Agent
from airees.context_budget import ContextBudget
from airees.context_compressor import ContextCompressor
from airees.events import EventBus, EventType
from airees.runner import Runner
from airees.tools.registry import ToolRegistry
from airees.router.types import ModelConfig


def _make_text_response(text: str, input_tokens: int = 50, output_tokens: int = 50) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


@pytest.mark.asyncio
async def test_runner_accepts_compressor_field():
    """Runner should accept an optional compressor parameter."""
    runner = Runner(
        router=AsyncMock(),
        tool_registry=ToolRegistry(),
        event_bus=EventBus(),
        compressor=None,
    )
    assert runner.compressor is None


@pytest.mark.asyncio
async def test_runner_compresses_when_budget_exceeds_70_percent():
    """Runner should compress messages when budget exceeds 70%."""
    mock_router = AsyncMock()
    mock_router.create_message = AsyncMock(
        return_value=_make_text_response("Done", input_tokens=80000, output_tokens=80000)
    )

    budget = ContextBudget(max_tokens=200000, used_tokens=0)
    compressor = ContextCompressor(router=mock_router, budget=budget)

    captured_events = []
    event_bus = EventBus()
    event_bus.subscribe_all(lambda e: captured_events.append(e))

    agent = Agent(
        name="test",
        instructions="test",
        model=ModelConfig(model_id="test-model"),
        max_turns=1,
        context_budget=budget,
    )

    runner = Runner(
        router=mock_router,
        tool_registry=ToolRegistry(),
        event_bus=event_bus,
        compressor=compressor,
    )

    await runner.run(agent=agent, task="test task")

    compressed_events = [e for e in captured_events if e.event_type == EventType.CONTEXT_COMPRESSED]
    assert len(compressed_events) == 1
    assert "stage" in compressed_events[0].data


@pytest.mark.asyncio
async def test_runner_no_compression_below_70_percent():
    """Runner should NOT compress when budget is below 70%."""
    mock_router = AsyncMock()
    mock_router.create_message = AsyncMock(
        return_value=_make_text_response("Done", input_tokens=100, output_tokens=100)
    )

    budget = ContextBudget(max_tokens=200000, used_tokens=0)
    compressor = ContextCompressor(router=mock_router, budget=budget)

    captured_events = []
    event_bus = EventBus()
    event_bus.subscribe_all(lambda e: captured_events.append(e))

    agent = Agent(
        name="test",
        instructions="test",
        model=ModelConfig(model_id="test-model"),
        max_turns=1,
        context_budget=budget,
    )

    runner = Runner(
        router=mock_router,
        tool_registry=ToolRegistry(),
        event_bus=event_bus,
        compressor=compressor,
    )

    await runner.run(agent=agent, task="test task")

    compressed_events = [e for e in captured_events if e.event_type == EventType.CONTEXT_COMPRESSED]
    assert len(compressed_events) == 0


@pytest.mark.asyncio
async def test_runner_without_compressor_still_works():
    """Runner with compressor=None should work as before."""
    mock_router = AsyncMock()
    mock_router.create_message = AsyncMock(
        return_value=_make_text_response("Done")
    )

    agent = Agent(
        name="test",
        instructions="test",
        model=ModelConfig(model_id="test-model"),
        max_turns=1,
    )

    runner = Runner(
        router=mock_router,
        tool_registry=ToolRegistry(),
        event_bus=EventBus(),
    )

    result = await runner.run(agent=agent, task="test task")
    assert result.output == "Done"
