"""Tool definitions for the Brain agent."""
from __future__ import annotations

from airees.tools.registry import ToolDefinition


def get_brain_tools() -> list[ToolDefinition]:
    """Return the set of tools available to the Brain agent.

    These are structured-output tools that produce JSON the Coordinator
    parses. They do not call external APIs — they define the schema for
    the Brain's decisions.

    Tools:
        create_plan: Create a task graph to achieve the goal.
        evaluate_result: Judge whether completed work satisfies the goal.
        adapt_plan: Modify the existing task graph mid-execution.
        message_user: Send a message to the user (results, updates, questions).
        search_corpus: Search training corpus for best practices.
        search_skills: Search for existing skills matching a goal.
        create_skill: Create a new skill from successful execution.
        update_skill: Update an existing skill.
        update_soul: Reflect and update SOUL.md.
    """
    return [
        ToolDefinition(
            name="create_plan",
            description="Create a task graph to achieve the goal.",
            input_schema={
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "agent_role": {"type": "string"},
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": (
                                        "Indices of tasks this depends on (0-based)"
                                    ),
                                },
                                "priority": {
                                    "type": "integer",
                                    "enum": [0, 1, 2, 3],
                                    "description": "Task priority: 0=critical, 1=high, 2=normal, 3=low",
                                },
                                "model": {
                                    "type": "string",
                                    "description": "Recommended model ID",
                                },
                            },
                            "required": ["title", "description", "agent_role"],
                        },
                    },
                    "model_recommendations": {
                        "type": "object",
                        "description": "Default model for each agent role",
                        "additionalProperties": {"type": "string"},
                    },
                    "strategy": {
                        "type": "string",
                        "description": (
                            "Brief explanation of the overall approach"
                        ),
                    },
                },
                "required": ["tasks"],
            },
        ),
        ToolDefinition(
            name="evaluate_result",
            description="Evaluate the completed work from the Coordinator.",
            input_schema={
                "type": "object",
                "properties": {
                    "satisfied": {"type": "boolean"},
                    "reasoning": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": ["satisfied", "adapt", "rewrite"],
                    },
                    "changes": {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                },
                "required": ["satisfied", "reasoning", "action"],
            },
        ),
        ToolDefinition(
            name="adapt_plan",
            description="Modify the existing task graph.",
            input_schema={
                "type": "object",
                "properties": {
                    "add_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "agent_role": {"type": "string"},
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["title", "description", "agent_role"],
                        },
                    },
                    "remove_task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "reasoning": {"type": "string"},
                },
                "required": ["reasoning"],
            },
        ),
        ToolDefinition(
            name="message_user",
            description="Send a message to the user.",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["result", "update", "question"],
                    },
                },
                "required": ["message", "type"],
            },
        ),
        ToolDefinition(
            name="search_corpus",
            description="Search training corpus for best practices.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {
                        "type": "integer",
                        "default": 3,
                        "description": "Number of results to return",
                    },
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="search_skills",
            description="Search for existing skills matching a goal.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="create_skill",
            description="Create a new skill from successful execution.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "triggers": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "task_graph": {"type": "string"},
                    "lessons_learned": {"type": "string"},
                    "quality_gates": {"type": "string"},
                    "known_pitfalls": {"type": "string"},
                },
                "required": ["name", "description", "triggers", "task_graph"],
            },
        ),
        ToolDefinition(
            name="update_skill",
            description="Update an existing skill.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "lessons_learned": {"type": "string"},
                    "known_pitfalls": {"type": "string"},
                    "task_graph": {"type": "string"},
                },
                "required": ["name"],
            },
        ),
        ToolDefinition(
            name="update_soul",
            description="Reflect and update SOUL.md.",
            input_schema={
                "type": "object",
                "properties": {
                    "capabilities_update": {
                        "type": "object",
                        "properties": {
                            "skills_mastered": {"type": "integer"},
                            "goals_completed": {"type": "integer"},
                            "total_iterations": {"type": "integer"},
                        },
                    },
                    "strategy_update": {"type": "string"},
                    "lesson": {"type": "string"},
                },
            },
        ),
    ]
