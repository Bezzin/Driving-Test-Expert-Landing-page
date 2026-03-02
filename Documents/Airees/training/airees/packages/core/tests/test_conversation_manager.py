"""Tests for ConversationManager — the central gateway orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.session import SessionStore
from airees.gateway.types import InboundMessage, OutboundMessage


# -- Fake router that mimics router.create_message ---------------------------


@dataclass
class FakeResponse:
    """Mimics the response.content[0].text structure."""

    text: str


@dataclass
class FakeRouterResponse:
    """Mimics router create_message return value."""

    content: list[FakeResponse] = field(default_factory=list)


@dataclass
class FakeRouter:
    """Fake model router for testing."""

    _calls: list[dict[str, Any]] = field(default_factory=list, init=False)
    reply: str = "fake reply"

    async def create_message(self, **kwargs: Any) -> FakeRouterResponse:
        self._calls.append(kwargs)
        return FakeRouterResponse(content=[FakeResponse(text=self.reply)])


# -- Fake orchestrator -------------------------------------------------------


@dataclass
class FakeOrchestrator:
    """Fake orchestrator for complex tasks."""

    reply: str = "orchestrated reply"

    async def submit_goal(self, text: str) -> str:
        return "goal-1"

    async def execute_goal(self, goal_id: str) -> str:
        return self.reply


# -- Helpers -----------------------------------------------------------------


def _make_manager(
    *,
    router: Any = None,
    orchestrator: Any = None,
    tmp_path: Path | None = None,
) -> ConversationManager:
    """Create a ConversationManager with test defaults."""
    return ConversationManager(
        router=router or FakeRouter(),
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        orchestrator=orchestrator,
    )


# -- Tests -------------------------------------------------------------------


def test_creates_with_session_store():
    mgr = _make_manager()
    assert isinstance(mgr.sessions, SessionStore)


@pytest.mark.asyncio
async def test_quick_message_uses_run_quick():
    router = FakeRouter(reply="hello back")
    mgr = _make_manager(router=router)

    msg = InboundMessage(channel="cli", sender_id="user-1", text="hi")
    response = await mgr.handle(msg)

    assert isinstance(response, OutboundMessage)
    assert response.text == "hello back"
    assert response.channel == "cli"
    assert response.recipient_id == "user-1"
    # Router should have been called
    assert len(router._calls) == 1


@pytest.mark.asyncio
async def test_complex_message_uses_run_orchestrated():
    router = FakeRouter()
    orchestrator = FakeOrchestrator(reply="detailed plan complete")
    mgr = _make_manager(router=router, orchestrator=orchestrator)

    msg = InboundMessage(
        channel="cli",
        sender_id="user-1",
        text="plan and create a comprehensive multi-step deployment strategy",
    )
    response = await mgr.handle(msg)

    assert response.text == "detailed plan complete"
    # Router should NOT have been called for complex messages
    assert len(router._calls) == 0


@pytest.mark.asyncio
async def test_records_turn_in_session():
    router = FakeRouter(reply="noted")
    mgr = _make_manager(router=router)

    msg = InboundMessage(channel="cli", sender_id="user-1", text="remember this")
    await mgr.handle(msg)

    session = mgr.sessions.get_or_create("cli", "user-1")
    assert len(session.messages) == 2
    assert session.messages[0] == {"role": "user", "content": "remember this"}
    assert session.messages[1] == {"role": "assistant", "content": "noted"}


@pytest.mark.asyncio
async def test_includes_history_in_context():
    router = FakeRouter(reply="second reply")
    mgr = _make_manager(router=router)

    # First turn
    msg1 = InboundMessage(channel="cli", sender_id="user-1", text="first message")
    await mgr.handle(msg1)

    # Second turn — should include first turn in context
    msg2 = InboundMessage(channel="cli", sender_id="user-1", text="second message")
    await mgr.handle(msg2)

    # The router should have received context messages on the second call
    assert len(router._calls) == 2
    second_call = router._calls[1]
    messages = second_call["messages"]
    # Should contain history (first turn) plus new user message
    assert len(messages) >= 3  # 2 from first turn + 1 new user message
    assert messages[0]["content"] == "first message"
    assert messages[1]["content"] == "second reply"
    assert messages[-1]["content"] == "second message"
