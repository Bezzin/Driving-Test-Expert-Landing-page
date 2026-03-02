"""Tests for Telegram voice message handling."""
from __future__ import annotations

import pytest

from airees.gateway.adapters.telegram_adapter import TelegramAdapter


def test_telegram_has_voice_support_flag():
    adapter = TelegramAdapter(bot_token="fake")
    assert hasattr(adapter, "voice_enabled")


def test_telegram_voice_disabled_by_default():
    adapter = TelegramAdapter(bot_token="fake")
    assert adapter.voice_enabled is False


def test_telegram_voice_can_be_enabled():
    adapter = TelegramAdapter(bot_token="fake", voice_enabled=True)
    assert adapter.voice_enabled is True
