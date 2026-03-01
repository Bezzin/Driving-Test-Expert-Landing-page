"""Tests for Brain tool definitions."""
from airees.brain.tools import get_brain_tools


def test_brain_tools_exist():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "create_plan" in names
    assert "evaluate_result" in names
    assert "adapt_plan" in names
    assert "message_user" in names


def test_create_plan_schema():
    tools = get_brain_tools()
    create_plan = next(t for t in tools if t.name == "create_plan")
    props = create_plan.input_schema["properties"]
    assert "tasks" in props
    assert "model_recommendations" in props


def test_evaluate_result_schema():
    tools = get_brain_tools()
    evaluate = next(t for t in tools if t.name == "evaluate_result")
    props = evaluate.input_schema["properties"]
    assert "satisfied" in props
    assert "reasoning" in props
    assert "action" in props
