from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileMemoryStore:
    """File-based memory store for per-agent markdown memory files.

    Each agent gets its own directory under base_path, containing markdown
    files following the SOUL.md / USER.md / MEMORY.md memory pattern.

    Directory layout:
        base_path/
            researcher/
                SOUL.md
                MEMORY.md
            planner/
                SOUL.md
                USER.md
    """

    base_path: Path

    def _agent_path(self, agent_name: str) -> Path:
        path = self.base_path / agent_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, agent_name: str, filename: str, content: str) -> None:
        """Write content to an agent's memory file, creating directories as needed."""
        path = self._agent_path(agent_name) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read(self, agent_name: str, filename: str) -> str:
        """Read content from an agent's memory file. Returns empty string if missing."""
        path = self._agent_path(agent_name) / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def append(self, agent_name: str, filename: str, content: str) -> None:
        """Append content to an agent's memory file, creating it if needed."""
        path = self._agent_path(agent_name) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(content)

    def list_files(self, agent_name: str) -> list[str]:
        """List all top-level files in an agent's memory directory. Returns empty list if missing."""
        path = self.base_path / agent_name
        if not path.exists():
            return []
        return [f.name for f in path.iterdir() if f.is_file()]
