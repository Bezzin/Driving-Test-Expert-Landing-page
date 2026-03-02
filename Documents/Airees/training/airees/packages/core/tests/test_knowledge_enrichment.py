"""Tests for knowledge-enriched conversation context."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.types import InboundMessage
from airees.knowledge.store import KnowledgeStore
from tests.test_conversation_manager import FakeRouter


@pytest.mark.asyncio
async def test_knowledge_enriches_system_prompt():
    """When knowledge_store has relevant docs, they appear in the prompt."""
    tmp = Path(tempfile.mkdtemp())

    # Create and populate knowledge store
    kb = KnowledgeStore(data_dir=tmp / "knowledge")
    doc = tmp / "project.txt"
    doc.write_text("The Airees project deadline is March 15th 2026.", encoding="utf-8")
    kb.ingest(doc)

    router = FakeRouter(reply="noted")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        knowledge_store=kb,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="when is the Airees deadline?")
    await mgr.handle(msg)

    # Check that the router received enriched context
    assert len(router._calls) == 1
    system_prompt = router._calls[0]["system"]
    assert "Relevant knowledge" in system_prompt or "deadline" in system_prompt.lower()


@pytest.mark.asyncio
async def test_no_knowledge_store_works_unchanged():
    """Without a KnowledgeStore, system prompt is built the same as before."""
    router = FakeRouter(reply="hello")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="hi there")
    await mgr.handle(msg)

    assert len(router._calls) == 1
    system_prompt = router._calls[0]["system"]
    assert "Relevant knowledge" not in system_prompt


@pytest.mark.asyncio
async def test_empty_knowledge_store_no_enrichment():
    """An empty KnowledgeStore should not add any knowledge section."""
    tmp = Path(tempfile.mkdtemp())

    kb = KnowledgeStore(data_dir=tmp / "knowledge")
    # Don't ingest anything — store is empty

    router = FakeRouter(reply="ok")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        knowledge_store=kb,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="hello")
    await mgr.handle(msg)

    assert len(router._calls) == 1
    system_prompt = router._calls[0]["system"]
    assert "Relevant knowledge" not in system_prompt
