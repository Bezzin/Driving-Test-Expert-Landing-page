"""ParallelTeam — fan-out orchestration pattern for Airees.

A :class:`ParallelTeam` dispatches multiple agent tasks concurrently
using ``asyncio.gather``, then aggregates the results into a single
:class:`ParallelResult`.

Usage::

    team = ParallelTeam(
        name="research-team",
        tasks=[
            ParallelTask(agent=researcher, task="Find papers on X"),
            ParallelTask(agent=analyst, task="Analyse market for X"),
        ],
    )
    result = await team.execute(runner=runner)
    for r in result.task_results:
        print(r.agent_name, r.output)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from airees.agent import Agent
from airees.runner import Runner, RunResult, TokenUsage


@dataclass(frozen=True)
class ParallelTask:
    """A single unit of work to be executed concurrently.

    Attributes:
        agent: The agent that will handle this task.
        task: The prompt / instruction for the agent.
    """

    agent: Agent
    task: str


@dataclass(frozen=True)
class ParallelResult:
    """Aggregated outcome of all parallel task executions.

    Attributes:
        task_results: Individual :class:`RunResult` objects, one per task.
        total_turns: Sum of turns across all tasks.
        total_tokens: Aggregated token usage across all tasks.
        run_id: Shared run identifier for the parallel execution.
    """

    task_results: list[RunResult]
    total_turns: int
    total_tokens: TokenUsage
    run_id: str


@dataclass(frozen=True)
class ParallelTeam:
    """Fan-out orchestration: run multiple agent tasks concurrently.

    All tasks are dispatched via ``asyncio.gather`` so they execute
    in parallel (subject to the event loop's concurrency).  Results
    are collected and aggregated into a :class:`ParallelResult`.

    Attributes:
        name: Human-readable identifier for this team.
        tasks: The list of :class:`ParallelTask` items to execute.
    """

    name: str
    tasks: list[ParallelTask]

    async def execute(
        self,
        runner: Runner,
        run_id: str | None = None,
    ) -> ParallelResult:
        """Execute all tasks concurrently and return aggregated results.

        Args:
            runner: The :class:`Runner` instance used to drive each agent.
            run_id: Optional shared run identifier.  A UUID is generated
                when ``None``.

        Returns:
            A :class:`ParallelResult` containing every task's output,
            aggregated turn count, and total token usage.
        """
        run_id = run_id or str(uuid.uuid4())

        async def run_task(task: ParallelTask) -> RunResult:
            return await runner.run(
                agent=task.agent,
                task=task.task,
                run_id=run_id,
            )

        results = await asyncio.gather(*[run_task(t) for t in self.tasks])
        result_list = list(results)

        total_input = sum(r.token_usage.input_tokens for r in result_list)
        total_output = sum(r.token_usage.output_tokens for r in result_list)
        total_turns = sum(r.turns for r in result_list)

        return ParallelResult(
            task_results=result_list,
            total_turns=total_turns,
            total_tokens=TokenUsage(input_tokens=total_input, output_tokens=total_output),
            run_id=run_id,
        )
