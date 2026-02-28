"""Tests for context budget tracking."""
import pytest

from airees.context_budget import ContextBudget


def test_budget_creation():
    budget = ContextBudget(max_tokens=200000)
    assert budget.max_tokens == 200000
    assert budget.used_tokens == 0
    assert budget.remaining == 200000


def test_budget_usage_percent():
    budget = ContextBudget(max_tokens=100000, used_tokens=5000)
    assert budget.usage_percent == 5.0


def test_budget_consume():
    budget = ContextBudget(max_tokens=100000)
    updated = budget.consume(10000)
    assert updated.used_tokens == 10000
    assert updated.remaining == 90000


def test_budget_exceeds_threshold():
    budget = ContextBudget(max_tokens=100000, used_tokens=85000)
    assert budget.exceeds_threshold(80.0) is True
    assert budget.exceeds_threshold(90.0) is False


def test_budget_max_percent():
    budget = ContextBudget(max_tokens=200000, max_usage_percent=5.0)
    assert budget.effective_max == 10000


def test_budget_is_over_limit():
    budget = ContextBudget(max_tokens=200000, max_usage_percent=5.0, used_tokens=15000)
    assert budget.is_over_limit is True


def test_budget_not_over_limit():
    budget = ContextBudget(max_tokens=200000, max_usage_percent=5.0, used_tokens=5000)
    assert budget.is_over_limit is False
