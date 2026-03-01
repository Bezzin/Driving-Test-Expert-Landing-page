"""Tests for role-to-tools mapping."""
import pytest
from airees.coordinator.worker_builder import ROLE_TOOLS, get_tools_for_role, build_worker_prompt


def test_researcher_gets_search_tools():
    tools = get_tools_for_role("researcher")
    assert "web_search" in tools
    assert "web_extract" in tools


def test_coder_gets_no_tools():
    tools = get_tools_for_role("coder")
    assert tools == []


def test_reviewer_gets_search():
    tools = get_tools_for_role("reviewer")
    assert "web_search" in tools


def test_unknown_role_gets_empty():
    tools = get_tools_for_role("unknown_role")
    assert tools == []


def test_worker_prompt_includes_tool_instructions():
    prompt = build_worker_prompt(
        task_title="Research AI",
        task_description="Find AI papers",
        agent_role="researcher",
        available_tools=["web_search"],
    )
    assert "web_search" in prompt
    assert "tool" in prompt.lower()


def test_worker_prompt_no_tools_no_instructions():
    prompt = build_worker_prompt(
        task_title="Write code",
        task_description="Build a function",
        agent_role="coder",
    )
    assert "web_search" not in prompt
