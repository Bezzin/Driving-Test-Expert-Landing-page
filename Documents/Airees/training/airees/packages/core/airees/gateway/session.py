"""Session and turn management for multi-channel conversations.

Sessions are mutable state containers — one per (channel, sender_id) pair.
The :class:`SessionStore` is an in-memory registry that creates sessions
on demand and provides lookup by composite key.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class Session:
    """A single conversation session between a user and Airees.

    Unlike gateway value objects, sessions are intentionally **mutable**
    because they accumulate conversation turns over time.

    Attributes:
        channel: Originating channel name.
        sender_id: Identifier for the user within the channel.
        messages: Chronological list of ``{"role": ..., "content": ...}`` dicts.
        created_at: Unix epoch when the session was created.
        updated_at: Unix epoch of the most recent turn.
        metadata: Arbitrary per-session key/value pairs.
    """

    channel: str
    sender_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_turn(self, *, user_text: str, assistant_text: str) -> None:
        """Append a user/assistant exchange and update the timestamp."""
        self.messages.append({"role": "user", "content": user_text})
        self.messages.append({"role": "assistant", "content": assistant_text})
        self.updated_at = time.time()
        log.debug(
            "Session %s:%s turn added (total messages: %d)",
            self.channel,
            self.sender_id,
            len(self.messages),
        )

    def get_context_messages(self, max_turns: int = 10) -> list[dict[str, str]]:
        """Return the last *max_turns* user/assistant pairs.

        Each turn consists of two messages, so this returns at most
        ``max_turns * 2`` items from the end of the message history.
        """
        limit = max_turns * 2
        return list(self.messages[-limit:])


@dataclass
class SessionStore:
    """In-memory session registry keyed by ``channel:sender_id``."""

    _sessions: dict[str, Session] = field(default_factory=dict)

    def get_or_create(self, channel: str, sender_id: str) -> Session:
        """Return the existing session or create a new one."""
        key = f"{channel}:{sender_id}"
        if key not in self._sessions:
            self._sessions[key] = Session(channel=channel, sender_id=sender_id)
            log.info("New session created: %s", key)
        return self._sessions[key]

    @property
    def active_sessions(self) -> int:
        """Number of tracked sessions."""
        return len(self._sessions)
