"""Integration tests: Phase 3 factory primitives wired into execution."""
import pytest
from pathlib import Path
from dataclasses import dataclass, field
from unittest.mock import AsyncMock


def test_goal_daemon_importable():
    """GoalDaemon should be importable from airees top-level."""
    from airees import GoalDaemon
    assert GoalDaemon is not None


def test_all_phase3_exports():
    """GoalDaemon should be in __all__."""
    import airees
    assert "GoalDaemon" in airees.__all__


# --- Mock helpers for the integration test ---

@dataclass
class FakeUsage:
    input_tokens: int = 50
    output_tokens: int = 50


@dataclass
class FakeTextBlock:
    type: str = "text"
    text: str = "output"


@dataclass
class FakeToolUseBlock:
    type: str = "tool_use"
    name: str = "create_plan"
    id: str = "tu_1"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {
                "strategy": "Test strategy",
                "tasks": [{
                    "title": "Task 1",
                    "description": "Do task 1",
                    "agent_role": "coder",
                    "priority": 1,
                }],
            }


@dataclass
class FakeEvalBlock:
    type: str = "tool_use"
    name: str = "evaluate_result"
    id: str = "tu_2"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {"action": "satisfied", "reasoning": "Looks good"}


@dataclass
class FakeResponse:
    content: list = None
    stop_reason: str = "end_turn"
    usage: FakeUsage = None

    def __post_init__(self):
        if self.content is None:
            self.content = [FakeTextBlock()]
        if self.usage is None:
            self.usage = FakeUsage()


@pytest.mark.asyncio
async def test_full_goal_lifecycle(tmp_path):
    """Full lifecycle: submit -> plan -> execute -> quality gate -> evaluate -> complete.

    Verifies ProjectState, DecisionDocument, FeedbackLoop, and QualityGate
    are all wired and produce artifacts.
    """
    from airees.brain.orchestrator import BrainOrchestrator
    from airees.db.schema import GoalStore
    from airees.events import EventBus, EventType
    from airees.quality_gate import QualityGate
    from airees.state import load_state

    db_path = tmp_path / "test.db"
    store = GoalStore(db_path=db_path)
    await store.initialize()

    state_dir = tmp_path / "states"
    decisions_dir = tmp_path / "decisions"
    memory_dir = tmp_path / "memory"
    soul_path = tmp_path / "SOUL.md"
    soul_path.write_text("# Airees\nI am an autonomous agent.", encoding="utf-8")

    events_captured = []
    bus = EventBus()
    bus.subscribe_all(lambda e: events_captured.append(e))

    mock_router = AsyncMock()

    # Mock sequence: classify_intent, plan, worker output, quality score, evaluation
    intent_response = FakeResponse(content=[FakeTextBlock(text="BUILD")])
    plan_response = FakeResponse(
        content=[FakeToolUseBlock()],
        stop_reason="tool_use",
    )
    worker_response = FakeResponse(content=[FakeTextBlock(text="Task completed successfully")])
    score_response = FakeResponse(content=[FakeTextBlock(text='{"score": 9, "feedback": "Excellent"}')])
    eval_response = FakeResponse(content=[FakeEvalBlock()], stop_reason="tool_use")

    mock_router.create_message = AsyncMock(side_effect=[
        intent_response,
        plan_response,
        worker_response,
        score_response,
        eval_response,
    ])

    gate = QualityGate(name="test", min_score=7.0, max_retries=3)

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=mock_router,
        event_bus=bus,
        soul_path=soul_path,
        state_dir=state_dir,
        decisions_dir=decisions_dir,
        memory_dir=memory_dir,
        quality_gate=gate,
    )

    goal_id = await orch.submit_goal("Build a test project")
    report = await orch.execute_goal(goal_id)

    # 1. Verify ProjectState completed
    state_file = state_dir / f"{goal_id}.json"
    assert state_file.exists(), "State file should exist"
    loaded = load_state(state_file)
    assert loaded.is_complete, "All phases should be completed"

    # 2. Verify DecisionDocument
    decision_file = decisions_dir / f"{goal_id}.md"
    assert decision_file.exists(), "Decision doc should be written"
    content = decision_file.read_text(encoding="utf-8")
    assert "create_plan" in content

    # 3. Verify FeedbackLoop memory
    feedback_file = memory_dir / "feedback.md"
    assert feedback_file.exists(), "Feedback file should be written"

    # 4. Verify events
    event_types = [e.event_type for e in events_captured]
    assert EventType.RUN_START in event_types
    assert EventType.AGENT_START in event_types
    assert EventType.QUALITY_GATE_PASS in event_types
    assert EventType.AGENT_COMPLETE in event_types
    assert EventType.FEEDBACK_RECORDED in event_types
