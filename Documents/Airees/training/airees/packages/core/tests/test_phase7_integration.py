"""Phase 7 integration tests — full pipeline with learning + knowledge."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.cost_tracker import CostTracker
from airees.gateway.learning import AutoSkillCapture
from airees.gateway.model_preference import ModelPreference
from airees.gateway.types import InboundMessage
from airees.knowledge.store import KnowledgeStore
from airees.skill_store import SkillStore
from tests.test_conversation_manager import FakeRouter


@pytest.mark.asyncio
async def test_full_pipeline_with_knowledge_and_skills():
    """Message flows through skill check -> knowledge enrichment -> router."""
    tmp = Path(tempfile.mkdtemp())

    # Set up knowledge
    kb = KnowledgeStore(data_dir=tmp / "knowledge")
    doc = tmp / "info.txt"
    doc.write_text("Project deadline is March 15th.", encoding="utf-8")
    kb.ingest(doc)

    # Set up skill store
    skills_dir = tmp / "skills"
    skills_dir.mkdir()
    store = SkillStore(skills_dir=skills_dir)

    router = FakeRouter(reply="Got it, deadline is March 15th")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        skill_store=store,
        cost_tracker=CostTracker(),
        model_preference=ModelPreference(),
        knowledge_store=kb,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="when is the deadline?")
    response = await mgr.handle(msg)

    assert response.text == "Got it, deadline is March 15th"
    # Knowledge should have enriched the system prompt
    assert len(router._calls) == 1
    system = router._calls[0]["system"]
    assert "deadline" in system.lower() or "march" in system.lower()


@pytest.mark.asyncio
async def test_auto_skill_capture_after_success():
    """After a successful goal pattern, skill is auto-captured."""
    tmp = Path(tempfile.mkdtemp())
    skills_dir = tmp / "skills"
    skills_dir.mkdir()
    store = SkillStore(skills_dir=skills_dir)
    capture = AutoSkillCapture(skill_store=store)

    capture.maybe_create_skill(
        goal_text="analyze the sales report",
        result_text="Sales increased 15% QoQ",
        success=True,
    )

    # Skill should now exist
    results = store.search("analyze sales report")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_skill_reuse_after_capture():
    """A captured skill should be reused for similar future requests."""
    tmp = Path(tempfile.mkdtemp())
    skills_dir = tmp / "skills"
    skills_dir.mkdir()
    store = SkillStore(skills_dir=skills_dir)

    # Create a skill (as if auto-captured)
    store.create_skill(
        name="weather-check",
        description="Check weather forecast",
        triggers=["check the weather", "weather forecast", "what is the weather"],
        task_graph="1. Check weather API\n2. Format response",
    )

    router = FakeRouter(reply="Weather is sunny")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        skill_store=store,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="check the weather forecast")
    response = await mgr.handle(msg)

    assert response.text == "Weather is sunny"
    # Should have used the skill path (check system prompt contains skill content)
    assert len(router._calls) == 1
    system = router._calls[0]["system"]
    assert "proven approach" in system.lower() or "task graph" in system.lower()
    # Should use haiku model (cheapest) for skill-matched requests
    assert "haiku" in router._calls[0]["model"]


@pytest.mark.asyncio
async def test_model_preference_learns():
    """ModelPreference should downgrade after enough successes."""
    pref = ModelPreference(downgrade_threshold=2)

    # Record 2 successes of moderate at haiku
    pref.record(complexity="moderate", model_used="haiku", success=True)
    pref.record(complexity="moderate", model_used="haiku", success=True)

    # Should now recommend haiku for moderate
    assert pref.get_model("moderate") == "haiku"

    # Feed this into ConversationManager
    tmp = Path(tempfile.mkdtemp())
    router = FakeRouter(reply="adaptive response")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        model_preference=pref,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="summarize the quarterly report findings")
    response = await mgr.handle(msg)

    assert response.text == "adaptive response"
    # Should use haiku since preference learned it works for moderate
    assert "haiku" in router._calls[0]["model"]
