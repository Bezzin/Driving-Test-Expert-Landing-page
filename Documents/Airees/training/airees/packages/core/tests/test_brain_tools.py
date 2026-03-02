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


def test_brain_tools_include_search_corpus():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "search_corpus" in names


def test_brain_tools_include_search_skills():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "search_skills" in names


def test_brain_tools_include_create_skill():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "create_skill" in names


def test_brain_tools_include_update_skill():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "update_skill" in names


def test_brain_tools_include_update_soul():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "update_soul" in names


def test_search_corpus_tool_schema():
    tools = get_brain_tools()
    tool = next(t for t in tools if t.name == "search_corpus")
    assert "query" in tool.input_schema["properties"]
    assert "query" in tool.input_schema["required"]


def test_create_skill_tool_schema():
    tools = get_brain_tools()
    tool = next(t for t in tools if t.name == "create_skill")
    props = tool.input_schema["properties"]
    assert "name" in props
    assert "description" in props
    assert "triggers" in props
    assert "task_graph" in props
