"""Tests for QualityGate integration inside BrainOrchestrator._execute_worker."""
from __future__ import annotations

import pytest
import pytest_asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, call

from airees.brain.orchestrator import BrainOrchestrator
from airees.events import EventBus, EventType
from airees.quality_gate import QualityGate, GateAction


# ---------------------------------------------------------------------------
# Lightweight fakes for LLM response objects
# ---------------------------------------------------------------------------

@dataclass
class FakeUsage:
    input_tokens: int = 10
    output_tokens: int = 20


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list
    stop_reason: str = "end_turn"
    usage: FakeUsage = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = FakeUsage()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _worker_response(text: str) -> FakeResponse:
    """Build a fake LLM response that ends the tool loop with text output."""
    return FakeResponse(content=[FakeTextBlock(text=text)])


def _score_response(score: float, feedback: str = "") -> FakeResponse:
    """Build a fake Haiku scoring response (JSON text)."""
    import json
    body = json.dumps({"score": score, "feedback": feedback})
    return FakeResponse(content=[FakeTextBlock(text=body)])


def _make_task(task_id: str = "task-1") -> dict:
    return {
        "id": task_id,
        "title": "Write unit tests",
        "description": "Write comprehensive unit tests for the auth module",
        "agent_role": "coder",
        "priority": 2,
        "retry_count": 0,
        "max_retries": 3,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quality_gate_retry_on_low_score():
    """When the quality gate scores output below threshold, the worker retries
    and eventually succeeds on the second attempt."""

    store = AsyncMock()
    router = AsyncMock()
    event_bus = EventBus()

    # Capture emitted events
    emitted: list = []
    event_bus.subscribe_all(lambda e: emitted.append(e))

    gate = QualityGate(name="test", min_score=7.0, max_retries=3, on_failure=GateAction.RETRY)

    # Router call sequence:
    # 1) Worker attempt 1 -> text output (end_turn)
    # 2) Haiku scoring   -> low score (4/10)
    # 3) Worker attempt 2 -> improved text output (end_turn)
    # 4) Haiku scoring   -> high score (8/10)
    router.create_message = AsyncMock(side_effect=[
        _worker_response("Initial rough draft"),
        _score_response(4, "Incomplete coverage, missing edge cases"),
        _worker_response("Improved comprehensive tests with edge cases"),
        _score_response(8, "Good coverage"),
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=router,
        event_bus=event_bus,
        soul_path=MagicMock(),
        quality_gate=gate,
    )

    task = _make_task()
    await orch._execute_worker("goal-1", task)

    # QUALITY_GATE_FAIL should have been emitted for the first low-score attempt
    gate_fail_events = [e for e in emitted if e.event_type == EventType.QUALITY_GATE_FAIL]
    assert len(gate_fail_events) >= 1, "Expected at least one QUALITY_GATE_FAIL event"

    # QUALITY_GATE_PASS should have been emitted for the second successful attempt
    gate_pass_events = [e for e in emitted if e.event_type == EventType.QUALITY_GATE_PASS]
    assert len(gate_pass_events) == 1, "Expected exactly one QUALITY_GATE_PASS event"

    # The task should have been completed (not flagged for human)
    store.complete_task.assert_called_once()
    store.flag_task_human.assert_not_called()


@pytest.mark.asyncio
async def test_quality_gate_escalate_after_max_retries():
    """When the quality gate fails repeatedly beyond max_retries, the worker
    escalates to human attention."""

    store = AsyncMock()
    router = AsyncMock()
    event_bus = EventBus()

    emitted: list = []
    event_bus.subscribe_all(lambda e: emitted.append(e))

    gate = QualityGate(
        name="strict", min_score=7.0, max_retries=3, on_failure=GateAction.FLAG_HUMAN,
    )

    # Router call sequence: 3 attempts, each scored low
    # attempt 1: worker output + score 3
    # attempt 2: worker output + score 3
    # attempt 3: worker output + score 3
    router.create_message = AsyncMock(side_effect=[
        _worker_response("Bad output v1"),
        _score_response(3, "Very poor quality"),
        _worker_response("Bad output v2"),
        _score_response(3, "Still very poor"),
        _worker_response("Bad output v3"),
        _score_response(3, "No improvement"),
    ])

    orch = BrainOrchestrator(
        store=store,
        brain_model="anthropic/claude-opus-4-6",
        router=router,
        event_bus=event_bus,
        soul_path=MagicMock(),
        quality_gate=gate,
    )

    task = _make_task()
    await orch._execute_worker("goal-1", task)

    # NEEDS_ATTENTION should have been emitted
    attention_events = [e for e in emitted if e.event_type == EventType.NEEDS_ATTENTION]
    assert len(attention_events) == 1, "Expected exactly one NEEDS_ATTENTION event"

    # flag_task_human should have been called
    store.flag_task_human.assert_called_once()

    # complete_task should NOT have been called
    store.complete_task.assert_not_called()
