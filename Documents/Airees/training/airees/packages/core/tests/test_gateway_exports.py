"""Tests for gateway package exports — verifies all gateway types importable from airees."""
from __future__ import annotations


def test_import_gateway_types() -> None:
    """InboundMessage, OutboundMessage, Attachment importable from airees."""
    from airees import Attachment, InboundMessage, OutboundMessage

    assert InboundMessage is not None
    assert OutboundMessage is not None
    assert Attachment is not None


def test_import_adapter_registry() -> None:
    """AdapterRegistry importable from airees."""
    from airees import AdapterRegistry

    assert AdapterRegistry is not None


def test_import_complexity() -> None:
    """Complexity and classify_complexity importable from airees."""
    from airees import Complexity, classify_complexity

    assert Complexity is not None
    assert classify_complexity is not None


def test_import_conversation_manager() -> None:
    """ConversationManager importable from airees."""
    from airees import ConversationManager

    assert ConversationManager is not None


def test_import_gateway_and_session() -> None:
    """Gateway, Session, SessionStore, PersonalContext, load_personal_context importable."""
    from airees import (
        Gateway,
        PersonalContext,
        Session,
        SessionStore,
        load_personal_context,
    )

    assert Gateway is not None
    assert Session is not None
    assert SessionStore is not None
    assert PersonalContext is not None
    assert load_personal_context is not None
