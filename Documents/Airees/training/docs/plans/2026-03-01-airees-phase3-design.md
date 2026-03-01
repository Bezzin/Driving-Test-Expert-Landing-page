# Phase 3: Factory Integration Design

> Wire standalone factory primitives (QualityGate, ProjectState, ContextBudget, Scheduler, DecisionDocument, FeedbackLoop, validation) into the live BrainOrchestrator execution pipeline with full crash recovery and background daemon scheduling.

## Status

- **Created:** 2026-03-01
- **Approach:** Orchestrator-Centric Integration (direct wiring, no new abstractions)

## Context

Phase 1 built the Brain/Coordinator/Worker architecture. Phase 2 added worker tools, parallel execution, and resilience. The "factory improvements" plan created standalone primitives (QualityGate, ProjectState, ContextBudget, Scheduler, DecisionDocument, FeedbackLoop, validate_pipeline) — all implemented with tests but **not wired into the live execution flow**.

Phase 3 integrates these primitives into the orchestration pipeline so they are actually used during goal execution.

### Current State

| Primitive | File | Status |
|-----------|------|--------|
| QualityGate | quality_gate.py | Standalone, tested |
| ProjectState | state.py | Standalone, tested |
| ContextBudget | context_budget.py | Partially wired (Agent dataclass + Runner) |
| Scheduler | scheduler.py | Standalone, tested |
| DecisionDocument | decision_doc.py | Standalone, tested |
| FeedbackLoop | feedback.py | Standalone, tested |
| validate_pipeline | validation.py | Standalone, tested |

## Architecture

### Integration Map

```
submit_goal()
  |-- validate_pipeline() on planned agents (cross-model check)
  |-- ProjectState created and saved to disk

execute_goal()
  |-- classify_intent()
  |-- plan()
  |   |-- ProjectState -> "planning" phase, persisted
  |   |-- DecisionDocument.add_entry(action="create_plan", ...)
  |
  |-- _execute_wave()
  |   |-- ProjectState -> "executing" phase, persisted
  |   |-- For each worker:
  |       |-- ContextBudget tracked per worker
  |       |-- Worker produces output
  |       |-- QualityGate.evaluate(score) on output
  |       |   |-- PASS -> complete_task()
  |       |   |-- RETRY -> re-execute worker with feedback appended
  |       |   |-- ESCALATE -> flag_human, emit NEEDS_ATTENTION event
  |       |-- DecisionDocument.add_entry(action="task_complete"|"task_retry"|"escalate")
  |
  |-- _evaluate()
  |   |-- ProjectState -> "evaluating" phase, persisted
  |   |-- DecisionDocument.add_entry(action="evaluate", reasoning=...)
  |   |-- FeedbackLoop.record(outcome) after each iteration
  |
  |-- Completion
      |-- ProjectState -> all phases COMPLETED, persisted
      |-- FeedbackLoop.record(final_outcome)
      |-- DecisionDocument.to_markdown() saved to data/decisions/

Crash Recovery:
  |-- On startup, GoalDaemon loads ProjectState files from data/states/
  |-- Any state with current_phase != None and status != COMPLETED -> resume
  |-- Resume calls execute_goal() which picks up from stored DB task statuses
```

## Quality Gate Integration

### Scoring Strategy

After each worker produces output, a lightweight Haiku call scores it 1-10:

```python
async def _score_output(self, task: dict, output: str) -> tuple[float, str]:
    """Rate worker output using Haiku for cost efficiency."""
    model = ModelConfig(model_id="claude-haiku-4-5-20251001")
    response = await self.router.create_message(
        model=model,
        system="Rate this output 1-10. Respond with JSON: {\"score\": N, \"feedback\": \"...\"}",
        messages=[{
            "role": "user",
            "content": f"Task: {task['title']}\n\nOutput:\n{output}"
        }],
    )
    # Parse score and feedback from response
```

### Retry with Feedback

When quality gate fails but retries remain, the worker re-runs with feedback appended:

```python
gate_result = self.quality_gate.evaluate(score)
if not gate_result.passed and self.quality_gate.should_retry(attempt):
    # Append feedback to messages, re-run worker loop
elif self.quality_gate.should_escalate(attempt):
    # Flag task as needs_human, emit NEEDS_ATTENTION event
```

### Defaults

- `min_score=7.0` (out of 10)
- `max_retries=3`
- `on_failure=GateAction.RETRY` (escalate to human after max retries)

## ProjectState & Crash Recovery

### Persistence Points

State persists to `data/states/{goal_id}.json` at every phase transition:

| Event | Phase | Action |
|-------|-------|--------|
| Goal submitted | planning | Create initial state |
| Plan created | executing | Tasks stored in DB |
| Wave complete | executing | State refreshed |
| Evaluation | evaluating | Results captured |
| Iteration | executing | Iteration count bumped |
| Complete | completed | Final state |
| Failure | failed/needs_human | Error info + retry count |

### Phases

```python
phases = ["planning", "executing", "evaluating", "completing"]
```

The executing/evaluating cycle repeats per iteration.

### Resume Logic

1. Scan `data/states/*.json` for non-complete states
2. Load state, check `current_phase`
3. `planning` -> re-plan (task DB may be empty)
4. `executing` -> tasks exist, re-execute from `_execute_wave()`
5. `evaluating` -> results exist, re-evaluate
6. `needs_human` -> skip, emit NEEDS_ATTENTION

### Crash Mid-Worker

Workers with status IN_PROGRESS but no result get reset to PENDING on resume. Worker execution is idempotent.

## DecisionDocument Integration

- `BrainOrchestrator` holds one `DecisionDocument` per goal execution
- Every significant action adds an entry: plan creation, task completion, quality gate result, evaluation, adaptation
- On goal completion: `doc.to_markdown()` saves to `data/decisions/{goal_id}.md`
- SQLite `log_decision()` calls remain (dual-write: DB for queries, markdown for humans)

## FeedbackLoop Integration

- `BrainOrchestrator` holds a `FeedbackLoop` instance
- After goal completion/failure: `FeedbackEntry` recorded with agent roles, scores, iterations, outcome
- `feedback.to_memory_content()` appends to `data/memory/feedback.md`
- Available to Brain in future goals for pattern recognition

## Validation Integration

- `validate_pipeline()` runs in `plan()` after tasks are created
- Checks if builder/reviewer pairs use the same model
- Warnings emitted as `EventType.VALIDATION_WARNING` events (advisory, don't block)
- Logged in DecisionDocument

## GoalDaemon (Background Scheduler)

```python
@dataclass
class GoalDaemon:
    orchestrator: BrainOrchestrator
    scheduler: Scheduler
    poll_interval: int = 30        # seconds
    state_dir: Path = Path("data/states")

    async def run_forever(self):
        while True:
            pending = await self._find_pending_goals()
            interrupted = self._find_interrupted_goals()
            for goal_id in [*interrupted, *pending]:
                if self.scheduler.has_capacity:
                    await self.scheduler.submit(
                        self.orchestrator.execute_goal(goal_id)
                    )
            await asyncio.sleep(self.poll_interval)

    async def _find_pending_goals(self) -> list[str]:
        """Query GoalStore for goals with status PENDING."""
        ...

    def _find_interrupted_goals(self) -> list[str]:
        """Scan state_dir for non-complete ProjectState files."""
        ...
```

- Polls every 30s (configurable) for pending and interrupted goals
- Respects `Scheduler.max_concurrent` capacity
- Interrupted goals (crash recovery) take priority over new pending goals
- Started via CLI: `airees daemon start`

## New Event Types

```python
QUALITY_GATE_PASS = "quality_gate_pass"
QUALITY_GATE_FAIL = "quality_gate_fail"
NEEDS_ATTENTION = "needs_attention"
STATE_PERSISTED = "state_persisted"
VALIDATION_WARNING = "validation_warning"
GOAL_RESUMED = "goal_resumed"
FEEDBACK_RECORDED = "feedback_recorded"
```

## Files Modified

| File | Changes |
|------|---------|
| `brain/orchestrator.py` | Accept new primitives, wire into lifecycle |
| `coordinator/executor.py` | Quality gate evaluation after worker output |
| `scheduler.py` | Background polling capability |
| `events.py` | New event types |
| `cli/main.py` | `airees daemon` command |
| `__init__.py` | Export updates |

## Files Created

| File | Purpose |
|------|---------|
| `goal_daemon.py` | Background daemon wrapping Scheduler + Orchestrator |

## Test Files

| File | Coverage |
|------|----------|
| `tests/test_orchestrator_integration.py` | Full lifecycle with all primitives |
| `tests/test_goal_daemon.py` | Daemon polling and resume |
| `tests/test_quality_gate_integration.py` | Gate wired into worker execution |

## Data Directories

```
data/
  states/          # ProjectState JSON files (one per goal)
  decisions/       # DecisionDocument markdown exports
  memory/
    feedback.md    # FeedbackLoop memory content
```

## Design Decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Integration approach | Orchestrator-centric | Direct, testable, minimal abstractions |
| Quality scoring | Haiku per-task | Cost efficient, fast, good enough for scoring |
| State persistence | JSON files | Human-readable, simple, crash-safe with atomic writes |
| Decision logging | Dual-write (SQLite + markdown) | DB for queries, markdown for human review |
| Daemon polling | 30s interval | Responsive enough without excessive load |
| Resume strategy | Reset IN_PROGRESS workers to PENDING | Idempotent re-execution |
| Interrupted goal priority | Before new pending goals | Finish what was started |
