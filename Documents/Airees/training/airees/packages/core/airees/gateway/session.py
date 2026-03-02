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
    """In-memory session registry keyed by ``channel:sender_id``.

    Parameters:
        max_sessions: Hard cap on stored sessions.  When exceeded after
            TTL eviction the oldest sessions (by ``updated_at``) are
            removed until the count is back under the limit.
        session_ttl: Time-to-live in seconds.  Sessions whose
            ``updated_at`` is older than this are evicted on the next
            :meth:`get_or_create` call.
    """

    max_sessions: int = 1000
    session_ttl: float = 3600.0
    _sessions: dict[str, Session] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_sessions < 1:
            raise ValueError(f"max_sessions must be >= 1, got {self.max_sessions}")
        if self.session_ttl <= 0:
            raise ValueError(f"session_ttl must be > 0, got {self.session_ttl}")

    # -- eviction -------------------------------------------------------------

    def _evict_stale(self) -> None:
        """Remove sessions that exceed *session_ttl* or *max_sessions*."""
        now = time.time()
        cutoff = now - self.session_ttl

        # 1. Remove sessions older than TTL
        stale_keys = [
            key
            for key, session in self._sessions.items()
            if session.updated_at < cutoff
        ]
        for key in stale_keys:
            del self._sessions[key]
            log.info("Evicted stale session: %s", key)

        # 2. If still over max_sessions, evict oldest by updated_at
        if len(self._sessions) >= self.max_sessions:
            sorted_keys = sorted(
                self._sessions,
                key=lambda k: self._sessions[k].updated_at,
            )
            evict_count = len(self._sessions) - self.max_sessions + 1
            for key in sorted_keys[:evict_count]:
                del self._sessions[key]
                log.info("Evicted session (over capacity): %s", key)

    # -- public API -----------------------------------------------------------

    def get_or_create(self, channel: str, sender_id: str) -> Session:
        """Return the existing session or create a new one.

        Triggers :meth:`_evict_stale` before lookup so that stale or
        over-capacity sessions are cleaned up lazily.
        """
        self._evict_stale()
        key = f"{channel}:{sender_id}"
        if key not in self._sessions:
            self._sessions[key] = Session(channel=channel, sender_id=sender_id)
            log.info("New session created: %s", key)
        return self._sessions[key]

    def remove(self, channel: str, sender_id: str) -> bool:
        """Explicitly remove a session.  Returns ``True`` if it existed."""
        key = f"{channel}:{sender_id}"
        if key in self._sessions:
            del self._sessions[key]
            log.info("Session removed: %s", key)
            return True
        return False

    @property
    def active_sessions(self) -> int:
        """Number of tracked sessions."""
        return len(self._sessions)
