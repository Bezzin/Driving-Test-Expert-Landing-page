"""Pipeline orchestration pattern for sequential multi-agent execution.

A :class:`Pipeline` chains multiple :class:`PipelineStep` instances, each
backed by an :class:`~airees.agent.Agent`.  Steps run sequentially and each
step's output is made available to the next via the ``{{previous_output}}``
template variable.

Usage::

    pipeline = Pipeline(
        name="research-write",
        steps=[
            PipelineStep(agent=researcher, task_template="Research {{topic}}"),
            PipelineStep(agent=writer, task_template="Write about: {{previous_output}}"),
        ],
    )
    result = await pipeline.execute(runner=runner, variables={"topic": "AI"})
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from airees.agent import Agent
from airees.quality_gate import QualityGate
from airees.runner import Runner, RunResult, TokenUsage


@dataclass(frozen=True)
class PipelineStep:
    """A single step within a pipeline.

    Attributes:
        agent: The agent that executes this step.
        task_template: A template string that may contain ``{{variable}}``
            placeholders.  The special variable ``{{previous_output}}`` is
            automatically populated with the preceding step's output.
    """

    agent: Agent
    task_template: str
    quality_gate: QualityGate | None = None


@dataclass(frozen=True)
class PipelineResult:
    """Immutable outcome of a full pipeline execution.

    Attributes:
        output: The final text output from the last step.
        total_turns: Aggregate number of LLM round-trips across all steps.
        total_tokens: Aggregate token consumption across all steps.
        step_results: Ordered list of per-step :class:`RunResult` objects.
        run_id: Unique identifier shared by every step in this pipeline run.
    """

    output: str
    total_turns: int
    total_tokens: TokenUsage
    step_results: list[RunResult]
    run_id: str


@dataclass(frozen=True)
class Pipeline:
    """Sequential multi-agent pipeline.

    Each step is executed in order.  The output of step *N* is injected
    into step *N+1* as the ``{{previous_output}}`` template variable.

    Attributes:
        name: Human-readable identifier for the pipeline.
        steps: Ordered list of :class:`PipelineStep` instances.
    """

    name: str
    steps: list[PipelineStep]

    async def execute(
        self,
        runner: Runner,
        variables: dict[str, str] | None = None,
        run_id: str | None = None,
    ) -> PipelineResult:
        """Run every step sequentially, threading outputs forward.

        Args:
            runner: The :class:`Runner` used to execute each agent.
            variables: Initial template variables (e.g. ``{"topic": "AI"}``).
            run_id: Optional shared run identifier.  A UUID is generated
                when ``None``.

        Returns:
            A :class:`PipelineResult` containing the final output,
            aggregated metrics, and per-step results.
        """
        import uuid

        run_id = run_id or str(uuid.uuid4())
        variables = dict(variables or {})
        step_results: list[RunResult] = []
        total_input = 0
        total_output = 0
        total_turns = 0
        gate_attempts: dict[int, int] = {}

        i = 0
        while i < len(self.steps):
            step = self.steps[i]
            task = self._interpolate(step.task_template, variables)
            result = await runner.run(
                agent=step.agent,
                task=task,
                run_id=run_id,
            )
            step_results.append(result)
            total_input += result.token_usage.input_tokens
            total_output += result.token_usage.output_tokens
            total_turns += result.turns
            variables["previous_output"] = result.output

            if step.quality_gate is not None:
                scores = re.findall(r"\d+\.?\d*", result.output)
                score = float(scores[-1]) if scores else 0.0
                gate_result = step.quality_gate.evaluate(score, result.output)
                if not gate_result.passed:
                    attempt = gate_attempts.get(i, 0) + 1
                    gate_attempts[i] = attempt
                    if step.quality_gate.should_retry(attempt):
                        i = max(0, i - 1)
                        continue

            i += 1

        final_output = step_results[-1].output if step_results else ""

        return PipelineResult(
            output=final_output,
            total_turns=total_turns,
            total_tokens=TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
            ),
            step_results=step_results,
            run_id=run_id,
        )

    def _interpolate(self, template: str, variables: dict[str, str]) -> str:
        """Replace ``{{key}}`` placeholders with values from *variables*.

        Unknown placeholders are left unchanged so that downstream steps
        can resolve them later.
        """

        def replace(match: re.Match) -> str:
            key = match.group(1)
            return variables.get(key, match.group(0))

        return re.sub(r"\{\{(\w+)\}\}", replace, template)
