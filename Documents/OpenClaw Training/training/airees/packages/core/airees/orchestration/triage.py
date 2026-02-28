"""TriageRouter — intent-based routing to specialised agents.

The TriageRouter uses a lightweight LLM call to classify an incoming
task and dispatch it to the most appropriate agent.  Each :class:`Route`
pairs an intent description with an :class:`Agent`; the router builds a
prompt from these descriptions, asks the ``router_model`` to pick one,
then delegates execution to the selected agent via the :class:`Runner`.

Usage::

    triage = TriageRouter(
        name="support-router",
        router_model=ModelConfig(model_id="claude-haiku-4-5"),
        routes=[
            Route(intent="needs research", agent=researcher_agent),
            Route(intent="needs coding", agent=coder_agent),
        ],
    )
    result = await triage.execute(runner=runner, task="Find info on AI safety")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.runner import Runner, RunResult, TokenUsage


@dataclass(frozen=True)
class Route:
    """A single routing option pairing an intent description with an agent.

    Attributes:
        intent: Human-readable description of when this route should be
            selected (e.g. ``"needs research"``).
        agent: The :class:`Agent` to delegate to when this route matches.
    """

    intent: str
    agent: Agent


@dataclass(frozen=True)
class TriageResult:
    """Immutable outcome of a :meth:`TriageRouter.execute` call.

    Attributes:
        output: The final text output from the selected agent.
        selected_agent: Name of the agent that was chosen by the router.
        run_result: The full :class:`RunResult` from the delegated run.
        run_id: Unique identifier for this triage execution.
    """

    output: str
    selected_agent: str
    run_result: RunResult
    run_id: str


@dataclass(frozen=True)
class TriageRouter:
    """Intent-based router that classifies a task and delegates to the
    best-matched agent.

    The router makes a lightweight LLM call using ``router_model`` to
    determine which agent should handle the task, then runs that agent
    through the provided :class:`Runner`.

    Attributes:
        name: Descriptive name for this router instance.
        router_model: The :class:`ModelConfig` used for the classification
            call (typically a fast, cheap model like Haiku).
        routes: Ordered list of :class:`Route` options.  The first route
            is used as a fallback if the model returns an unrecognised
            agent name.
    """

    name: str
    router_model: ModelConfig
    routes: list[Route]

    async def execute(
        self,
        runner: Runner,
        task: str,
        run_id: str | None = None,
    ) -> TriageResult:
        """Classify *task* and delegate to the appropriate agent.

        Args:
            runner: The :class:`Runner` instance used for both the
                classification call and the agent execution.
            task: The user task / prompt to route and execute.
            run_id: Optional run identifier.  A UUID is generated when
                ``None``.

        Returns:
            A :class:`TriageResult` containing the selected agent name,
            output text, and full run result.
        """
        run_id = run_id or str(uuid.uuid4())

        agent_descriptions = "\n".join(
            f"- {route.agent.name}: {route.intent}"
            for route in self.routes
        )
        agent_names = [route.agent.name for route in self.routes]

        routing_prompt = (
            f"Given the following task, select the most appropriate agent.\n\n"
            f"Available agents:\n{agent_descriptions}\n\n"
            f"Task: {task}\n\n"
            f"Respond with ONLY the agent name, one of: {', '.join(agent_names)}"
        )

        response = await runner.router.create_message(
            model=self.router_model,
            system="You are a routing agent. Select the best agent for the task. Respond with only the agent name.",
            messages=[{"role": "user", "content": routing_prompt}],
        )

        selected_name = ""
        for block in response.content:
            if block.type == "text":
                selected_name = block.text.strip().lower()
                break

        agent_map = {route.agent.name.lower(): route.agent for route in self.routes}
        selected_agent = agent_map.get(selected_name)

        if selected_agent is None:
            selected_agent = self.routes[0].agent
            selected_name = selected_agent.name

        result = await runner.run(
            agent=selected_agent,
            task=task,
            run_id=run_id,
        )

        return TriageResult(
            output=result.output,
            selected_agent=selected_name,
            run_result=result,
            run_id=run_id,
        )
