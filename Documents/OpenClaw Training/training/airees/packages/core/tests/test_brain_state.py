"""Tests for Brain state machine."""
import pytest
from airees.brain.state_machine import BrainState, BrainStateMachine


def test_initial_state():
    sm = BrainStateMachine()
    assert sm.state == BrainState.IDLE


def test_valid_transition_idle_to_planning():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    assert sm.state == BrainState.PLANNING


def test_valid_transition_planning_to_delegating():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    assert sm.state == BrainState.DELEGATING


def test_invalid_transition_raises():
    sm = BrainStateMachine()
    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition(BrainState.EVALUATING)


def test_full_happy_path():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    sm.transition(BrainState.WAITING)
    sm.transition(BrainState.EVALUATING)
    sm.transition(BrainState.COMPLETING)
    sm.transition(BrainState.IDLE)
    assert sm.state == BrainState.IDLE


def test_iteration_path():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    sm.transition(BrainState.WAITING)
    sm.transition(BrainState.EVALUATING)
    sm.transition(BrainState.ADAPTING)
    sm.transition(BrainState.DELEGATING)
    assert sm.state == BrainState.DELEGATING


def test_transition_history():
    sm = BrainStateMachine()
    sm.transition(BrainState.PLANNING)
    sm.transition(BrainState.DELEGATING)
    assert len(sm.history) == 2
    assert sm.history[0] == (BrainState.IDLE, BrainState.PLANNING)
