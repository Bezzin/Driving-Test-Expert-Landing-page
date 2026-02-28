"""Tests for self-improving feedback loops."""
import pytest

from airees.feedback import FeedbackConfig, FeedbackEntry, FeedbackLoop


def test_feedback_config_creation():
    config = FeedbackConfig(evaluate_after=True, success_criteria="score >= 8")
    assert config.evaluate_after is True


def test_feedback_entry_creation():
    entry = FeedbackEntry(
        run_id="run-001",
        agent_name="builder",
        outcome="success",
        score=9.0,
        lesson="Template approach worked well",
    )
    assert entry.outcome == "success"
    assert entry.score == 9.0


def test_feedback_loop_record():
    loop = FeedbackLoop()
    updated = loop.record(FeedbackEntry(
        run_id="run-001",
        agent_name="builder",
        outcome="success",
        score=9.0,
        lesson="X worked",
    ))
    assert len(updated.entries) == 1


def test_feedback_loop_to_memory():
    loop = FeedbackLoop()
    loop = loop.record(FeedbackEntry(
        run_id="run-001",
        agent_name="builder",
        outcome="success",
        score=9.0,
        lesson="Templates save time",
    ))
    loop = loop.record(FeedbackEntry(
        run_id="run-002",
        agent_name="builder",
        outcome="failure",
        score=4.0,
        lesson="Skip payments causes rejection",
    ))
    memory = loop.to_memory_content("builder")
    assert "Templates save time" in memory
    assert "Skip payments causes rejection" in memory
    assert "success" in memory.lower() or "SUCCESS" in memory
    assert "failure" in memory.lower() or "FAILURE" in memory


def test_feedback_loop_immutability():
    loop = FeedbackLoop()
    loop.record(FeedbackEntry(
        run_id="x",
        agent_name="a",
        outcome="success",
        score=1.0,
        lesson="y",
    ))
    assert len(loop.entries) == 0
