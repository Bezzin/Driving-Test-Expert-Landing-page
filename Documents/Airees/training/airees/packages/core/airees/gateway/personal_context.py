"""Personal context loader — reads USER.md to personalise Airees' responses.

The file format mirrors SOUL.md: optional YAML frontmatter (``---`` fences)
followed by free-form markdown content.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


@dataclass(frozen=True)
class PersonalContext:
    """Immutable snapshot of a user's personal context.

    Attributes:
        name: The user's preferred name.
        timezone: IANA timezone string (e.g. ``"Europe/London"``).
        content: Free-form markdown after the frontmatter.
        raw: The original file contents, unprocessed.
    """

    name: str
    timezone: str
    content: str
    raw: str

    def to_prompt(self) -> str:
        """Format the personal context as a system prompt fragment."""
        lines = [
            f"The user's name is {self.name}.",
            f"Their timezone is {self.timezone}.",
        ]
        if self.content:
            lines.append(f"\nUser context:\n{self.content}")
        return "\n".join(lines)


def load_personal_context(path: Path) -> PersonalContext:
    """Load personal context from *path*, returning defaults if missing."""
    if not path.exists():
        log.info("No USER.md found at %s — using defaults", path)
        return PersonalContext(name="User", timezone="UTC", content="", raw="")

    raw = path.read_text(encoding="utf-8")
    log.info("Loaded USER.md from %s (%d bytes)", path, len(raw))
    return _parse_user_md(raw)


def _parse_user_md(raw: str) -> PersonalContext:
    """Parse a USER.md string into a :class:`PersonalContext`."""
    name = "User"
    timezone = "UTC"
    content = raw.strip()

    match = _FRONTMATTER_RE.match(raw)
    if match:
        frontmatter_text = match.group(1)
        content = match.group(2).strip()
        try:
            meta = yaml.safe_load(frontmatter_text)
            if isinstance(meta, dict):
                name = meta.get("name", name)
                timezone = meta.get("timezone", timezone)
        except yaml.YAMLError:
            log.warning("Failed to parse USER.md frontmatter as YAML")

    return PersonalContext(name=name, timezone=timezone, content=content, raw=raw)
