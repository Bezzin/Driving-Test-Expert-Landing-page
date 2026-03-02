"""Runner — the core execution engine for Airees agents.

The Runner takes an :class:`Agent` and a task string, then drives a
conversation loop: send messages to the LLM via the :class:`ModelRouter`,
inspect the response for tool-use blocks, execute tools through the
:class:`ToolRegistry`, append tool results, and repeat until the model
stops requesting tools or ``agent.max_turns`` is exhausted.

Every significant lifecycle moment emits an :class:`Event` through the
:class:`EventBus` for observability (streaming, logging, hooks).

Usage::

    runner = Runner(
        router=model_router,
        tool_registry=registry,
        event_bus=event_bus,
    )
    result = await runner.run(agent=agent, task="Summarise this document")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from airees.agent import Agent
from airees.context_compressor import ContextCompressor
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus, Event, EventType


@dataclass(frozen=True)
class TokenUsage:
    """Immutable accumulator for token consumption across turns.

    Attributes:
        input_tokens: Total input (prompt) tokens consumed.
        output_tokens: Total output (completion) tokens consumed.
    """

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Sum of input and output tokens."""
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class RunResult:
    """Immutable outcome of a single :meth:`Runner.run` invocation.

    Attributes:
        output: The final text output produced by the agent.
        turns: Number of LLM round-trips completed.
        token_usage: Aggregated token counts for the entire run.
        run_id: Unique identifier for this run (UUID).
        agent_name: Name of the agent that produced the result.
        messages: Full conversation history including tool results.
    """

    output: str
    turns: int
    token_usage: TokenUsage
    run_id: str
    agent_name: str
    messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Runner:
    """Core execution loop that drives an agent through a task.

    The runner orchestrates the send-receive-tool cycle:

    1. Build the initial message list from the task.
    2. Call the LLM via :attr:`router`.
    3. If the response contains ``tool_use`` blocks, execute each tool
       and append the results as a ``user`` message.
    4. Repeat from step 2 until the model returns ``end_turn`` (or
       another non-tool stop reason) or ``agent.max_turns`` is reached.
    5. Return a :class:`RunResult` with the final text, token totals,
       and full message history.

    Attributes:
        router: The :class:`ModelRouter` used for LLM API calls.
        tool_registry: The :class:`ToolRegistry` containing available tools.
        event_bus: The :class:`EventBus` for emitting lifecycle events.
    """

    router: ModelRouter
    tool_registry: ToolRegistry
    event_bus: EventBus
    compressor: ContextCompressor | None = None

    async def run(
        self,
        agent: Agent,
        task: str,
        run_id: str | None = None,
    ) -> RunResult:
        """Execute an agent on a task and return the result.

        Args:
            agent: The agent definition to run.
            task: The user task / prompt to send.
            run_id: Optional run identifier.  A UUID is generated when
                ``None``.

        Returns:
            A :class:`RunResult` containing the output text, turn count,
            token usage, and full message history.
        """
        run_id = run_id or str(uuid.uuid4())
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": task},
        ]
        total_input = 0
        total_output = 0
        turns = 0

        await self.event_bus.emit_async(Event(
            event_type=EventType.RUN_START,
            agent_name=agent.name,
            run_id=run_id,
            data={"task": task},
        ))

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_START,
            agent_name=agent.name,
            run_id=run_id,
        ))

        tools = (
            self.tool_registry.to_anthropic_format(agent.tools)
            if agent.tools
            else None
        )

        while turns < agent.max_turns:
            turns += 1

            response = await self.router.create_message(
                model=agent.model,
                system=agent.instructions,
                messages=messages,
                tools=tools,
            )

            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

            if agent.context_budget is not None:
                updated_budget = agent.context_budget.consume(
                    response.usage.input_tokens + response.usage.output_tokens
                )
                if updated_budget.is_over_limit:
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.CONTEXT_WARNING,
                        agent_name=agent.name,
                        data={
                            "usage_percent": updated_budget.usage_percent,
                            "used_tokens": updated_budget.used_tokens,
                            "effective_max": updated_budget.effective_max,
                            "message": f"Agent '{agent.name}' exceeded context budget ({updated_budget.usage_percent:.1f}% used)",
                        },
                        run_id=run_id,
                    ))

                # Proactive compression when budget exceeds 70%
                if self.compressor is not None and updated_budget.exceeds_threshold(70.0):
                    self.compressor.update_budget(updated_budget)
                    stage = self.compressor.detect_stage()
                    if stage > 0:
                        before_count = len(messages)
                        messages = await self.compressor.compress(messages, stage)
                        await self.event_bus.emit_async(Event(
                            event_type=EventType.CONTEXT_COMPRESSED,
                            agent_name=agent.name,
                            run_id=run_id,
                            data={
                                "stage": stage,
                                "before_count": before_count,
                                "after_count": len(messages),
                                "usage_percent": updated_budget.usage_percent,
                            },
                        ))

            assistant_content: list[dict[str, Any]] = []
            output_text = ""

            for block in response.content:
                if block.type == "text":
                    output_text += block.text
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.TOOL_CALL,
                        agent_name=agent.name,
                        run_id=run_id,
                        data={"tool": block.name, "input": block.input},
                    ))
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            messages.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason != "tool_use":
                break

            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await self._execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.TOOL_RESULT,
                        agent_name=agent.name,
                        run_id=run_id,
                        data={"tool": block.name, "result": result},
                    ))

            messages.append({"role": "user", "content": tool_results})

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_COMPLETE,
            agent_name=agent.name,
            run_id=run_id,
            data={"output": output_text, "turns": turns},
        ))

        await self.event_bus.emit_async(Event(
            event_type=EventType.RUN_COMPLETE,
            agent_name=agent.name,
            run_id=run_id,
        ))

        return RunResult(
            output=output_text,
            turns=turns,
            token_usage=TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
            ),
            run_id=run_id,
            agent_name=agent.name,
            messages=messages,
        )

    async def _execute_tool(self, name: str, input_data: dict[str, Any]) -> str:
        """Execute a single tool by name and return its string result.

        Args:
            name: The registered tool name.
            input_data: The input dict provided by the model.

        Returns:
            A string representation of the tool's output, or an error
            message if execution fails.
        """
        if name not in self.tool_registry:
            return f"Error: Tool '{name}' not found"
        tools = self.tool_registry.scope([name])
        tool_def = tools[0]
        if tool_def.handler is None:
            return f"Error: Tool '{name}' has no handler"
        try:
            result = await tool_def.handler(input_data)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {e}"
