"""Tests for worker builder — model selection and prompt assembly."""
import pytest
from airees.coordinator.worker_builder import build_worker_prompt, select_model


def test_select_model_for_code_task():
    model = select_model(agent_role="coder", recommended=None)
    assert "haiku" in model.lower() or "free" in model.lower()


def test_select_model_uses_recommendation():
    model = select_model(agent_role="coder", recommended="openrouter/meta-llama/llama-3.3-70b-instruct:free")
    assert "llama" in model.lower()


def test_select_model_for_research():
    model = select_model(agent_role="researcher", recommended=None)
    assert model  # returns a non-empty string


def test_build_worker_prompt():
    prompt = build_worker_prompt(
        task_title="Scaffold project",
        task_description="Create a Next.js project with TypeScript and Tailwind",
        agent_role="coder",
    )
    assert "Scaffold project" in prompt
    assert "Next.js" in prompt
    assert "coder" in prompt.lower() or "code" in prompt.lower()


def test_build_worker_prompt_with_skill():
    prompt = build_worker_prompt(
        task_title="Add auth",
        task_description="Integrate Clerk authentication",
        agent_role="coder",
        skill_content="## Auth Pattern\nUse Clerk for auth.",
    )
    assert "Clerk" in prompt
    assert "Auth Pattern" in prompt


def test_build_worker_prompt_with_previous_output():
    prompt = build_worker_prompt(
        task_title="Add API routes",
        task_description="Build REST endpoints",
        agent_role="coder",
        previous_output="Project scaffolded at /app with Next.js 15",
    )
    assert "scaffolded" in prompt
