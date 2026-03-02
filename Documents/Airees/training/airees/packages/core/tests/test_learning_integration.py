"""Integration test: learning loop wired end-to-end."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.cost_tracker import CostTracker
from airees.gateway.learning import AutoSkillCapture
from airees.gateway.model_preference import ModelPreference
from airees.gateway.session import SessionStore
from airees.gateway.types import InboundMessage
from airees.skill_store import SkillStore

# Reuse FakeRouter from test_conversation_manager
from tests.test_conversation_manager import FakeRouter


@pytest.mark.asyncio
async def test_learning_loop_wired():
    """ConversationManager with all learning components responds."""
    tmp = Path(tempfile.mkdtemp())
    skills_dir = tmp / "skills"
    skills_dir.mkdir()

    store = SkillStore(skills_dir=skills_dir)
    tracker = CostTracker()
    pref = ModelPreference()

    mgr = ConversationManager(
        router=FakeRouter(reply="learned reply"),
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        skill_store=store,
        cost_tracker=tracker,
        model_preference=pref,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="hello there")
    response = await mgr.handle(msg)

    assert response.text == "learned reply"
    assert tracker.total_turns >= 1
