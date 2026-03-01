"""Tests for the intent classifier."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from airees.brain.intent import GoalIntent, classify_intent, intent_to_prompt_hint
from airees.brain.prompt import build_brain_prompt
from airees.soul import Soul


def test_goal_intent_values():
    assert GoalIntent.RESEARCH.value == "research"
    assert GoalIntent.BUILD.value == "build"
    assert GoalIntent.FIX.value == "fix"
    assert GoalIntent.INVESTIGATE.value == "investigate"
    assert GoalIntent.OPTIMIZE.value == "optimize"


@pytest.mark.asyncio
async def test_classify_intent_research():
    mock_router = AsyncMock()
    response = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "research"
    response.content = [block]
    mock_router.create_message = AsyncMock(return_value=response)

    intent = await classify_intent(mock_router, "Find information about quantum computing")
    assert intent == GoalIntent.RESEARCH


@pytest.mark.asyncio
async def test_classify_intent_defaults_to_build():
    mock_router = AsyncMock()
    response = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "something_unknown"
    response.content = [block]
    mock_router.create_message = AsyncMock(return_value=response)

    intent = await classify_intent(mock_router, "Do something vague")
    assert intent == GoalIntent.BUILD


def test_intent_to_prompt_hint_research():
    hint = intent_to_prompt_hint(GoalIntent.RESEARCH)
    assert "research" in hint.lower()
    assert "search" in hint.lower()


def test_intent_to_prompt_hint_fix():
    hint = intent_to_prompt_hint(GoalIntent.FIX)
    assert "fix" in hint.lower() or "debug" in hint.lower()


def test_brain_prompt_includes_intent():
    soul = Soul(name="Test", version=0, content="Test soul", raw="")
    prompt = build_brain_prompt(
        soul=soul, goal="Fix the login bug", intent="fix",
    )
    assert "fix" in prompt.lower() or "debug" in prompt.lower()
