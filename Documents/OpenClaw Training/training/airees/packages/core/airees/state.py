"""File-based project state machine for resumable multi-phase workflows."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_HUMAN = "needs_human"


@dataclass(frozen=True)
class ProjectState:
    project_id: str
    name: str
    phases: list[str]
    current_phase: str | None = None
    phase_statuses: dict[str, PhaseStatus] = field(default_factory=dict)
    retry_counts: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3

    def __post_init__(self) -> None:
        if self.current_phase is None and self.phases and not self.phase_statuses:
            object.__setattr__(self, "current_phase", self.phases[0])
        if not self.phase_statuses and self.phases:
            statuses = {p: PhaseStatus.PENDING for p in self.phases}
            object.__setattr__(self, "phase_statuses", statuses)

    def advance(self) -> ProjectState:
        if self.current_phase is None:
            return self
        idx = self.phases.index(self.current_phase)
        new_statuses = {**self.phase_statuses, self.current_phase: PhaseStatus.COMPLETED}
        next_phase = self.phases[idx + 1] if idx + 1 < len(self.phases) else None
        return ProjectState(
            project_id=self.project_id, name=self.name, phases=list(self.phases),
            current_phase=next_phase, phase_statuses=new_statuses,
            retry_counts=dict(self.retry_counts), metadata=dict(self.metadata),
            max_retries=self.max_retries,
        )

    def fail_phase(self, error: str) -> ProjectState:
        phase = self.current_phase or self.phases[0]
        count = self.retry_counts.get(phase, 0) + 1
        new_status = PhaseStatus.NEEDS_HUMAN if count >= self.max_retries else PhaseStatus.FAILED
        return ProjectState(
            project_id=self.project_id, name=self.name, phases=list(self.phases),
            current_phase=self.current_phase,
            phase_statuses={**self.phase_statuses, phase: new_status},
            retry_counts={**self.retry_counts, phase: count},
            metadata={**self.metadata, "last_error": error},
            max_retries=self.max_retries,
        )

    def needs_human(self, phase: str) -> bool:
        return self.retry_counts.get(phase, 0) >= self.max_retries

    @property
    def is_complete(self) -> bool:
        return all(s == PhaseStatus.COMPLETED for s in self.phase_statuses.values())


def save_state(state: ProjectState, path: Path) -> None:
    data = {
        "project_id": state.project_id, "name": state.name,
        "phases": state.phases, "current_phase": state.current_phase,
        "phase_statuses": {k: v.value for k, v in state.phase_statuses.items()},
        "retry_counts": state.retry_counts, "metadata": state.metadata,
        "max_retries": state.max_retries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_state(path: Path) -> ProjectState:
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectState(
        project_id=data["project_id"], name=data["name"],
        phases=data["phases"], current_phase=data.get("current_phase"),
        phase_statuses={k: PhaseStatus(v) for k, v in data.get("phase_statuses", {}).items()},
        retry_counts=data.get("retry_counts", {}),
        metadata=data.get("metadata", {}),
        max_retries=data.get("max_retries", 3),
    )
