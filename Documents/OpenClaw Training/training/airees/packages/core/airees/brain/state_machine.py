"""Brain state machine — controls the orchestrator lifecycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BrainState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    DELEGATING = "delegating"
    WAITING = "waiting"
    EVALUATING = "evaluating"
    ADAPTING = "adapting"
    COMPLETING = "completing"


VALID_TRANSITIONS: dict[BrainState, set[BrainState]] = {
    BrainState.IDLE: {BrainState.PLANNING},
    BrainState.PLANNING: {BrainState.DELEGATING},
    BrainState.DELEGATING: {BrainState.WAITING},
    BrainState.WAITING: {BrainState.EVALUATING},
    BrainState.EVALUATING: {BrainState.ADAPTING, BrainState.COMPLETING},
    BrainState.ADAPTING: {BrainState.DELEGATING},
    BrainState.COMPLETING: {BrainState.IDLE},
}


@dataclass
class BrainStateMachine:
    state: BrainState = BrainState.IDLE
    history: list[tuple[BrainState, BrainState]] = field(default_factory=list)

    def transition(self, new_state: BrainState) -> None:
        valid = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in valid:
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {new_state.value}. "
                f"Valid targets: {[s.value for s in valid]}"
            )
        self.history.append((self.state, new_state))
        self.state = new_state

    def force_reset(self, reason: str = "max_iterations") -> None:
        """Force state back to IDLE, recording in history for auditability."""
        self.history.append((self.state, BrainState.IDLE))
        self.state = BrainState.IDLE

    def can_transition(self, new_state: BrainState) -> bool:
        return new_state in VALID_TRANSITIONS.get(self.state, set())
