"""Tests for zero-cost keyword-based complexity classifier."""
from __future__ import annotations

import pytest

from airees.gateway.complexity import Complexity, classify_complexity


# -- Enum values --------------------------------------------------------------


def test_enum_values():
    assert Complexity.QUICK.value == "quick"
    assert Complexity.MODERATE.value == "moderate"
    assert Complexity.COMPLEX.value == "complex"


# -- model_hint property ------------------------------------------------------


def test_model_hint_property():
    assert Complexity.QUICK.model_hint == "haiku"
    assert Complexity.MODERATE.model_hint == "sonnet"
    assert Complexity.COMPLEX.model_hint == "opus"


# -- classify_complexity: QUICK ------------------------------------------------


@pytest.mark.asyncio
async def test_greeting_returns_quick():
    result = await classify_complexity("hello")
    assert result is Complexity.QUICK


@pytest.mark.asyncio
async def test_short_question_returns_quick():
    result = await classify_complexity("what time is it?")
    assert result is Complexity.QUICK


# -- classify_complexity: MODERATE ---------------------------------------------


@pytest.mark.asyncio
async def test_summarize_returns_moderate():
    result = await classify_complexity("summarize the quarterly report findings")
    assert result is Complexity.MODERATE


# -- classify_complexity: COMPLEX ----------------------------------------------


@pytest.mark.asyncio
async def test_multi_step_plan_returns_complex():
    result = await classify_complexity(
        "plan and create a comprehensive multi-step deployment strategy"
    )
    assert result is Complexity.COMPLEX


@pytest.mark.asyncio
async def test_short_complex_message_returns_complex():
    """Short messages matching complex patterns should be COMPLEX, not QUICK."""
    result = await classify_complexity("plan and deploy")
    assert result is Complexity.COMPLEX


@pytest.mark.asyncio
async def test_long_text_returns_complex():
    long_text = "Please analyze the following situation. " * 10
    assert len(long_text) > 200
    result = await classify_complexity(long_text)
    assert result is Complexity.COMPLEX
