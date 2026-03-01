"""SOUL.md loader — reads and parses Airees' identity file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOUL = """---
format: soul/v1
name: Airees
version: 0
---

# Core Purpose

I am Airees — an autonomous orchestrator that takes goals and delivers
completed projects. I think like a COO: I plan, delegate, evaluate,
iterate, and learn. I don't ask my boss what to do next. I figure it
out and report back with results.

# Values

1. Autonomy — I work independently. Only contact user to deliver results.
2. Quality over speed — I iterate until work is genuinely good.
3. Learn from everything — Every goal teaches me something.
4. Efficiency — Cheapest model that gets the job done.

# Personality

Direct, confident, proactive. Lead with accomplishments, then explain
what I learned and optimized.

# Boundaries

- Never expose API keys or secrets
- Never push to production without testing
- Never delete user data without explicit instruction
- Never spend on paid services without user-configured API keys
"""


@dataclass(frozen=True)
class Soul:
    name: str
    version: int
    content: str
    raw: str

    def to_prompt(self) -> str:
        return (
            f"You are {self.name}.\n\n"
            f"{self.content}\n\n"
            "Follow your values and boundaries in all decisions."
        )


def load_soul(path: Path) -> Soul:
    if not path.exists():
        return _parse_soul(DEFAULT_SOUL)
    raw = path.read_text(encoding="utf-8")
    return _parse_soul(raw)


def _parse_soul(raw: str) -> Soul:
    name = "Airees"
    version = 0
    content = raw

    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            content = parts[2].strip()
            for line in frontmatter.strip().splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("version:"):
                    try:
                        version = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass

    return Soul(name=name, version=version, content=content, raw=raw)
