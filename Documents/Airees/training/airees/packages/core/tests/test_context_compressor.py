"""Tests for progressive context compression."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from airees.context_budget import ContextBudget
from airees.context_compressor import ContextCompressor


def _mock_router(summary_text: str = "Summary of output."):
    router = AsyncMock()
    block = MagicMock()
    block.type = "text"
    block.text = summary_text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(input_tokens=50, output_tokens=20)
    router.create_message.return_value = response
    return router


def test_detect_stage_no_compression():
    budget = ContextBudget(max_tokens=1000, used_tokens=500)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 0


def test_detect_stage_1():
    budget = ContextBudget(max_tokens=1000, used_tokens=750)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 1


def test_detect_stage_2():
    budget = ContextBudget(max_tokens=1000, used_tokens=850)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 2


def test_detect_stage_3():
    budget = ContextBudget(max_tokens=1000, used_tokens=920)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 3


def test_detect_stage_4():
    budget = ContextBudget(max_tokens=1000, used_tokens=960)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 4


@pytest.mark.asyncio
async def test_compress_stage_0_passthrough():
    budget = ContextBudget(max_tokens=1000, used_tokens=100)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Do task"},
        {"role": "assistant", "content": "Here's the full output of the task."},
    ]
    result = await compressor.compress(messages, stage=0)
    assert result == messages


@pytest.mark.asyncio
async def test_compress_stage_1_summarizes():
    router = _mock_router("Summarized output.")
    budget = ContextBudget(max_tokens=1000, used_tokens=650)
    compressor = ContextCompressor(router=router, budget=budget)
    messages = [
        {"role": "user", "content": "Do task 1"},
        {"role": "assistant", "content": "A" * 500},
        {"role": "user", "content": "Do task 2"},
        {"role": "assistant", "content": "B" * 500},
    ]
    result = await compressor.compress(messages, stage=1)
    assert len(result) == len(messages)
    assert "Summarized" in result[1]["content"] or len(result[1]["content"]) < 500


@pytest.mark.asyncio
async def test_compress_stage_4_emergency():
    budget = ContextBudget(max_tokens=1000, used_tokens=960)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Task 1"},
        {"role": "assistant", "content": "Output 1"},
        {"role": "user", "content": "Task 2"},
        {"role": "assistant", "content": "Output 2"},
        {"role": "user", "content": "Task 3"},
        {"role": "assistant", "content": "Output 3"},
    ]
    result = await compressor.compress(messages, stage=4)
    assert len(result) <= 2


@pytest.mark.asyncio
async def test_compress_stage_2_collapses_pairs():
    budget = ContextBudget(max_tokens=1000, used_tokens=780)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Task 1"},
        {"role": "assistant", "content": "Output 1"},
        {"role": "user", "content": "Task 2"},
        {"role": "assistant", "content": "Output 2"},
        {"role": "user", "content": "Task 3"},
        {"role": "assistant", "content": "Output 3"},
    ]
    result = await compressor.compress(messages, stage=2)
    # Last 4 messages kept verbatim, earlier collapsed into one summary
    assert len(result) == 5  # 1 collapsed + 4 recent
    assert "[Compressed earlier context]" in result[0]["content"]
    assert result[-1]["content"] == "Output 3"


@pytest.mark.asyncio
async def test_compress_stage_2_short_passthrough():
    budget = ContextBudget(max_tokens=1000, used_tokens=780)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Task 1"},
        {"role": "assistant", "content": "Output 1"},
    ]
    result = await compressor.compress(messages, stage=2)
    # <= 4 messages: returned as-is
    assert result == messages


@pytest.mark.asyncio
async def test_compress_stage_3_checkpoint_trim():
    budget = ContextBudget(max_tokens=1000, used_tokens=870)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Task 1"},
        {"role": "assistant", "content": "Output 1"},
        {"role": "user", "content": "Task 2"},
        {"role": "assistant", "content": "Output 2"},
        {"role": "user", "content": "Task 3"},
        {"role": "assistant", "content": "Output 3"},
    ]
    result = await compressor.compress(messages, stage=3)
    assert len(result) == 2
    assert result[0]["content"] == "Task 3"
    assert result[1]["content"] == "Output 3"


@pytest.mark.asyncio
async def test_emergency_trim_preserves_chronological_order():
    budget = ContextBudget(max_tokens=1000, used_tokens=960)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Old task"},
        {"role": "assistant", "content": "Old output"},
        {"role": "user", "content": "Latest task"},
        {"role": "assistant", "content": "Latest output"},
    ]
    result = await compressor.compress(messages, stage=4)
    assert len(result) == 2
    # User must come before assistant (chronological)
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"


def test_update_budget():
    budget = ContextBudget(max_tokens=1000, used_tokens=500)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    compressor.update_budget(ContextBudget(max_tokens=1000, used_tokens=700))
    assert compressor.budget.used_tokens == 700


def test_thresholds_are_70_80_90_95():
    """Verify compressor uses corpus-recommended thresholds."""
    from airees.context_budget import ContextBudget
    compressor = ContextCompressor(router=None, budget=ContextBudget(max_tokens=1000, used_tokens=0))
    assert compressor._THRESHOLDS == (70.0, 80.0, 90.0, 95.0)


def test_detect_stage_at_65_percent_is_zero():
    """65% should be stage 0 (below 70% threshold)."""
    from airees.context_budget import ContextBudget
    budget = ContextBudget(max_tokens=1000, used_tokens=650)
    compressor = ContextCompressor(router=None, budget=budget)
    assert compressor.detect_stage() == 0


def test_detect_stage_at_72_percent_is_one():
    """72% should be stage 1 (between 70% and 80%)."""
    from airees.context_budget import ContextBudget
    budget = ContextBudget(max_tokens=1000, used_tokens=720)
    compressor = ContextCompressor(router=None, budget=budget)
    assert compressor.detect_stage() == 1
