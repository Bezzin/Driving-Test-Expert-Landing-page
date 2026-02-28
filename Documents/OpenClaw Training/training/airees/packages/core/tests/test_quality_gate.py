"""Tests for quality gate system."""
import pytest

from airees.quality_gate import GateAction, GateResult, QualityGate


def test_gate_creation():
    gate = QualityGate(name="code-review", min_score=8, max_retries=3, on_failure=GateAction.RETRY)
    assert gate.name == "code-review"
    assert gate.min_score == 8
    assert gate.max_retries == 3


def test_gate_result_pass():
    result = GateResult(score=9, passed=True, feedback="Looks good")
    assert result.passed is True


def test_gate_result_fail():
    result = GateResult(score=5, passed=False, feedback="Missing tests")
    assert result.passed is False


def test_gate_evaluate_pass():
    gate = QualityGate(name="test", min_score=7)
    result = gate.evaluate(score=8, feedback="OK")
    assert result.passed is True


def test_gate_evaluate_fail():
    gate = QualityGate(name="test", min_score=8)
    result = gate.evaluate(score=6, feedback="Bad")
    assert result.passed is False


def test_gate_should_retry():
    gate = QualityGate(name="test", min_score=8, max_retries=3)
    assert gate.should_retry(attempt=1) is True
    assert gate.should_retry(attempt=2) is True
    assert gate.should_retry(attempt=3) is False


def test_gate_should_escalate():
    gate = QualityGate(name="test", min_score=8, max_retries=3, on_failure=GateAction.FLAG_HUMAN)
    assert gate.should_escalate(attempt=3) is True
    assert gate.should_escalate(attempt=1) is False
