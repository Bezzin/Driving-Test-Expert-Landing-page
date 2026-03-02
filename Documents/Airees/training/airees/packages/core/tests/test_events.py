# tests/test_events.py
import pytest
from airees.events import EventBus, Event, EventType


def test_event_creation():
    event = Event(
        event_type=EventType.AGENT_START,
        agent_name="researcher",
        data={"task": "find info"},
    )
    assert event.event_type == EventType.AGENT_START
    assert event.agent_name == "researcher"


def test_subscribe_and_emit():
    bus = EventBus()
    received = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.AGENT_START, handler)
    bus.emit(Event(event_type=EventType.AGENT_START, agent_name="test"))

    assert len(received) == 1
    assert received[0].agent_name == "test"


def test_subscribe_wildcard():
    bus = EventBus()
    received = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe_all(handler)
    bus.emit(Event(event_type=EventType.AGENT_START, agent_name="a"))
    bus.emit(Event(event_type=EventType.AGENT_COMPLETE, agent_name="a"))

    assert len(received) == 2


@pytest.mark.asyncio
async def test_async_handler():
    bus = EventBus()
    received = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.TOOL_CALL, handler)
    await bus.emit_async(Event(event_type=EventType.TOOL_CALL, agent_name="test"))

    assert len(received) == 1


def test_event_has_timestamp():
    event = Event(event_type=EventType.RUN_START)
    assert event.timestamp is not None


def test_multiple_handlers_same_event():
    bus = EventBus()
    results = []

    bus.subscribe(EventType.AGENT_START, lambda e: results.append("a"))
    bus.subscribe(EventType.AGENT_START, lambda e: results.append("b"))
    bus.emit(Event(event_type=EventType.AGENT_START, agent_name="test"))

    assert len(results) == 2


def test_quality_gate_pass_event_type():
    assert EventType.QUALITY_GATE_PASS.value == "quality_gate.pass"

def test_quality_gate_fail_event_type():
    assert EventType.QUALITY_GATE_FAIL.value == "quality_gate.fail"

def test_needs_attention_event_type():
    assert EventType.NEEDS_ATTENTION.value == "goal.needs_attention"

def test_state_persisted_event_type():
    assert EventType.STATE_PERSISTED.value == "state.persisted"

def test_validation_warning_event_type():
    assert EventType.VALIDATION_WARNING.value == "validation.warning"

def test_goal_resumed_event_type():
    assert EventType.GOAL_RESUMED.value == "goal.resumed"

def test_feedback_recorded_event_type():
    assert EventType.FEEDBACK_RECORDED.value == "feedback.recorded"


def test_corpus_search_event_type():
    assert EventType.CORPUS_SEARCH.value == "corpus.search"

def test_skill_matched_event_type():
    assert EventType.SKILL_MATCHED.value == "skill.matched"

def test_skill_created_event_type():
    assert EventType.SKILL_CREATED.value == "skill.created"

def test_skill_updated_event_type():
    assert EventType.SKILL_UPDATED.value == "skill.updated"

def test_context_compressed_event_type():
    assert EventType.CONTEXT_COMPRESSED.value == "context.compressed"

def test_soul_updated_event_type():
    assert EventType.SOUL_UPDATED.value == "soul.updated"

def test_reflection_triggered_event_type():
    assert EventType.REFLECTION_TRIGGERED.value == "reflection.triggered"
