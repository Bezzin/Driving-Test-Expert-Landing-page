"""Decision document -- structured reasoning artifact for each run."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DecisionEntry:
    phase: str
    agent: str
    decision: str
    reasoning: str
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class DecisionDocument:
    project_id: str
    title: str
    entries: list[DecisionEntry] = field(default_factory=list)

    def add_entry(self, entry: DecisionEntry) -> DecisionDocument:
        return DecisionDocument(
            project_id=self.project_id,
            title=self.title,
            entries=[*self.entries, entry],
        )

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"**Project ID:** {self.project_id}", ""]
        for entry in self.entries:
            confidence_pct = f"{entry.confidence * 100:.0f}%"
            lines.extend([
                f"## {entry.phase}", "",
                f"**Agent:** {entry.agent}  ",
                f"**Confidence:** {confidence_pct}  ",
                f"**Time:** {entry.timestamp}", "",
                f"**Decision:** {entry.decision}", "",
                f"**Reasoning:** {entry.reasoning}", "",
                "---", "",
            ])
        return "\n".join(lines)
