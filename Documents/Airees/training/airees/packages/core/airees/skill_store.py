"""Skill storage, search, creation, and versioning."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillDocument:
    """Parsed skill with frontmatter metadata and body content."""

    path: Path
    name: str
    description: str
    version: int
    success_rate: float
    triggers: list[str]
    content: str
    tokens: list[str]
    frontmatter: dict[str, Any]


@dataclass(frozen=True)
class SkillResult:
    """A search result from the skill store."""

    name: str
    path: Path
    score: float
    version: int
    success_rate: float
    content: str


@dataclass
class SkillStore:
    """Manage skill creation, search, and updates.

    Uses BM25 over skill triggers + descriptions for matching.
    """

    skills_dir: Path
    _index: object | None = field(default=None, init=False, repr=False)
    _skills: list[SkillDocument] = field(default_factory=list, init=False, repr=False)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from a skill file."""
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        fm_raw = parts[1].strip()
        body = parts[2].strip()
        fm: dict[str, Any] = {}

        current_key = ""
        current_list: list[str] | None = None

        for line in fm_raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("- ") and current_list is not None:
                current_list.append(stripped[2:].strip())
                continue

            if current_list is not None:
                fm[current_key] = current_list
                current_list = None

            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if val:
                    try:
                        fm[key] = int(val)
                    except ValueError:
                        try:
                            fm[key] = float(val)
                        except ValueError:
                            fm[key] = val.strip('"').strip("'")
                else:
                    current_key = key
                    current_list = []

        if current_list is not None:
            fm[current_key] = current_list

        return fm, body

    def _build_index(self) -> None:
        from rank_bm25 import BM25Okapi

        self._skills = []

        if not self.skills_dir.exists():
            self._index = None
            return

        for md_file in sorted(self.skills_dir.glob("*.md")):
            try:
                raw = md_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            fm, body = self._parse_frontmatter(raw)
            name = fm.get("name", md_file.stem)
            description = fm.get("description", "")
            triggers = fm.get("triggers", [])
            if isinstance(triggers, str):
                triggers = [triggers]

            search_text = f"{name} {description} {' '.join(triggers)} {body}"
            tokens = self._tokenize(search_text)

            if not tokens:
                continue

            self._skills.append(
                SkillDocument(
                    path=md_file,
                    name=name,
                    description=description,
                    version=int(fm.get("version", 1)),
                    success_rate=float(fm.get("success_rate", 0.0)),
                    triggers=triggers,
                    content=body,
                    tokens=tokens,
                    frontmatter=fm,
                )
            )

        if not self._skills:
            self._index = None
            return

        self._index = BM25Okapi([s.tokens for s in self._skills])

    def search(self, query: str, top_k: int = 3) -> list[SkillResult]:
        if self._index is None and not self._skills:
            self._build_index()

        if self._index is None or not self._skills:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores = self._index.get_scores(tokens)
        scored = sorted(zip(scores, self._skills), key=lambda x: x[0], reverse=True)

        query_set = set(tokens)
        results = []
        for score, skill in scored[:top_k]:
            # BM25 with small corpora can produce negative scores even for
            # matching documents (IDF goes negative when N == n).  Fall back
            # to a token-overlap check so we never discard a genuine match.
            has_overlap = bool(query_set & set(skill.tokens))
            if not has_overlap:
                continue
            results.append(
                SkillResult(
                    name=skill.name,
                    path=skill.path,
                    score=max(float(score), 0.001),
                    version=skill.version,
                    success_rate=skill.success_rate,
                    content=skill.content,
                )
            )
        return results

    def invalidate(self) -> None:
        self._index = None
        self._skills = []

    def load_skill(self, name: str) -> str | None:
        path = self.skills_dir / f"{name}.md"
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        _, body = self._parse_frontmatter(raw)
        return body

    def create_skill(
        self,
        *,
        name: str,
        description: str,
        triggers: list[str],
        task_graph: str,
        lessons_learned: str = "",
        quality_gates: str = "",
        known_pitfalls: str = "",
    ) -> Path:
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        triggers_yaml = "\n".join(f"  - {t}" for t in triggers)
        frontmatter = (
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"version: 1\n"
            f"success_rate: 1.0\n"
            f"total_executions: 1\n"
            f"triggers:\n{triggers_yaml}\n"
            f"---\n"
        )

        body_sections = [f"\n# {name.replace('-', ' ').title()} Pipeline\n"]
        body_sections.append(f"\n## Task Graph\n{task_graph}\n")

        if lessons_learned:
            body_sections.append(f"\n## Lessons Learned\n- {lessons_learned}\n")
        if quality_gates:
            body_sections.append(f"\n## Quality Gates\n- {quality_gates}\n")
        if known_pitfalls:
            body_sections.append(f"\n## Known Pitfalls\n- {known_pitfalls}\n")

        path = self.skills_dir / f"{name}.md"
        path.write_text(frontmatter + "\n".join(body_sections), encoding="utf-8")
        self.invalidate()
        return path

    def update_skill(
        self,
        *,
        name: str,
        lessons_learned: str = "",
        known_pitfalls: str = "",
        task_graph: str = "",
        success: bool | None = None,
    ) -> Path:
        path = self.skills_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Skill not found: {name}")

        raw = path.read_text(encoding="utf-8")
        fm, body = self._parse_frontmatter(raw)

        old_version = int(fm.get("version", 1))
        new_version = old_version + 1

        total_exec = int(fm.get("total_executions", 0)) + 1
        old_rate = float(fm.get("success_rate", 0.0))
        if success is not None:
            successes = round(old_rate * (total_exec - 1)) + (1 if success else 0)
            new_rate = successes / total_exec
        else:
            new_rate = old_rate

        fm["version"] = new_version
        fm["total_executions"] = total_exec
        fm["success_rate"] = round(new_rate, 2)

        fm_lines = ["---"]
        for key, val in fm.items():
            if isinstance(val, list):
                fm_lines.append(f"{key}:")
                for item in val:
                    fm_lines.append(f"  - {item}")
            else:
                fm_lines.append(f"{key}: {val}")
        fm_lines.append("---")

        if lessons_learned:
            if "## Lessons Learned" in body:
                body = body.replace(
                    "## Lessons Learned",
                    f"## Lessons Learned\n- {lessons_learned}",
                )
            else:
                body += f"\n\n## Lessons Learned\n- {lessons_learned}\n"

        if known_pitfalls:
            if "## Known Pitfalls" in body:
                body = body.replace(
                    "## Known Pitfalls",
                    f"## Known Pitfalls\n- {known_pitfalls}",
                )
            else:
                body += f"\n\n## Known Pitfalls\n- {known_pitfalls}\n"

        if task_graph:
            if "## Task Graph" in body:
                body = re.sub(
                    r"## Task Graph\n.*?(?=\n## |\Z)",
                    f"## Task Graph\n{task_graph}\n",
                    body,
                    flags=re.DOTALL,
                )
            else:
                body = f"## Task Graph\n{task_graph}\n\n" + body

        path.write_text("\n".join(fm_lines) + "\n\n" + body, encoding="utf-8")
        self.invalidate()
        return path
