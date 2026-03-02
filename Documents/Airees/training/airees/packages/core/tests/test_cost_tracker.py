"""Tests for gateway.cost_tracker — ModelCost and CostTracker."""
from __future__ import annotations

import pytest

from airees.gateway.cost_tracker import CostTracker, ModelCost


class TestModelCostDefaults:
    """ModelCost.defaults() returns the expected model tiers."""

    def test_defaults_has_all_tiers(self) -> None:
        """defaults() includes haiku, sonnet, and opus entries."""
        costs = ModelCost.defaults()

        assert "haiku" in costs
        assert "sonnet" in costs
        assert "opus" in costs
        assert len(costs) == 3

        # Verify each is a ModelCost instance
        for tier, cost in costs.items():
            assert isinstance(cost, ModelCost), f"{tier} is not a ModelCost"
            assert cost.input_per_mtok > 0
            assert cost.output_per_mtok > 0


class TestCostTracker:
    """CostTracker records API usage and computes costs."""

    def test_record_and_total_cost(self) -> None:
        """record() calculates cost and total_cost sums all records."""
        tracker = CostTracker()

        # 1M input tokens of haiku at $1.0/M = $1.0
        # 500K output tokens of haiku at $5.0/M = $2.5
        cost = tracker.record(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=500_000,
            channel="cli",
        )

        expected = (1_000_000 / 1_000_000) * 1.0 + (500_000 / 1_000_000) * 5.0
        assert cost == pytest.approx(expected)
        assert tracker.total_cost == pytest.approx(expected)

    def test_per_model_breakdown(self) -> None:
        """breakdown() returns cost grouped by model tier."""
        tracker = CostTracker()

        tracker.record(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=0,
            channel="cli",
        )
        tracker.record(
            model="claude-sonnet-4-5",
            input_tokens=1_000_000,
            output_tokens=0,
            channel="cli",
        )

        breakdown = tracker.breakdown()

        assert breakdown["haiku"] == pytest.approx(1.0)
        assert breakdown["sonnet"] == pytest.approx(3.0)

    def test_per_channel_cost(self) -> None:
        """by_channel() returns cost grouped by channel name."""
        tracker = CostTracker()

        tracker.record(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=0,
            channel="cli",
        )
        tracker.record(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=0,
            channel="telegram",
        )

        by_chan = tracker.by_channel()

        assert by_chan["cli"] == pytest.approx(1.0)
        assert by_chan["telegram"] == pytest.approx(1.0)

    def test_reset_clears_records(self) -> None:
        """reset() removes all records and zeroes totals."""
        tracker = CostTracker()
        tracker.record(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=0,
            channel="cli",
        )

        assert tracker.total_cost > 0

        tracker.reset()

        assert tracker.total_cost == 0.0
        assert tracker.total_turns == 0
        assert tracker.breakdown() == {}
        assert tracker.by_channel() == {}

    def test_total_turns_counts_records(self) -> None:
        """total_turns returns the number of recorded API calls."""
        tracker = CostTracker()

        assert tracker.total_turns == 0

        tracker.record(
            model="claude-haiku-4-5",
            input_tokens=100,
            output_tokens=50,
            channel="cli",
        )
        tracker.record(
            model="claude-sonnet-4-5",
            input_tokens=200,
            output_tokens=100,
            channel="telegram",
        )

        assert tracker.total_turns == 2

    def test_unknown_model_defaults_to_sonnet(self) -> None:
        """An unrecognised model name falls back to sonnet pricing."""
        tracker = CostTracker()
        cost = tracker.record(
            model="some-unknown-model",
            input_tokens=1_000_000,
            output_tokens=0,
            channel="cli",
        )

        # sonnet input: 3.0 per M tokens
        assert cost == pytest.approx(3.0)
        assert tracker.breakdown()["sonnet"] == pytest.approx(3.0)
