"""Tests for Phase 7 exports."""
from __future__ import annotations

import pytest


def test_learning_exports():
    from airees import AutoSkillCapture, ModelPreference
    assert AutoSkillCapture is not None
    assert ModelPreference is not None


def test_knowledge_exports():
    from airees.knowledge.store import KnowledgeStore, KnowledgeResult
    assert KnowledgeStore is not None
    assert KnowledgeResult is not None


def test_knowledge_top_level_exports():
    from airees import KnowledgeStore, KnowledgeResult
    assert KnowledgeStore is not None
    assert KnowledgeResult is not None


def test_cron_exports():
    from airees.gateway.cron import CronTrigger, is_due
    assert CronTrigger is not None
    assert is_due is not None


def test_cron_top_level_exports():
    from airees import CronTrigger
    assert CronTrigger is not None


def test_proactive_exports():
    from airees.gateway.proactive import ProactiveScheduler
    assert ProactiveScheduler is not None


def test_proactive_top_level_exports():
    from airees import ProactiveScheduler
    assert ProactiveScheduler is not None


def test_discord_exports():
    from airees.gateway.adapters.discord_adapter import DiscordAdapter
    assert DiscordAdapter is not None


def test_voice_exports():
    from airees.voice.stt import SpeechToText
    from airees.voice.tts import TextToSpeech
    assert SpeechToText is not None
    assert TextToSpeech is not None


def test_voice_top_level_exports():
    from airees import SpeechToText, TextToSpeech
    assert SpeechToText is not None
    assert TextToSpeech is not None


@pytest.mark.asyncio
async def test_bootstrap_gateway_wires_knowledge_store(monkeypatch, tmp_path):
    """Verify bootstrap_gateway creates a KnowledgeStore and passes it to ConversationManager."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Write a minimal config file
    config_file = tmp_path / "airees.yaml"
    config_file.write_text(f"data_dir: {tmp_path / 'data'}\n")

    from airees.cli.bootstrap import bootstrap_gateway

    gateway = await bootstrap_gateway(config_file)

    # ConversationManager should have a KnowledgeStore set
    from airees.knowledge.store import KnowledgeStore
    assert isinstance(
        gateway.conversation_manager.knowledge_store, KnowledgeStore
    )
