"""EventBus — observability backbone for Airees.

Every agent action (start, tool call, handoff, complete) emits an Event
through the EventBus.  Consumers include:

* WebSocket streaming (real-time UI)
* SQLite logging (persistence)
* Custom user hooks

Both synchronous and asynchronous handlers are supported.  Use ``emit``
for sync-only pipelines and ``emit_async`` when any handler is a coroutine.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class EventType(Enum):
    """Lifecycle events emitted by agents and the runtime."""

    AGENT_START = "agent.start"
    AGENT_COMPLETE = "agent.complete"
    AGENT_HANDOFF = "agent.handoff"
    TOOL_CALL = "agent.tool_call"
    TOOL_RESULT = "agent.tool_result"
    RUN_START = "run.start"
    RUN_COMPLETE = "run.complete"
    RUN_ERROR = "run.error"
    CONTEXT_WARNING = "agent.context_warning"
    QUALITY_GATE_PASS = "quality_gate.pass"
    QUALITY_GATE_FAIL = "quality_gate.fail"
    NEEDS_ATTENTION = "goal.needs_attention"
    STATE_PERSISTED = "state.persisted"
    VALIDATION_WARNING = "validation.warning"
    GOAL_RESUMED = "goal.resumed"
    FEEDBACK_RECORDED = "feedback.recorded"
    CORPUS_SEARCH = "corpus.search"
    SKILL_MATCHED = "skill.matched"
    SKILL_CREATED = "skill.created"
    SKILL_UPDATED = "skill.updated"
    CONTEXT_COMPRESSED = "context.compressed"
    SOUL_UPDATED = "soul.updated"
    REFLECTION_TRIGGERED = "reflection.triggered"
    HEARTBEAT_ANOMALY = "heartbeat.anomaly"
    HEARTBEAT_ESCALATE = "heartbeat.escalate"


@dataclass(frozen=True)
class Event:
    """Immutable record of something that happened in the system."""

    event_type: EventType
    agent_name: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str = ""


EventHandler = Callable[[Event], Any]


@dataclass
class EventBus:
    """Publish / subscribe hub for Airees lifecycle events.

    Handlers registered via ``subscribe`` receive only the requested
    ``EventType``.  Handlers registered via ``subscribe_all`` act as
    wildcard listeners and receive every event.
    """

    _handlers: dict[EventType, list[EventHandler]] = field(default_factory=dict)
    _wildcard_handlers: list[EventHandler] = field(default_factory=list)

    # -- registration -------------------------------------------------------

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Register *handler* for a specific ``EventType``."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Register *handler* to receive **every** event (wildcard)."""
        self._wildcard_handlers.append(handler)

    # -- dispatching --------------------------------------------------------

    def emit(self, event: Event) -> None:
        """Synchronously dispatch *event* to all matching handlers.

        Raises ``RuntimeError`` if any handler returns a coroutine — use
        ``emit_async`` instead when async handlers are registered.
        """
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if asyncio.iscoroutine(result):
                raise RuntimeError("Use emit_async for async handlers")
        for handler in self._wildcard_handlers:
            result = handler(event)
            if asyncio.iscoroutine(result):
                raise RuntimeError("Use emit_async for async handlers")

    async def emit_async(self, event: Event) -> None:
        """Dispatch *event*, awaiting any coroutine handlers."""
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        for handler in self._wildcard_handlers:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
