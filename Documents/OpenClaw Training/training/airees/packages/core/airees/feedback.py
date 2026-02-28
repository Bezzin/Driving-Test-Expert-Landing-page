"""Self-improving feedback loops for outcome-based learning."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class FeedbackConfig:
    evaluate_after: bool = True
    success_criteria: str = "score >= 7"
    on_success: str = "Record what worked in MEMORY.md"
    on_failure: str = "Record what failed and why in MEMORY.md"


@dataclass(frozen=True)
class FeedbackEntry:
    run_id: str
    agent_name: str
    outcome: str
    score: float
    lesson: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class FeedbackLoop:
    entries: list[FeedbackEntry] = field(default_factory=list)

    def record(self, entry: FeedbackEntry) -> FeedbackLoop:
        return FeedbackLoop(entries=[*self.entries, entry])

    def for_agent(self, agent_name: str) -> list[FeedbackEntry]:
        return [e for e in self.entries if e.agent_name == agent_name]

    def to_memory_content(self, agent_name: str) -> str:
        agent_entries = self.for_agent(agent_name)
        if not agent_entries:
            return ""
        lines = [f"# Learned Patterns for {agent_name}", "", "## Successes", ""]
        for e in [x for x in agent_entries if x.outcome == "success"]:
            lines.append(f"- [score={e.score:.1f}] {e.lesson} (run: {e.run_id})")
        lines.extend(["", "## Failures", ""])
        for e in [x for x in agent_entries if x.outcome == "failure"]:
            lines.append(f"- [score={e.score:.1f}] {e.lesson} (run: {e.run_id})")
        return "\n".join(lines)
