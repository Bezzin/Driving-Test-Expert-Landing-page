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
    ]
