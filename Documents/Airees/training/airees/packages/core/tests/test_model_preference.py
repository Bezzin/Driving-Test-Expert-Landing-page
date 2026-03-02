"""Tests for adaptive model preference learning."""
from __future__ import annotations

import pytest

from airees.gateway.model_preference import ModelPreference


def test_default_preference_returns_hint():
    """With no history, returns the default model hint."""
    pref = ModelPreference()
    assert pref.get_model("quick") == "haiku"
    assert pref.get_model("moderate") == "sonnet"
    assert pref.get_model("complex") == "opus"


def test_record_success_at_cheaper_tier():
    """After enough successes at a cheaper tier, prefer it."""
    pref = ModelPreference(downgrade_threshold=3)

    # Record 3 successes of "moderate" tasks at "haiku"
    for _ in range(3):
        pref.record(complexity="moderate", model_used="haiku", success=True)

    # Should now prefer haiku for moderate
    assert pref.get_model("moderate") == "haiku"


def test_record_failure_upgrades():
    """After failures at a tier, don't downgrade."""
    pref = ModelPreference(downgrade_threshold=3, upgrade_threshold=2)

    # Record 2 failures at haiku for moderate
    pref.record(complexity="moderate", model_used="haiku", success=False)
    pref.record(complexity="moderate", model_used="haiku", success=False)

    # Should keep sonnet for moderate (not downgrade)
    assert pref.get_model("moderate") == "sonnet"


def test_stats_returns_counts():
    pref = ModelPreference()
    pref.record(complexity="quick", model_used="haiku", success=True)
    pref.record(complexity="quick", model_used="haiku", success=True)
    pref.record(complexity="quick", model_used="haiku", success=False)

    stats = pref.stats()
    assert stats["quick"]["haiku"]["successes"] == 2
    assert stats["quick"]["haiku"]["failures"] == 1
