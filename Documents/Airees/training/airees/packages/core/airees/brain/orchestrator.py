"""Brain Orchestrator — the main loop tying Brain + Coordinator + Workers."""
from __future__ import annotations

import asyncio
import json as json_module
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from airees.brain.intent import classify_intent
from airees.decision_doc import DecisionDocument, DecisionEntry
from airees.brain.prompt import build_brain_prompt
from airees.brain.state_machine import BrainState, BrainStateMachine
from airees.brain.tools import get_brain_tools
from airees.coordinator.executor import Coordinator
from airees.coordinator.worker_builder import build_worker_prompt, select_model
from airees.db.schema import GoalStore, GoalStatus
from airees.events import Event, EventBus, EventType
from airees.feedback import FeedbackLoop, FeedbackEntry
from airees.quality_gate import QualityGate, GateAction
from airees.router.types import ModelConfig
from airees.soul import load_soul
from airees.state import ProjectState, load_state, save_state
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
    state_dir: Path = Path("data/states")
    decisions_dir: Path = Path("data/decisions")
    memory_dir: Path = Path("data/memory")
    state_machine: BrainStateMachine = field(default_factory=BrainStateMachine)
    tool_provider: Any = None
    quality_gate: QualityGate = field(
        default_factory=lambda: QualityGate(name="default", min_score=7.0, max_retries=3)
    )

    _decision_docs: dict[str, DecisionDocument] = field(
        default_factory=dict, init=False, repr=False
    )
    _feedback: FeedbackLoop = field(default_factory=FeedbackLoop, init=False, repr=False)
    _STATE_PHASES: list[str] = field(
        default_factory=lambda: ["planning", "executing", "evaluating", "completing"],
        init=False,
        repr=False,
    )

    def _state_path(self, goal_id: str) -> Path:
        """Return the file path for a goal's ProjectState JSON."""
        return self.state_dir / f"{goal_id}.json"

    def _persist_phase(self, goal_id: str, phase: str) -> None:
        """Load state, advance through phases up to *phase*, and save.

        If the state file does not yet exist this is a no-op (submit_goal
        creates the initial state separately).
        """
        path = self._state_path(goal_id)
        if not path.exists():
            return
        state = load_state(path)
        while state.current_phase is not None and state.current_phase != phase:
            state = state.advance()
        save_state(state, path)

    def _complete_state(self, goal_id: str) -> None:
        """Advance all remaining phases to COMPLETED and save."""
        path = self._state_path(goal_id)
        if not path.exists():
            return
        state = load_state(path)
        while state.current_phase is not None:
            state = state.advance()
        save_state(state, path)

    def _record_decision(
        self,
        goal_id: str,
        phase: str,
        agent: str,
        decision: str,
        reasoning: str,
        confidence: float = 0.8,
    ) -> None:
        """Append a decision entry to the goal's DecisionDocument."""
        doc = self._decision_docs.get(goal_id)
        if doc is None:
            return
        entry = DecisionEntry(
            phase=phase,
            agent=agent,
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
        )
        self._decision_docs[goal_id] = doc.add_entry(entry)

    def _save_decision_doc(self, goal_id: str) -> None:
        """Write the goal's DecisionDocument to decisions_dir/{goal_id}.md."""
        doc = self._decision_docs.get(goal_id)
        if doc is None:
            return
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        path = self.decisions_dir / f"{goal_id}.md"
        path.write_text(doc.to_markdown(), encoding="utf-8")

    def _record_feedback(
        self,
        goal_id: str,
        outcome: str,
        score: float,
        lesson: str,
    ) -> None:
        """Record a FeedbackEntry, persist to memory_dir/feedback.md, and emit event."""
        entry = FeedbackEntry(
            run_id=goal_id,
            agent_name="airees-brain",
            outcome=outcome,
            score=score,
            lesson=lesson,
        )
        self._feedback = self._feedback.record(entry)

        self.memory_dir.mkdir(parents=True, exist_ok=True)
        feedback_path = self.memory_dir / "feedback.md"
        feedback_path.write_text(
            self._feedback.to_memory_content("airees-brain"),
            encoding="utf-8",
        )

        self.event_bus.emit(Event(
            event_type=EventType.FEEDBACK_RECORDED,
            agent_name="airees-brain",
            data={"goal_id": goal_id, "outcome": outcome, "score": score},
        ))

    async def submit_goal(self, description: str) -> str:
        """Create a new goal and emit a RUN_START event."""
        goal_id = await self.store.create_goal(description=description)

        # Initialize decision document for this goal
        self._decision_docs[goal_id] = DecisionDocument(
            project_id=goal_id, title=description
        )

        # Persist initial ProjectState with current_phase == "planning"
        initial_state = ProjectState(
            project_id=goal_id,
            name=description,
            phases=list(self._STATE_PHASES),
        )
        save_state(initial_state, self._state_path(goal_id))

        await self.event_bus.emit_async(Event(
            event_type=EventType.RUN_START,
            agent_name="airees-brain",
            data={"goal_id": goal_id, "description": description},
        ))
        return goal_id

    async def plan(self, goal_id: str, intent: str | None = None) -> list[dict]:
        """Invoke the Brain to create a task plan for the given goal.

        Transitions: IDLE -> PLANNING -> DELEGATING.
        Calls the LLM once and processes any create_plan tool use blocks.
        """
        self._persist_phase(goal_id, "planning")
        self.state_machine.transition(BrainState.PLANNING)
        await self.store.update_goal_status(goal_id, GoalStatus.PLANNING)

        goal = await self.store.get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")
        soul = load_soul(self.soul_path)
        prompt = build_brain_prompt(soul=soul, goal=goal["description"], intent=intent)

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
                self._record_decision(
                    goal_id=goal_id,
                    phase="planning",
                    agent="brain",
                    decision="create_plan",
                    reasoning=plan_data.get("strategy", "Initial plan created"),
                )

        self.state_machine.transition(BrainState.DELEGATING)
        await self.store.update_goal_status(goal_id, GoalStatus.EXECUTING)
        return tasks_created

    async def execute_goal(self, goal_id: str) -> str:
        """Full autonomous loop: classify intent -> plan -> execute -> evaluate -> iterate."""
        goal = await self.store.get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")
        intent = await classify_intent(self.router, goal["description"])
        await self.plan(goal_id, intent=intent.value)

        coordinator = Coordinator(store=self.store, runner=self.router)

        self.state_machine.transition(BrainState.WAITING)
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            self._persist_phase(goal_id, "executing")
            while True:
                ready = await coordinator.get_next_tasks(goal_id)
                if not ready:
                    break
                await self._execute_wave(goal_id)
                if await coordinator.is_goal_complete(goal_id):
                    break
                if await coordinator.has_failures(goal_id):
                    break

            self._persist_phase(goal_id, "evaluating")
            self.state_machine.transition(BrainState.EVALUATING)
            report = await coordinator.build_report(goal_id)
            action = await self._evaluate(goal_id, report, iteration)

            if action == "satisfied":
                self._complete_state(goal_id)
                self._save_decision_doc(goal_id)
                self._record_feedback(goal_id, "success", 8.0, "Goal completed successfully")
                self.state_machine.transition(BrainState.COMPLETING)
                await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
                self.state_machine.transition(BrainState.IDLE)
                return report

            iteration += 1
            await self.store.increment_iteration(goal_id)
            self.state_machine.transition(BrainState.ADAPTING)
            self.state_machine.transition(BrainState.DELEGATING)
            self.state_machine.transition(BrainState.WAITING)

        self._complete_state(goal_id)
        self._save_decision_doc(goal_id)
        self._record_feedback(goal_id, "partial", 5.0, "Goal completed after max iterations")
        await self.store.update_goal_status(goal_id, GoalStatus.COMPLETED)
        report = await coordinator.build_report(goal_id)
        if self.state_machine.state != BrainState.IDLE:
            self.state_machine.force_reset(reason="max_iterations")
        return report

    async def _execute_wave(self, goal_id: str) -> None:
        """Execute all ready tasks in parallel."""
        coordinator = Coordinator(store=self.store, runner=self.router)
        ready = await coordinator.get_next_tasks(goal_id)
        if not ready:
            return

        # Sort by priority (lower = higher priority)
        ready.sort(key=lambda t: t.get("priority", 2))

        # Execute all ready tasks concurrently
        tasks = [self._execute_worker(goal_id, task) for task in ready]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _score_output(self, task: dict, output: str) -> tuple[float, str]:
        """Rate worker output using Haiku for cost efficiency."""
        model = ModelConfig(model_id="claude-haiku-4-5-20251001")
        response = await self.router.create_message(
            model=model,
            system=(
                "You are a quality scorer. Rate the output 1-10 for completeness, "
                "accuracy, and quality relative to the task. "
                'Respond with ONLY valid JSON: {"score": N, "feedback": "..."}'
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Task: {task['title']}\n"
                    f"Description: {task['description']}\n\n"
                    f"Output:\n{output}"
                ),
            }],
        )
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text
        try:
            parsed = json_module.loads(text)
            return float(parsed.get("score", 5)), parsed.get("feedback", "")
        except (json_module.JSONDecodeError, ValueError):
            return 5.0, "Could not parse score"

    async def _execute_worker(self, goal_id: str, task: dict) -> None:
        """Run a single worker sub-agent with an agentic tool_use loop.

        After each attempt the output is scored by a lightweight Haiku call.
        If the score is below the quality gate threshold the worker retries
        with the feedback appended.  After max retries, escalate to human.
        """
        from airees.coordinator.worker_builder import get_tools_for_role

        role_tool_names = get_tools_for_role(task["agent_role"])
        worker_prompt = build_worker_prompt(
            task_title=task["title"],
            task_description=task["description"],
            agent_role=task["agent_role"],
            available_tools=role_tool_names if role_tool_names else None,
        )
        model_id = select_model(agent_role=task["agent_role"])
        model = ModelConfig(model_id=model_id)

        # Build tool definitions for the LLM
        tools_formatted = None
        if self.tool_provider and role_tool_names:
            tool_defs = self.tool_provider.get_tools()
            available = [t for t in tool_defs if t.name in role_tool_names]
            if available:
                registry = ToolRegistry()
                for t in available:
                    registry.register(t)
                tools_formatted = registry.to_anthropic_format(
                    [t.name for t in available]
                )

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_START,
            agent_name=f"worker:{task['title']}",
            data={"task_id": task["id"], "model": model_id},
        ))

        try:
            total_tokens = 0
            output = ""
            gate = self.quality_gate

            for attempt in range(gate.max_retries):
                # Reset output for each quality-gate attempt
                output = ""
                messages = [{"role": "user", "content": task["description"]}]

                # If this is a retry, append the scoring feedback
                if attempt > 0:
                    messages[0] = {
                        "role": "user",
                        "content": (
                            f"{task['description']}\n\n"
                            f"PREVIOUS ATTEMPT FEEDBACK (attempt {attempt}): "
                            f"{gate_feedback}\n"
                            "Please improve your output based on this feedback."
                        ),
                    }

                # --- Agentic tool_use loop (unchanged logic) ---
                max_tool_rounds = 10
                for _ in range(max_tool_rounds):
                    response = await self.router.create_message(
                        model=model,
                        system=worker_prompt,
                        messages=messages,
                        tools=tools_formatted,
                    )

                    total_tokens += (
                        response.usage.input_tokens + response.usage.output_tokens
                    )

                    if response.stop_reason == "end_turn" or response.stop_reason != "tool_use":
                        for block in response.content:
                            if getattr(block, "type", None) == "text":
                                output += block.text
                        break

                    tool_results = []
                    for block in response.content:
                        if getattr(block, "type", None) == "tool_use" and self.tool_provider:
                            result = await self.tool_provider.execute(
                                block.name, block.input
                            )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

                # --- Quality gate scoring ---
                score, gate_feedback = await self._score_output(task, output)
                gate_result = gate.evaluate(score, gate_feedback)

                if gate_result.passed:
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.QUALITY_GATE_PASS,
                        agent_name=f"worker:{task['title']}",
                        data={
                            "task_id": task["id"],
                            "score": score,
                            "attempt": attempt + 1,
                        },
                    ))
                    break

                # Gate failed
                await self.event_bus.emit_async(Event(
                    event_type=EventType.QUALITY_GATE_FAIL,
                    agent_name=f"worker:{task['title']}",
                    data={
                        "task_id": task["id"],
                        "score": score,
                        "feedback": gate_feedback,
                        "attempt": attempt + 1,
                    },
                ))

                if gate.should_escalate(attempt + 1):
                    await self.store.flag_task_human(
                        task["id"],
                        reason=(
                            f"Quality gate failed after {attempt + 1} attempts. "
                            f"Last score: {score}. Feedback: {gate_feedback}"
                        ),
                    )
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.NEEDS_ATTENTION,
                        agent_name=f"worker:{task['title']}",
                        data={
                            "task_id": task["id"],
                            "score": score,
                            "attempts": attempt + 1,
                        },
                    ))
                    return

                if not gate.should_retry(attempt + 1):
                    break

            # After the loop: complete the task with the final output
            cost = total_tokens * 0.000001
            await self.store.complete_task(
                task["id"],
                result=output,
                tokens_used=total_tokens,
                cost=cost,
            )

            await self.event_bus.emit_async(Event(
                event_type=EventType.AGENT_COMPLETE,
                agent_name=f"worker:{task['title']}",
                data={"task_id": task["id"], "tokens": total_tokens},
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
                self._record_decision(
                    goal_id=goal_id,
                    phase="evaluating",
                    agent="brain",
                    decision=action,
                    reasoning=reasoning,
                )
                return action

        return "satisfied"
