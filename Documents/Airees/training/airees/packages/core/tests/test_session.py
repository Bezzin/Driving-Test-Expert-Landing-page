"""Tests for Session and SessionStore turn management."""
from __future__ import annotations

import time

import pytest

from airees.gateway.session import Session, SessionStore


# -- Session creation ---------------------------------------------------------


def test_session_creates_with_defaults():
    before = time.time()
    session = Session(channel="cli", sender_id="user-1")
    after = time.time()

    assert session.channel == "cli"
    assert session.sender_id == "user-1"
    assert session.messages == []
    assert before <= session.created_at <= after
    assert before <= session.updated_at <= after
    assert session.metadata == {}


# -- add_turn -----------------------------------------------------------------


def test_add_turn_appends_pair():
    session = Session(channel="cli", sender_id="u1")
    session.add_turn(user_text="hello", assistant_text="hi there")

    assert len(session.messages) == 2
    assert session.messages[0] == {"role": "user", "content": "hello"}
    assert session.messages[1] == {"role": "assistant", "content": "hi there"}


# -- get_context_messages -----------------------------------------------------


def test_get_context_messages_limits():
    session = Session(channel="cli", sender_id="u1")
    for i in range(20):
        session.add_turn(user_text=f"q{i}", assistant_text=f"a{i}")

    # 40 messages total, max_turns=5 should return last 10 messages
    context = session.get_context_messages(max_turns=5)
    assert len(context) == 10
    assert context[0]["content"] == "q15"
    assert context[-1]["content"] == "a19"


def test_get_context_messages_fewer_than_max_returns_all():
    session = Session(channel="cli", sender_id="u1")
    session.add_turn(user_text="only", assistant_text="one")

    context = session.get_context_messages(max_turns=10)
    assert len(context) == 2


# -- SessionStore -------------------------------------------------------------


def test_store_get_or_create():
    store = SessionStore()
    session = store.get_or_create("cli", "user-1")

    assert isinstance(session, Session)
    assert session.channel == "cli"
    assert session.sender_id == "user-1"


def test_store_returns_existing():
    store = SessionStore()
    s1 = store.get_or_create("cli", "user-1")
    s2 = store.get_or_create("cli", "user-1")

    assert s1 is s2


def test_store_separates_channels():
    store = SessionStore()
    s1 = store.get_or_create("cli", "user-1")
    s2 = store.get_or_create("telegram", "user-1")

    assert s1 is not s2
    assert s1.channel == "cli"
    assert s2.channel == "telegram"


def test_store_active_sessions_count():
    store = SessionStore()
    assert store.active_sessions == 0

    store.get_or_create("cli", "user-1")
    assert store.active_sessions == 1

    store.get_or_create("cli", "user-2")
    assert store.active_sessions == 2

    # Same key should not increase count
    store.get_or_create("cli", "user-1")
    assert store.active_sessions == 2
