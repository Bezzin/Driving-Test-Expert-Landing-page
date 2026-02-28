"""Tests for the Agent dataclass."""

import pytest

from airees.agent import Agent
from airees.router.types import ModelConfig


def test_agent_creation():
    agent = Agent(
        name="researcher",
        instructions="You are a research specialist.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    assert agent.name == "researcher"
    assert agent.instructions == "You are a research specialist."
    assert agent.model.model_id == "claude-sonnet-4-6"
    assert agent.tools == []
    assert agent.max_turns == 10


def test_agent_with_tools():
    agent = Agent(
        name="coder",
        instructions="You write code.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        tools=["file_read", "file_write"],
    )
    assert agent.tools == ["file_read", "file_write"]


def test_agent_is_immutable():
    agent = Agent(
        name="test",
        instructions="test",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    with pytest.raises(AttributeError):
        agent.name = "changed"


def test_agent_with_description():
    agent = Agent(
        name="researcher",
        instructions="Research things.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        description="Web research specialist",
    )
    assert agent.description == "Web research specialist"


def test_agent_with_memory_files():
    agent = Agent(
        name="researcher",
        instructions="Research.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        memory_files={"personality": "SOUL.md", "context": "MEMORY.md"},
    )
    assert agent.memory_files["personality"] == "SOUL.md"
