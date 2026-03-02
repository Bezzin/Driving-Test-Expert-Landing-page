"""End-to-end integration tests for the gateway layer.

Each test wires up real Gateway + ConversationManager instances with a
mocked model router (no real API calls) to verify the full message
lifecycle from inbound message to outbound reply.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.server import Gateway
from airees.gateway.types import InboundMessage, OutboundMessage


# -- Helpers -----------------------------------------------------------------


def _make_mock_router() -> MagicMock:
    """Create a mock router whose create_message returns a realistic response."""
    mock_router = MagicMock()
    mock_router.create_message = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text="response")])
    )
    return mock_router


def _make_gateway(
    *,
    router: MagicMock,
    soul_path: Path,
    user_path: Path,
) -> Gateway:
    """Create a Gateway + ConversationManager wired to the given mock router."""
    manager = ConversationManager(
        router=router,
        event_bus=MagicMock(),
        soul_path=soul_path,
        user_path=user_path,
    )
    return Gateway(conversation_manager=manager)


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_cli_message_flow(tmp_path: Path) -> None:
    """Full flow: CLI message -> Gateway -> ConversationManager -> mock router -> response.

    Verifies:
    - Response is an OutboundMessage with correct channel.
    - Session records the turn.
    - Router was called with haiku model (short message = QUICK complexity).
    """
    mock_router = _make_mock_router()
    soul_path = tmp_path / "SOUL.md"
    user_path = tmp_path / "USER.md"

    gw = _make_gateway(
        router=mock_router,
        soul_path=soul_path,
        user_path=user_path,
    )

    msg = InboundMessage(channel="cli", sender_id="user1", text="hello")
    result = await gw.handle_message(msg)

    # Response is an OutboundMessage for the CLI channel
    assert isinstance(result, OutboundMessage)
    assert result.channel == "cli"
    assert result.recipient_id == "user1"
    assert result.text == "response"

    # Session recorded the turn (user + assistant = 2 messages)
    session = gw.conversation_manager.sessions.get_or_create("cli", "user1")
    assert len(session.messages) == 2
    assert session.messages[0]["role"] == "user"
    assert session.messages[1]["role"] == "assistant"

    # Router was called once with haiku model (short "hello" = QUICK)
    mock_router.create_message.assert_awaited_once()
    call_kwargs = mock_router.create_message.call_args[1]
    assert "haiku" in call_kwargs["model"].lower()


@pytest.mark.asyncio
async def test_e2e_multi_turn_context(tmp_path: Path) -> None:
    """Two messages from the same user should include prior conversation history.

    On the second call the router should receive at least 3 messages:
    the first user message, the first assistant reply, and the new user message.
    """
    mock_router = _make_mock_router()
    soul_path = tmp_path / "SOUL.md"
    user_path = tmp_path / "USER.md"

    gw = _make_gateway(
        router=mock_router,
        soul_path=soul_path,
        user_path=user_path,
    )

    # First turn
    msg1 = InboundMessage(channel="cli", sender_id="user1", text="hello")
    await gw.handle_message(msg1)

    # Second turn — should carry history
    msg2 = InboundMessage(channel="cli", sender_id="user1", text="thanks")
    await gw.handle_message(msg2)

    # The second router call should include at least 3 messages
    assert mock_router.create_message.call_count == 2
    second_call_kwargs = mock_router.create_message.call_args_list[1][1]
    messages = second_call_kwargs["messages"]

    # At least: user("hello"), assistant("response"), user("thanks")
    assert len(messages) >= 3
    assert messages[0]["content"] == "hello"
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[-1]["content"] == "thanks"
    assert messages[-1]["role"] == "user"


@pytest.mark.asyncio
async def test_e2e_personal_context_loaded(tmp_path: Path) -> None:
    """USER.md personal context is included in the system prompt sent to the router.

    Verifies the router's system prompt includes the user's name and timezone.
    """
    mock_router = _make_mock_router()
    soul_path = tmp_path / "SOUL.md"
    user_path = tmp_path / "USER.md"

    # Write USER.md with personal context
    user_path.write_text(
        "---\nname: Nathaniel\ntimezone: Europe/London\n---\n\nPrefers concise answers.\n",
        encoding="utf-8",
    )

    gw = _make_gateway(
        router=mock_router,
        soul_path=soul_path,
        user_path=user_path,
    )

    msg = InboundMessage(channel="cli", sender_id="user1", text="hi")
    await gw.handle_message(msg)

    # Router should have been called with a system prompt containing personal context
    mock_router.create_message.assert_awaited_once()
    call_kwargs = mock_router.create_message.call_args[1]
    system_prompt = call_kwargs["system"]

    assert "Nathaniel" in system_prompt
    assert "Europe/London" in system_prompt
