"""Brain Orchestrator — the main loop tying Brain + Coordinator + Workers."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from airees.brain.prompt import build_brain_prompt
from airees.brain.state_machine import BrainState, BrainStateMachine
from airees.brain.tools import get_brain_tools
from airees.coordinator.executor import Coordinator
from airees.coordinator.worker_builder import build_worker_prompt, select_model
from airees.db.schema import GoalStore, GoalStatus
from airees.events import Event, EventBus, EventType
from airees.router.types import ModelConfig
from airees.soul import load_soul
from airees.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class BrainOrchestrator:
    """Top-level orchestrator implementing the plan-execute-evaluate loop.

    Receives a goal, activates the Brain for planning, hands tasks to the
    Coordinator for execution, then activates the Brain again for evaluation.
    Iterates until satisfied or max iterations reached.
    """

    store: GoalStore
    brain_model: str
    router: Any  # ModelRouter
    event_bus: EventBus
    soul_path: Path = Path("data/SOUL.md")
    state_machine: BrainStateMachine = field(default_factory=BrainStateMachine)

    async def submit_goal(self, description: str) -> str:
        """Create a new goal and emit a RUN_START event."""
        goal_id = await self.store.create_goal(description=description)
        await self.event_bus.emit_async(Event(
            event_type=EventType.RUN_START,
            agent_name="airees-brain",
            data={"goal_id": goal_id, "description": description},
        ))
        return goal_id

    async def plan(self, goal_id: str) -> list[dict]:
        """Invoke the Brain to create a task plan for the given goal.

        Transitions: IDLE -> PLANNING -> DELEGATING.
        Calls the LLM once and processes any create_plan tool use blocks.
        """
        self.state_machine.transition(BrainState.PLANNING)
        await self.store.update_goal_status(goal_id, GoalStatus.PLANNING)

        goal = await self.store.get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")
        soul = load_soul(self.soul_path)
        prompt = build_brain_prompt(soul=soul, goal=goal["description"])

        brain_tools = get_brain_tools()
        registry = ToolRegistry()
        for t in brain_tools:
            registry.register(t)

        tools_formatted = registry.to_anthropic_format([t.name for t in brain_tools])
        model = ModelConfig(model_id=self.brain_model)

        response = await self.router.create_message(
            model=model,
            system=prompt,
            messages=[{"role": "user", "content": f"Plan this goal: {goal['description']}"}],
            tools=tools_formatted,
        )

        tasks_created = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "create_plan":
                plan_data = block.input
                task_id_map: dict[int, str] = {}

                for i, task_spec in enumerate(plan_data.get("tasks", [])):
                    dep_indices = task_spec.get("dependencies", [])
                    dep_ids = [task_id_map[d] for d in dep_indices if d in task_id_map]

                    task_id = await self.store.create_task(
                        goal_id=goal_id,
                        title=task_spec["title"],
                        description=task_spec.get("description", ""),
                        agent_role=task_spec.get("agent_role", "coder"),
                        dependencies=dep_ids,
                        priority=task_spec.get("priority", 2),
                    )
                    task_id_map[i] = task_id
                    tasks_created.append({**{"id": task_id}, **task_spec})

                await self.store.log_decision(
                    goal_id=goal_id,
                    iteration=0,
                    action="create_plan",
                    reasoning=plan_data.get("strategy", "Initial plan created"),
                )

        self.state_machine.transition(BrainState.DELEGATING)
        await self.store.update_goal_status(goal_id, GoalStatus.EXECUTING)
        return tasks_created

    async def execute_goal(self, goal_id: str) -> str:
        """Full autonomous loop: plan -> execute -> evaluate -> iterate."""
        await self.plan(goal_id)

        coordinator = Coordinator(store=self.store, runner=self.router)

        self.state_machine.transition(BrainState.WAITING)
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            while True:
                ready = await coordinator.get_next_tasks(goal_id)
                if not ready:
                    break

                for task in ready:
                    await self._execute_worker(goal_id, task)

                if await coordinator.is_goal_complete(goal_id):
                    break
                if await coordinator.has_failures(goal_id):
                    break

            self.state_machine.transition(BrainState.EVALUATING)
            report = await coordinator.build_report(goal_id)
            action = await self._evaluate(goal_id, report, iteration)

            if action == "satisfied":
                self.state_machine.transition(BrainState.COMPLETING)
                await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
                self.state_machine.transition(BrainState.IDLE)
                return report

            iteration += 1
            await self.store.increment_iteration(goal_id)
            self.state_machine.transition(BrainState.ADAPTING)
            self.state_machine.transition(BrainState.DELEGATING)
            self.state_machine.transition(BrainState.WAITING)

        await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
        report = await coordinator.build_report(goal_id)
        if self.state_machine.state != BrainState.IDLE:
            self.state_machine.force_reset(reason="max_iterations")
        return report

    async def _execute_worker(self, goal_id: str, task: dict) -> None:
        """Run a single worker sub-agent for the given task."""
        worker_prompt = build_worker_prompt(
            task_title=task["title"],
            task_description=task["description"],
            agent_role=task["agent_role"],
        )
        model_id = select_model(agent_role=task["agent_role"])
        model = ModelConfig(model_id=model_id)

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_START,
            agent_name=f"worker:{task['title']}",
            data={"task_id": task["id"], "model": model_id},
        ))

        try:
            response = await self.router.create_message(
                model=model,
                system=worker_prompt,
                messages=[{"role": "user", "content": task["description"]}],
            )

            output = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    output += block.text

            tokens = response.usage.input_tokens + response.usage.output_tokens
            cost = tokens * 0.000001

            await self.store.complete_task(
                task["id"],
                result=output,
                tokens_used=tokens,
                cost=cost,
            )

            await self.event_bus.emit_async(Event(
                event_type=EventType.AGENT_COMPLETE,
                agent_name=f"worker:{task['title']}",
                data={"task_id": task["id"], "tokens": tokens},
            ))

        except Exception as e:
            logger.exception("Worker failed: %s", task["title"])
            retry = task.get("retry_count", 0) < task.get("max_retries", 3)
            await self.store.fail_task(task["id"], error=str(e), retry=retry)

    async def _evaluate(self, goal_id: str, report: str, iteration: int) -> str:
        """Ask the Brain to evaluate completed work and decide next action."""
        soul = load_soul(self.soul_path)
        goal = await self.store.get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")
        prompt = build_brain_prompt(
            soul=soul,
            goal=goal["description"],
            coordinator_report=report,
            iteration=iteration,
        )

        brain_tools = get_brain_tools()
        registry = ToolRegistry()
        for t in brain_tools:
            registry.register(t)
        tools_formatted = registry.to_anthropic_format([t.name for t in brain_tools])
        model = ModelConfig(model_id=self.brain_model)

        response = await self.router.create_message(
            model=model,
            system=prompt,
            messages=[{"role": "user", "content": "Evaluate the results and decide: satisfied, adapt, or rewrite."}],
            tools=tools_formatted,
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "evaluate_result":
                action = block.input.get("action", "satisfied")
                reasoning = block.input.get("reasoning", "")
                await self.store.log_decision(
                    goal_id=goal_id,
                    iteration=iteration,
                    action=action,
                    reasoning=reasoning,
                )
                return action

        return "satisfied"
