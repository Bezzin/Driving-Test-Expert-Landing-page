# Phase 4: Memory & Learning System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the training corpus, skills system, progressive compression, and self-reflection into the live orchestration pipeline so Airees can search knowledge, create/reuse skills, manage context, and evolve.

**Architecture:** Four new modules (corpus_search, skill_store, context_compressor, brain/reflection) integrated into BrainOrchestrator and worker_builder. BM25 keyword search over training corpus and skills. Progressive 4-stage context compression in Runner. Soul self-reflection with genesis hash guard.

**Tech Stack:** Python 3.12, rank-bm25, aiosqlite (existing), pyyaml (existing), pytest-asyncio

---

### Task 1: Add New Event Types

**Files:**
- Modify: `packages/core/airees/events.py:41`
- Test: `packages/core/tests/test_events.py`

**Step 1: Write the failing test**

Add to the existing test file:

```python
# In tests/test_events.py — add these test cases

def test_corpus_search_event_type():
    assert EventType.CORPUS_SEARCH.value == "corpus.search"

def test_skill_matched_event_type():
    assert EventType.SKILL_MATCHED.value == "skill.matched"

def test_skill_created_event_type():
    assert EventType.SKILL_CREATED.value == "skill.created"

def test_skill_updated_event_type():
    assert EventType.SKILL_UPDATED.value == "skill.updated"

def test_context_compressed_event_type():
    assert EventType.CONTEXT_COMPRESSED.value == "context.compressed"

def test_soul_updated_event_type():
    assert EventType.SOUL_UPDATED.value == "soul.updated"

def test_reflection_triggered_event_type():
    assert EventType.REFLECTION_TRIGGERED.value == "reflection.triggered"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_events.py -v -k "corpus_search or skill_matched or skill_created or skill_updated or context_compressed or soul_updated or reflection_triggered"`
Expected: FAIL with AttributeError — enum members don't exist yet

**Step 3: Write minimal implementation**

In `events.py`, add these 7 members after line 41 (after `FEEDBACK_RECORDED`):

```python
    CORPUS_SEARCH = "corpus.search"
    SKILL_MATCHED = "skill.matched"
    SKILL_CREATED = "skill.created"
    SKILL_UPDATED = "skill.updated"
    CONTEXT_COMPRESSED = "context.compressed"
    SOUL_UPDATED = "soul.updated"
    REFLECTION_TRIGGERED = "reflection.triggered"
```

**Step 4: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_events.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/events.py packages/core/tests/test_events.py
git commit -m "feat: add Phase 4 event types for corpus, skills, compression, reflection"
```

---

### Task 2: Add `rank-bm25` Dependency

**Files:**
- Modify: `packages/core/pyproject.toml:7`

**Step 1: Add dependency**

In `pyproject.toml`, add `"rank-bm25>=0.2.2"` to the `dependencies` array after `"tavily-python>=0.5.0"`:

```toml
dependencies = [
    "anthropic>=0.52.0",
    "httpx>=0.27.0",
    "pydantic>=2.10.0",
    "aiosqlite>=0.20.0",
    "click>=8.1.0",
    "tavily-python>=0.5.0",
    "rank-bm25>=0.2.2",
]
```

**Step 2: Install**

Run: `cd packages/core && pip install rank-bm25>=0.2.2`

**Step 3: Verify import works**

Run: `python -c "from rank_bm25 import BM25Okapi; print('OK')"`
Expected: OK

**Step 4: Commit**

```bash
git add packages/core/pyproject.toml
git commit -m "chore: add rank-bm25 dependency for corpus and skill search"
```

---

### Task 3: Create Corpus Search Engine

**Files:**
- Create: `packages/core/airees/corpus_search.py`
- Test: `packages/core/tests/test_corpus_search.py`

**Step 1: Write the failing tests**

Create `tests/test_corpus_search.py`:

```python
"""Tests for corpus search engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from airees.corpus_search import CorpusDocument, CorpusResult, CorpusSearchEngine


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    """Create a minimal corpus directory with sample files."""
    cat1 = tmp_path / "01-fundamentals" / "concepts"
    cat1.mkdir(parents=True)
    (cat1 / "01-agent-basics.md").write_text(
        "# Agent Basics\n\n## Summary\n\nAgents use tools to accomplish tasks.\n"
        "## Key Concepts\n- Tool use\n- Planning\n- Evaluation\n",
        encoding="utf-8",
    )

    cat2 = tmp_path / "02-prompts" / "patterns"
    cat2.mkdir(parents=True)
    (cat2 / "01-chain-of-thought.md").write_text(
        "# Chain of Thought\n\n## Summary\n\nChain of thought prompting improves reasoning.\n"
        "## Key Concepts\n- Step-by-step reasoning\n- Self-consistency\n",
        encoding="utf-8",
    )

    cat3 = tmp_path / "07-security" / "hardening"
    cat3.mkdir(parents=True)
    (cat3 / "01-input-validation.md").write_text(
        "# Input Validation\n\n## Summary\n\nAlways validate user input to prevent injection.\n"
        "## Key Concepts\n- SQL injection\n- XSS prevention\n- Sanitization\n",
        encoding="utf-8",
    )
    return tmp_path


def test_engine_builds_index(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("agent tools", top_k=3)
    assert len(results) > 0
    assert all(isinstance(r, CorpusResult) for r in results)


def test_search_returns_relevant_results(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("security input validation injection", top_k=1)
    assert len(results) == 1
    assert "security" in results[0].category.lower() or "validation" in results[0].title.lower()


def test_search_respects_top_k(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("concepts", top_k=2)
    assert len(results) <= 2


def test_empty_corpus(tmp_path: Path):
    engine = CorpusSearchEngine(corpus_dir=tmp_path)
    results = engine.search("anything", top_k=3)
    assert results == []


def test_corpus_document_fields(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("agent", top_k=1)
    assert len(results) == 1
    r = results[0]
    assert r.path is not None
    assert r.title != ""
    assert r.score > 0
    assert r.excerpt != ""


def test_index_cached_across_searches(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    engine.search("agent", top_k=1)
    # Second search should reuse the cached index (not rebuild)
    results = engine.search("security", top_k=1)
    assert len(results) > 0
    # Verify internal index is populated
    assert engine._index is not None
    assert len(engine._documents) == 3


def test_format_results(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("agent tools", top_k=2)
    formatted = engine.format_results(results)
    assert "###" in formatted  # Markdown headers
    assert "Category:" in formatted
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_corpus_search.py -v`
Expected: FAIL — ModuleNotFoundError: No module named 'airees.corpus_search'

**Step 3: Write minimal implementation**

Create `packages/core/airees/corpus_search.py`:

```python
"""BM25 keyword search over the Airees training corpus."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CorpusDocument:
    """A single document from the training corpus."""

    path: Path
    title: str
    category: str
    content: str
    tokens: list[str]


@dataclass(frozen=True)
class CorpusResult:
    """A search result from the corpus."""

    path: Path
    title: str
    category: str
    score: float
    excerpt: str


@dataclass
class CorpusSearchEngine:
    """BM25 keyword search over markdown training files.

    The index is built lazily on the first search call and cached
    for the lifetime of the process.

    Attributes:
        corpus_dir: Root directory of the training corpus.
    """

    corpus_dir: Path
    _index: object | None = field(default=None, init=False, repr=False)
    _documents: list[CorpusDocument] = field(default_factory=list, init=False, repr=False)

    def _tokenize(self, text: str) -> list[str]:
        """Whitespace + punctuation tokenizer for BM25."""
        return re.findall(r"\w+", text.lower())

    def _extract_title(self, content: str) -> str:
        """Extract the first markdown heading as title."""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return "Untitled"

    def _extract_category(self, path: Path) -> str:
        """Extract category from the file path relative to corpus_dir."""
        try:
            rel = path.relative_to(self.corpus_dir)
            parts = rel.parts
            return parts[0] if parts else "unknown"
        except ValueError:
            return "unknown"

    def _build_index(self) -> None:
        """Scan corpus_dir for .md files and build a BM25 index."""
        from rank_bm25 import BM25Okapi

        self._documents = []

        if not self.corpus_dir.exists():
            self._index = None
            return

        for md_file in sorted(self.corpus_dir.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            title = self._extract_title(content)
            category = self._extract_category(md_file)
            tokens = self._tokenize(f"{title} {content}")

            if not tokens:
                continue

            self._documents.append(
                CorpusDocument(
                    path=md_file,
                    title=title,
                    category=category,
                    content=content,
                    tokens=tokens,
                )
            )

        if not self._documents:
            self._index = None
            return

        corpus_tokenized = [doc.tokens for doc in self._documents]
        self._index = BM25Okapi(corpus_tokenized)

    def search(self, query: str, top_k: int = 3) -> list[CorpusResult]:
        """Search the corpus and return the top-k most relevant results.

        Args:
            query: The search query string.
            top_k: Maximum number of results to return.

        Returns:
            A list of CorpusResult objects sorted by relevance score.
        """
        if self._index is None and not self._documents:
            self._build_index()

        if self._index is None or not self._documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = self._index.get_scores(query_tokens)

        scored_docs = sorted(
            zip(scores, self._documents),
            key=lambda x: x[0],
            reverse=True,
        )

        results = []
        for score, doc in scored_docs[:top_k]:
            if score <= 0:
                continue
            excerpt = doc.content[:500].strip()
            results.append(
                CorpusResult(
                    path=doc.path,
                    title=doc.title,
                    category=doc.category,
                    score=float(score),
                    excerpt=excerpt,
                )
            )
        return results

    def format_results(self, results: list[CorpusResult]) -> str:
        """Format search results as markdown for injection into prompts.

        Args:
            results: The list of CorpusResult objects.

        Returns:
            A markdown-formatted string with titles, categories, and excerpts.
        """
        if not results:
            return "No relevant training material found."

        sections = []
        for r in results:
            sections.append(
                f"### {r.title}\n"
                f"**Category:** {r.category} | **Relevance:** {r.score:.2f}\n\n"
                f"{r.excerpt}\n"
            )
        return "\n---\n\n".join(sections)
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_corpus_search.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/corpus_search.py packages/core/tests/test_corpus_search.py
git commit -m "feat: add BM25 corpus search engine over training files"
```

---

### Task 4: Create Skill Store

**Files:**
- Create: `packages/core/airees/skill_store.py`
- Test: `packages/core/tests/test_skill_store.py`

**Step 1: Write the failing tests**

Create `tests/test_skill_store.py`:

```python
"""Tests for the skill store — create, search, update skills."""
from __future__ import annotations

from pathlib import Path

import pytest

from airees.skill_store import SkillDocument, SkillResult, SkillStore


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """Create a skills directory with a sample skill."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "web-scraper.md").write_text(
        "---\n"
        "name: web-scraper\n"
        "description: Scrape and parse web pages for data extraction\n"
        "version: 2\n"
        "success_rate: 0.9\n"
        "triggers:\n"
        "  - scrape a website\n"
        "  - extract data from web\n"
        "tools_required:\n"
        "  - web_search\n"
        "  - web_extract\n"
        "---\n\n"
        "# Web Scraper Pipeline\n\n"
        "## Task Graph\n"
        "1. Identify target URLs\n"
        "2. Fetch pages\n"
        "3. Parse content\n\n"
        "## Lessons Learned\n"
        "- Use retry logic for flaky sites\n\n"
        "## Known Pitfalls\n"
        "- Respect robots.txt\n",
        encoding="utf-8",
    )
    return skills


def test_search_finds_matching_skill(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    results = store.search("scrape a website to extract data")
    assert len(results) >= 1
    assert results[0].name == "web-scraper"


def test_search_returns_skill_result_fields(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    results = store.search("web scraper", top_k=1)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, SkillResult)
    assert r.name == "web-scraper"
    assert r.version == 2
    assert r.success_rate == 0.9
    assert r.score > 0
    assert "Task Graph" in r.content


def test_search_empty_dir(tmp_path: Path):
    store = SkillStore(skills_dir=tmp_path)
    results = store.search("anything")
    assert results == []


def test_create_skill(tmp_path: Path):
    store = SkillStore(skills_dir=tmp_path)
    store.create_skill(
        name="api-builder",
        description="Build REST APIs with FastAPI",
        triggers=["build an api", "create rest endpoint"],
        task_graph="1. Design schema\n2. Implement routes\n3. Test",
        lessons_learned="Use Pydantic for validation",
        quality_gates="All endpoints return 200",
        known_pitfalls="Don't forget CORS",
    )
    path = tmp_path / "api-builder.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "name: api-builder" in content
    assert "version: 1" in content
    assert "success_rate: 1.0" in content
    assert "build an api" in content
    assert "## Task Graph" in content
    assert "Use Pydantic for validation" in content


def test_update_skill(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    store.update_skill(
        name="web-scraper",
        lessons_learned="Also handle JavaScript-rendered pages",
        known_pitfalls="Watch for rate limits",
    )
    content = (skills_dir / "web-scraper.md").read_text(encoding="utf-8")
    assert "version: 3" in content
    assert "JavaScript-rendered" in content
    assert "rate limits" in content
    # Original content preserved
    assert "Respect robots.txt" in content
    assert "Use retry logic" in content


def test_update_skill_bumps_execution_count(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    store.update_skill(name="web-scraper", success=True)
    content = (skills_dir / "web-scraper.md").read_text(encoding="utf-8")
    assert "version: 3" in content


def test_update_nonexistent_skill_raises(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    with pytest.raises(FileNotFoundError):
        store.update_skill(name="nonexistent")


def test_invalidate_rebuilds_index(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    store.search("web scraper")
    assert store._index is not None
    store.invalidate()
    assert store._index is None


def test_load_skill_content(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    content = store.load_skill("web-scraper")
    assert "Web Scraper Pipeline" in content
    assert "Task Graph" in content


def test_load_nonexistent_skill_returns_none(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    content = store.load_skill("nonexistent")
    assert content is None
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_skill_store.py -v`
Expected: FAIL — ModuleNotFoundError: No module named 'airees.skill_store'

**Step 3: Write minimal implementation**

Create `packages/core/airees/skill_store.py`:

```python
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
        """Parse YAML frontmatter from a skill file.

        Returns (frontmatter_dict, body_content).
        """
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
                    # Try numeric conversion
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
        """Scan skills_dir and build a BM25 index."""
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
        """Search skills by query, return top-k matches."""
        if self._index is None and not self._skills:
            self._build_index()

        if self._index is None or not self._skills:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores = self._index.get_scores(tokens)
        scored = sorted(zip(scores, self._skills), key=lambda x: x[0], reverse=True)

        results = []
        for score, skill in scored[:top_k]:
            if score <= 0:
                continue
            results.append(
                SkillResult(
                    name=skill.name,
                    path=skill.path,
                    score=float(score),
                    version=skill.version,
                    success_rate=skill.success_rate,
                    content=skill.content,
                )
            )
        return results

    def invalidate(self) -> None:
        """Force index rebuild on next search."""
        self._index = None
        self._skills = []

    def load_skill(self, name: str) -> str | None:
        """Load the full content of a skill by name. Returns None if not found."""
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
        """Create a new skill file with YAML frontmatter.

        Returns the path to the created skill file.
        """
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
        """Update an existing skill: bump version, append learnings.

        Raises FileNotFoundError if the skill doesn't exist.
        """
        path = self.skills_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Skill not found: {name}")

        raw = path.read_text(encoding="utf-8")
        fm, body = self._parse_frontmatter(raw)

        # Bump version
        old_version = int(fm.get("version", 1))
        new_version = old_version + 1

        # Update execution stats
        total_exec = int(fm.get("total_executions", 0)) + 1
        old_rate = float(fm.get("success_rate", 0.0))
        if success is not None:
            successes = round(old_rate * (total_exec - 1)) + (1 if success else 0)
            new_rate = successes / total_exec
        else:
            new_rate = old_rate

        # Rebuild frontmatter
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

        # Append new lessons and pitfalls to body
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
                # Replace task graph section
                import re
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
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_skill_store.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/skill_store.py packages/core/tests/test_skill_store.py
git commit -m "feat: add skill store with BM25 search, create, and update"
```

---

### Task 5: Create Context Compressor

**Files:**
- Create: `packages/core/airees/context_compressor.py`
- Test: `packages/core/tests/test_context_compressor.py`

**Step 1: Write the failing tests**

Create `tests/test_context_compressor.py`:

```python
"""Tests for progressive context compression."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from airees.context_budget import ContextBudget
from airees.context_compressor import ContextCompressor


def _mock_router(summary_text: str = "Summary of output."):
    """Return a mock router whose create_message returns a text block."""
    router = AsyncMock()
    block = MagicMock()
    block.type = "text"
    block.text = summary_text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(input_tokens=50, output_tokens=20)
    router.create_message.return_value = response
    return router


def test_detect_stage_no_compression():
    budget = ContextBudget(max_tokens=1000, used_tokens=500)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 0


def test_detect_stage_1():
    budget = ContextBudget(max_tokens=1000, used_tokens=650)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 1


def test_detect_stage_2():
    budget = ContextBudget(max_tokens=1000, used_tokens=780)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 2


def test_detect_stage_3():
    budget = ContextBudget(max_tokens=1000, used_tokens=870)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 3


def test_detect_stage_4():
    budget = ContextBudget(max_tokens=1000, used_tokens=960)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    assert compressor.detect_stage() == 4


@pytest.mark.asyncio
async def test_compress_stage_0_passthrough():
    budget = ContextBudget(max_tokens=1000, used_tokens=100)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Do task"},
        {"role": "assistant", "content": "Here's the full output of the task."},
    ]
    result = await compressor.compress(messages, stage=0)
    assert result == messages  # No compression


@pytest.mark.asyncio
async def test_compress_stage_1_summarizes():
    router = _mock_router("Summarized output.")
    budget = ContextBudget(max_tokens=1000, used_tokens=650)
    compressor = ContextCompressor(router=router, budget=budget)
    messages = [
        {"role": "user", "content": "Do task 1"},
        {"role": "assistant", "content": "A" * 500},
        {"role": "user", "content": "Do task 2"},
        {"role": "assistant", "content": "B" * 500},
    ]
    result = await compressor.compress(messages, stage=1)
    # Assistant messages should be summarized
    assert len(result) == len(messages)
    assert "Summarized" in result[1]["content"] or len(result[1]["content"]) < 500


@pytest.mark.asyncio
async def test_compress_stage_4_emergency():
    budget = ContextBudget(max_tokens=1000, used_tokens=960)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    messages = [
        {"role": "user", "content": "Task 1"},
        {"role": "assistant", "content": "Output 1"},
        {"role": "user", "content": "Task 2"},
        {"role": "assistant", "content": "Output 2"},
        {"role": "user", "content": "Task 3"},
        {"role": "assistant", "content": "Output 3"},
    ]
    result = await compressor.compress(messages, stage=4)
    # Emergency: only last user + last assistant
    assert len(result) <= 2


def test_update_budget():
    budget = ContextBudget(max_tokens=1000, used_tokens=500)
    compressor = ContextCompressor(router=AsyncMock(), budget=budget)
    compressor.update_budget(ContextBudget(max_tokens=1000, used_tokens=700))
    assert compressor.budget.used_tokens == 700
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_context_compressor.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write minimal implementation**

Create `packages/core/airees/context_compressor.py`:

```python
"""Progressive context compression for long-running goals.

Implements a 4-stage compression cascade that activates based on
ContextBudget usage:

- Stage 0 (<60%): No compression
- Stage 1 (60-74%): Summarize completed assistant outputs via Haiku
- Stage 2 (75-84%): Collapse completed message pairs into one-liners
- Stage 3 (85-94%): Checkpoint — keep only recent messages
- Stage 4 (95%+): Emergency — keep only the last exchange
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from airees.context_budget import ContextBudget
from airees.router.types import ModelConfig


@dataclass
class ContextCompressor:
    """Compress conversation messages based on context budget usage.

    Attributes:
        router: ModelRouter for Haiku summarization calls.
        budget: Current ContextBudget tracking token usage.
    """

    router: Any  # ModelRouter
    budget: ContextBudget

    _THRESHOLDS = (60.0, 75.0, 85.0, 95.0)

    def detect_stage(self) -> int:
        """Return the compression stage (0-4) based on budget usage."""
        pct = self.budget.usage_percent
        for i, threshold in enumerate(self._THRESHOLDS):
            if pct < threshold:
                return i
        return 4

    def update_budget(self, budget: ContextBudget) -> None:
        """Update the tracked budget after token consumption."""
        self.budget = budget

    async def compress(
        self,
        messages: list[dict[str, Any]],
        stage: int,
    ) -> list[dict[str, Any]]:
        """Compress messages according to the given stage.

        Args:
            messages: The current conversation message list.
            stage: Compression stage (0-4).

        Returns:
            A (possibly shorter) list of messages.
        """
        if stage == 0 or not messages:
            return list(messages)

        if stage >= 4:
            return self._emergency_trim(messages)

        if stage >= 3:
            return self._checkpoint_trim(messages)

        if stage >= 2:
            return self._collapse_pairs(messages)

        # Stage 1: summarize assistant outputs
        return await self._summarize_outputs(messages)

    async def _summarize_outputs(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Stage 1: Replace long assistant messages with Haiku summaries."""
        result = []
        for msg in messages:
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                content = msg["content"]
                if len(content) > 200:
                    summary = await self._haiku_summarize(content)
                    result.append({"role": "assistant", "content": f"[Summarized] {summary}"})
                else:
                    result.append(msg)
            else:
                result.append(msg)
        return result

    def _collapse_pairs(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Stage 2: Collapse all but the last 2 message pairs into one-liners."""
        if len(messages) <= 4:
            return list(messages)

        collapsed = []
        # Keep last 4 messages (2 pairs) intact
        earlier = messages[:-4]
        recent = messages[-4:]

        summaries = []
        for msg in earlier:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, str):
                preview = content[:80].replace("\n", " ")
            else:
                preview = str(content)[:80]
            summaries.append(f"[{role}] {preview}")

        if summaries:
            collapsed.append({
                "role": "user",
                "content": "[Compressed earlier context]\n" + "\n".join(summaries),
            })

        collapsed.extend(recent)
        return collapsed

    def _checkpoint_trim(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Stage 3: Keep only the last 2 messages."""
        if len(messages) <= 2:
            return list(messages)
        return list(messages[-2:])

    def _emergency_trim(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Stage 4: Keep only the last user message and last assistant message."""
        last_user = None
        last_assistant = None
        for msg in reversed(messages):
            if msg.get("role") == "user" and last_user is None:
                last_user = msg
            elif msg.get("role") == "assistant" and last_assistant is None:
                last_assistant = msg
            if last_user and last_assistant:
                break

        result = []
        if last_user:
            result.append(last_user)
        if last_assistant:
            result.append(last_assistant)
        return result if result else list(messages[-1:])

    async def _haiku_summarize(self, text: str) -> str:
        """Use Haiku to compress text into a 2-line summary."""
        model = ModelConfig(model_id="claude-haiku-4-5-20251001")
        response = await self.router.create_message(
            model=model,
            system="Summarize this text in exactly 2 lines. Preserve key facts and results.",
            messages=[{"role": "user", "content": text}],
        )
        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return text[:200]
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_context_compressor.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/context_compressor.py packages/core/tests/test_context_compressor.py
git commit -m "feat: add progressive context compressor with 4-stage cascade"
```

---

### Task 6: Add Brain Reflection and Soul Update

**Files:**
- Create: `packages/core/airees/brain/reflection.py`
- Modify: `packages/core/airees/soul.py`
- Test: `packages/core/tests/test_reflection.py`

**Step 1: Write the failing tests**

Create `tests/test_reflection.py`:

```python
"""Tests for brain reflection and soul updates."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from airees.brain.reflection import (
    compute_genesis_hash,
    update_soul_file,
    write_daily_log,
)
from airees.soul import load_soul


@pytest.fixture
def soul_path(tmp_path: Path) -> Path:
    """Create a SOUL.md file for testing."""
    path = tmp_path / "SOUL.md"
    path.write_text(
        "---\n"
        "format: soul/v1\n"
        "name: Airees\n"
        "version: 1\n"
        "---\n\n"
        "# Core Purpose\n\n"
        "I am Airees — an autonomous orchestrator.\n\n"
        "# Values\n\n1. Autonomy\n2. Quality\n\n"
        "# Capabilities\n\n"
        "- Skills mastered: 0\n"
        "- Goals completed: 0\n\n"
        "# Strategy\n\n"
        "- Current focus: Learning\n",
        encoding="utf-8",
    )
    return path


def test_compute_genesis_hash(soul_path: Path):
    h = compute_genesis_hash(soul_path)
    assert isinstance(h, str)
    assert len(h) == 64  # sha256 hex


def test_update_soul_bumps_version(soul_path: Path):
    update_soul_file(
        soul_path,
        capabilities_update={"goals_completed": 5},
    )
    soul = load_soul(soul_path)
    assert soul.version == 2


def test_update_soul_capabilities(soul_path: Path):
    update_soul_file(
        soul_path,
        capabilities_update={"skills_mastered": 3, "goals_completed": 7},
    )
    content = soul_path.read_text(encoding="utf-8")
    assert "Skills mastered: 3" in content
    assert "Goals completed: 7" in content


def test_update_soul_strategy(soul_path: Path):
    update_soul_file(
        soul_path,
        strategy_update="Focus on SaaS applications",
    )
    content = soul_path.read_text(encoding="utf-8")
    assert "Focus on SaaS applications" in content


def test_update_soul_appends_lesson(soul_path: Path):
    update_soul_file(
        soul_path,
        lesson="Clerk is better than NextAuth for SaaS",
    )
    content = soul_path.read_text(encoding="utf-8")
    assert "Clerk is better than NextAuth" in content


def test_write_daily_log(tmp_path: Path):
    memory_dir = tmp_path / "memory"
    write_daily_log(
        memory_dir=memory_dir,
        goal_id="goal-123",
        iterations=2,
        skills_created=["api-builder"],
        total_cost=1.50,
        key_decisions=["Used FastAPI over Flask"],
        lesson="FastAPI is faster for async APIs",
    )
    logs = list(memory_dir.glob("*.md"))
    assert len(logs) == 1
    content = logs[0].read_text(encoding="utf-8")
    assert "goal-123" in content
    assert "Iterations:** 2" in content
    assert "api-builder" in content
    assert "1.50" in content or "1.5" in content


def test_write_daily_log_appends(tmp_path: Path):
    memory_dir = tmp_path / "memory"
    write_daily_log(memory_dir=memory_dir, goal_id="goal-1")
    write_daily_log(memory_dir=memory_dir, goal_id="goal-2")
    logs = list(memory_dir.glob("*.md"))
    assert len(logs) == 1  # Same day, same file
    content = logs[0].read_text(encoding="utf-8")
    assert "goal-1" in content
    assert "goal-2" in content
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_reflection.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write minimal implementation**

Create `packages/core/airees/brain/reflection.py`:

```python
"""Brain self-reflection — update SOUL.md and write daily memory logs."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path


def compute_genesis_hash(soul_path: Path) -> str:
    """Compute SHA-256 of the Core Purpose section in SOUL.md.

    This hash anchors the identity. If the Core Purpose drifts,
    the reflection system can detect and re-anchor it.
    """
    if not soul_path.exists():
        return ""
    content = soul_path.read_text(encoding="utf-8")
    match = re.search(
        r"# Core Purpose\s*\n(.*?)(?=\n# |\Z)",
        content,
        flags=re.DOTALL,
    )
    purpose = match.group(1).strip() if match else ""
    return hashlib.sha256(purpose.encode("utf-8")).hexdigest()


def update_soul_file(
    soul_path: Path,
    *,
    capabilities_update: dict[str, int] | None = None,
    strategy_update: str | None = None,
    lesson: str | None = None,
) -> None:
    """Update SOUL.md with new capabilities, strategy, and lessons.

    Bumps the version number in the YAML frontmatter.
    """
    if not soul_path.exists():
        return

    content = soul_path.read_text(encoding="utf-8")

    # Bump version in frontmatter
    content = re.sub(
        r"^(version:\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Update capabilities counters
    if capabilities_update:
        for key, value in capabilities_update.items():
            label = key.replace("_", " ").capitalize()
            content = re.sub(
                rf"(- {label}:\s*)\d+",
                rf"\g<1>{value}",
                content,
                flags=re.IGNORECASE,
            )

    # Update strategy section
    if strategy_update:
        content = re.sub(
            r"(# Strategy\s*\n).*?(?=\n# |\Z)",
            rf"\g<1>- Current focus: {strategy_update}\n",
            content,
            flags=re.DOTALL,
        )

    # Append lesson
    if lesson:
        if "# Lessons" in content:
            content = content.replace(
                "# Lessons",
                f"# Lessons\n- {lesson}",
            )
        else:
            content = content.rstrip() + f"\n\n# Lessons\n\n- {lesson}\n"

    soul_path.write_text(content, encoding="utf-8")


def write_daily_log(
    memory_dir: Path,
    goal_id: str,
    iterations: int = 0,
    skills_created: list[str] | None = None,
    total_cost: float = 0.0,
    key_decisions: list[str] | None = None,
    lesson: str = "",
) -> Path:
    """Append a goal completion entry to the daily memory log.

    Creates ``memory_dir/{date}.md`` if it doesn't exist.
    """
    memory_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = memory_dir / f"{date_str}.md"

    skills_list = ", ".join(skills_created) if skills_created else "none"
    decisions_list = (
        "\n".join(f"  - {d}" for d in key_decisions) if key_decisions else "  - none"
    )

    entry = (
        f"\n## Goal: {goal_id}\n"
        f"- **Completed:** {datetime.now(timezone.utc).isoformat()}\n"
        f"- **Iterations:** {iterations}\n"
        f"- **Skills created/updated:** {skills_list}\n"
        f"- **Cost:** ${total_cost:.2f}\n"
        f"- **Key decisions:**\n{decisions_list}\n"
        f"- **Lesson:** {lesson}\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return log_path
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_reflection.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/brain/reflection.py packages/core/tests/test_reflection.py
git commit -m "feat: add brain reflection with soul update and daily memory logs"
```

---

### Task 7: Add Brain Tools for Corpus, Skills, and Reflection

**Files:**
- Modify: `packages/core/airees/brain/tools.py`
- Test: `packages/core/tests/test_brain_tools.py`

**Step 1: Write the failing test**

Add to `tests/test_brain_tools.py`:

```python
# Add these tests to the existing test file

from airees.brain.tools import get_brain_tools


def test_brain_tools_include_search_corpus():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "search_corpus" in names


def test_brain_tools_include_search_skills():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "search_skills" in names


def test_brain_tools_include_create_skill():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "create_skill" in names


def test_brain_tools_include_update_skill():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "update_skill" in names


def test_brain_tools_include_update_soul():
    tools = get_brain_tools()
    names = [t.name for t in tools]
    assert "update_soul" in names


def test_search_corpus_tool_schema():
    tools = get_brain_tools()
    tool = next(t for t in tools if t.name == "search_corpus")
    assert "query" in tool.input_schema["properties"]
    assert "query" in tool.input_schema["required"]


def test_create_skill_tool_schema():
    tools = get_brain_tools()
    tool = next(t for t in tools if t.name == "create_skill")
    props = tool.input_schema["properties"]
    assert "name" in props
    assert "description" in props
    assert "triggers" in props
    assert "task_graph" in props
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_brain_tools.py -v -k "search_corpus or search_skills or create_skill or update_skill or update_soul"`
Expected: FAIL — assertions fail

**Step 3: Write minimal implementation**

In `brain/tools.py`, add 5 new tool definitions to the list returned by `get_brain_tools()`. Add them after the existing `message_user` tool (before the closing `]`):

```python
        ToolDefinition(
            name="search_corpus",
            description="Search the training corpus for best practices and reference material.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for finding relevant training material",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="search_skills",
            description="Search for existing skills that match this goal.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Goal description to match against skills",
                    },
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="create_skill",
            description="Create a new skill from a successful goal execution.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name (kebab-case)",
                    },
                    "description": {
                        "type": "string",
                        "description": "What this skill does",
                    },
                    "triggers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Goal phrases that should match this skill",
                    },
                    "task_graph": {
                        "type": "string",
                        "description": "Markdown task graph with dependencies",
                    },
                    "lessons_learned": {"type": "string"},
                    "quality_gates": {"type": "string"},
                    "known_pitfalls": {"type": "string"},
                },
                "required": ["name", "description", "triggers", "task_graph"],
            },
        ),
        ToolDefinition(
            name="update_skill",
            description="Update an existing skill with improvements from the latest execution.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Existing skill name",
                    },
                    "lessons_learned": {"type": "string"},
                    "known_pitfalls": {"type": "string"},
                    "task_graph": {"type": "string"},
                },
                "required": ["name"],
            },
        ),
        ToolDefinition(
            name="update_soul",
            description="Reflect on execution and update SOUL.md.",
            input_schema={
                "type": "object",
                "properties": {
                    "capabilities_update": {
                        "type": "object",
                        "properties": {
                            "skills_mastered": {"type": "integer"},
                            "goals_completed": {"type": "integer"},
                            "total_iterations": {"type": "integer"},
                        },
                    },
                    "strategy_update": {"type": "string"},
                    "lesson": {"type": "string"},
                },
            },
        ),
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_brain_tools.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/brain/tools.py packages/core/tests/test_brain_tools.py
git commit -m "feat: add brain tools for corpus search, skills, and soul reflection"
```

---

### Task 8: Add `corpus_context` to Brain and Worker Prompts

**Files:**
- Modify: `packages/core/airees/brain/prompt.py:7-14`
- Modify: `packages/core/airees/coordinator/worker_builder.py:56-64`
- Test: `packages/core/tests/test_brain_prompt.py`

**Step 1: Write the failing test**

Add to `tests/test_brain_prompt.py`:

```python
from airees.brain.prompt import build_brain_prompt
from airees.soul import Soul


def test_brain_prompt_includes_corpus_context():
    soul = Soul(name="Test", version=1, content="Test soul", raw="---\nname: Test\n---\nTest soul")
    prompt = build_brain_prompt(
        soul=soul,
        goal="Build an API",
        corpus_context="## Best Practices\n- Use FastAPI for async\n",
    )
    assert "Training Corpus Reference" in prompt
    assert "Use FastAPI for async" in prompt


def test_brain_prompt_without_corpus_context():
    soul = Soul(name="Test", version=1, content="Test soul", raw="---\nname: Test\n---\nTest soul")
    prompt = build_brain_prompt(soul=soul, goal="Build an API")
    assert "Training Corpus Reference" not in prompt
```

And in `tests/test_worker_builder.py` (if it exists, otherwise test_brain_prompt.py):

```python
from airees.coordinator.worker_builder import build_worker_prompt


def test_worker_prompt_includes_corpus_context():
    prompt = build_worker_prompt(
        task_title="Research APIs",
        task_description="Find the best API framework",
        agent_role="researcher",
        corpus_context="## Best Practices\n- REST vs GraphQL comparison\n",
    )
    assert "Training Corpus" in prompt
    assert "REST vs GraphQL" in prompt


def test_worker_prompt_without_corpus_context():
    prompt = build_worker_prompt(
        task_title="Research APIs",
        task_description="Find the best API framework",
        agent_role="researcher",
    )
    assert "Training Corpus" not in prompt
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_brain_prompt.py -v -k "corpus"`
Expected: FAIL — unexpected keyword argument 'corpus_context'

**Step 3: Write minimal implementation**

In `brain/prompt.py`, add `corpus_context: str | None = None` parameter to `build_brain_prompt()` after `active_skill`:

```python
def build_brain_prompt(
    *,
    soul: Soul,
    goal: str,
    intent: str | None = None,
    coordinator_report: str | None = None,
    active_skill: str | None = None,
    corpus_context: str | None = None,
    iteration: int = 0,
) -> str:
```

Then add this block after the `active_skill` section (after line 68):

```python
    if corpus_context:
        sections.append(f"\n## Training Corpus Reference\n\n{corpus_context}\n")
```

In `coordinator/worker_builder.py`, add `corpus_context: str | None = None` parameter to `build_worker_prompt()`:

```python
def build_worker_prompt(
    *,
    task_title: str,
    task_description: str,
    agent_role: str,
    skill_content: str | None = None,
    previous_output: str | None = None,
    available_tools: list[str] | None = None,
    corpus_context: str | None = None,
) -> str:
```

Then add this block after the `skill_content` section (after line 79):

```python
    if corpus_context:
        sections.append(f"\n## Training Corpus Reference\n\n{corpus_context}")
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_brain_prompt.py tests/test_worker_builder.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/brain/prompt.py packages/core/airees/coordinator/worker_builder.py packages/core/tests/test_brain_prompt.py
git commit -m "feat: add corpus_context parameter to brain and worker prompts"
```

---

### Task 9: Wire Everything into BrainOrchestrator

**Files:**
- Modify: `packages/core/airees/brain/orchestrator.py`
- Test: `packages/core/tests/test_brain_orchestrator.py`

This is the biggest integration task. The orchestrator needs to:
1. Accept `CorpusSearchEngine` and `SkillStore` as constructor parameters
2. Search skills on `submit_goal()`
3. Search corpus during `plan()` and inject into brain prompt
4. Search corpus during `_execute_worker()` and inject into worker prompt
5. Handle `create_skill`, `update_skill`, `search_corpus`, `search_skills`, `update_soul` tool calls from Brain

**Step 1: Write the failing tests**

Add to `tests/test_brain_orchestrator.py`:

```python
# These tests require updating existing mocks and adding new ones

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from airees.brain.orchestrator import BrainOrchestrator
from airees.corpus_search import CorpusSearchEngine, CorpusResult
from airees.skill_store import SkillStore, SkillResult
from airees.events import EventBus


@pytest.fixture
def mock_corpus_engine():
    engine = MagicMock(spec=CorpusSearchEngine)
    engine.search.return_value = [
        CorpusResult(
            path=Path("training/01/test.md"),
            title="Test Best Practices",
            category="01-fundamentals",
            score=5.0,
            excerpt="Always write tests first.",
        )
    ]
    engine.format_results.return_value = "### Test Best Practices\nAlways write tests first."
    return engine


@pytest.fixture
def mock_skill_store(tmp_path):
    store = MagicMock(spec=SkillStore)
    store.search.return_value = []
    store.load_skill.return_value = None
    store.create_skill.return_value = tmp_path / "skills" / "test.md"
    store.update_skill.return_value = tmp_path / "skills" / "test.md"
    return store


@pytest.mark.asyncio
async def test_orchestrator_accepts_corpus_and_skills(tmp_path):
    store = AsyncMock()
    router = AsyncMock()
    bus = EventBus()
    corpus = MagicMock(spec=CorpusSearchEngine)
    skills = MagicMock(spec=SkillStore)

    orch = BrainOrchestrator(
        store=store,
        brain_model="test",
        router=router,
        event_bus=bus,
        corpus_engine=corpus,
        skill_store=skills,
    )
    assert orch.corpus_engine is corpus
    assert orch.skill_store is skills


@pytest.mark.asyncio
async def test_orchestrator_defaults_none_corpus_and_skills(tmp_path):
    store = AsyncMock()
    router = AsyncMock()
    bus = EventBus()

    orch = BrainOrchestrator(
        store=store,
        brain_model="test",
        router=router,
        event_bus=bus,
    )
    assert orch.corpus_engine is None
    assert orch.skill_store is None


@pytest.mark.asyncio
async def test_execute_worker_injects_corpus_context(
    mock_corpus_engine, mock_skill_store, tmp_path
):
    """Verify that _execute_worker searches corpus and passes context to worker prompt."""
    store = AsyncMock()
    router = AsyncMock()
    bus = EventBus()

    # Mock response for worker LLM call
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Worker output"
    worker_response = MagicMock()
    worker_response.content = [text_block]
    worker_response.stop_reason = "end_turn"
    worker_response.usage = MagicMock(input_tokens=100, output_tokens=50)

    # Mock response for quality gate scoring
    score_block = MagicMock()
    score_block.type = "text"
    score_block.text = '{"score": 8, "feedback": "Good"}'
    score_response = MagicMock()
    score_response.content = [score_block]
    score_response.usage = MagicMock(input_tokens=50, output_tokens=20)

    router.create_message.side_effect = [worker_response, score_response]

    orch = BrainOrchestrator(
        store=store,
        brain_model="test",
        router=router,
        event_bus=bus,
        corpus_engine=mock_corpus_engine,
        skill_store=mock_skill_store,
    )

    task = {
        "id": "task-1",
        "title": "Test Task",
        "description": "Do something",
        "agent_role": "coder",
    }

    await orch._execute_worker("goal-1", task)
    mock_corpus_engine.search.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_brain_orchestrator.py -v -k "corpus or skill"`
Expected: FAIL — BrainOrchestrator doesn't accept corpus_engine or skill_store

**Step 3: Write minimal implementation**

Modify `brain/orchestrator.py`:

1. Add imports at top:
```python
from airees.corpus_search import CorpusSearchEngine
from airees.skill_store import SkillStore
from airees.brain.reflection import update_soul_file, write_daily_log
```

2. Add fields to the `BrainOrchestrator` dataclass (after `quality_gate`):
```python
    corpus_engine: CorpusSearchEngine | None = None
    skill_store: SkillStore | None = None
    skills_dir: Path = Path("data/skills")
```

3. In `_execute_worker()`, after building `worker_prompt` (around line 394-399), search corpus and inject:
```python
        # Search corpus for relevant best practices
        corpus_context = None
        if self.corpus_engine:
            corpus_results = self.corpus_engine.search(task["description"], top_k=2)
            if corpus_results:
                corpus_context = self.corpus_engine.format_results(corpus_results)

        worker_prompt = build_worker_prompt(
            task_title=task["title"],
            task_description=task["description"],
            agent_role=task["agent_role"],
            available_tools=role_tool_names if role_tool_names else None,
            corpus_context=corpus_context,
        )
```

4. In `plan()`, search corpus and pass to build_brain_prompt:
```python
        # Search corpus for relevant best practices
        corpus_context = None
        if self.corpus_engine:
            corpus_results = self.corpus_engine.search(goal["description"], top_k=3)
            if corpus_results:
                corpus_context = self.corpus_engine.format_results(corpus_results)

        # Search skills for matching pipeline
        active_skill = None
        if self.skill_store:
            skill_results = self.skill_store.search(goal["description"], top_k=1)
            if skill_results:
                active_skill = self.skill_store.load_skill(skill_results[0].name)
                await self.event_bus.emit_async(Event(
                    event_type=EventType.SKILL_MATCHED,
                    agent_name="brain",
                    data={"skill": skill_results[0].name, "score": skill_results[0].score},
                ))

        prompt = build_brain_prompt(
            soul=soul,
            goal=goal["description"],
            intent=intent,
            active_skill=active_skill,
            corpus_context=corpus_context,
        )
```

5. In `execute_goal()`, after the satisfied branch (around line 320), handle Brain tool calls for skills and reflection:

Add a new method `_handle_brain_tools()` that processes `create_skill`, `update_skill`, `search_corpus`, `search_skills`, `update_soul` tool use blocks from Brain responses:

```python
    async def _handle_brain_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a brain tool call and return the result."""
        if tool_name == "search_corpus" and self.corpus_engine:
            results = self.corpus_engine.search(
                tool_input.get("query", ""),
                top_k=tool_input.get("top_k", 3),
            )
            return self.corpus_engine.format_results(results)

        if tool_name == "search_skills" and self.skill_store:
            results = self.skill_store.search(tool_input.get("query", ""))
            if not results:
                return "No matching skills found."
            lines = []
            for r in results:
                lines.append(f"- **{r.name}** (v{r.version}, {r.success_rate:.0%} success): {r.content[:100]}...")
            return "\n".join(lines)

        if tool_name == "create_skill" and self.skill_store:
            path = self.skill_store.create_skill(
                name=tool_input["name"],
                description=tool_input["description"],
                triggers=tool_input["triggers"],
                task_graph=tool_input["task_graph"],
                lessons_learned=tool_input.get("lessons_learned", ""),
                quality_gates=tool_input.get("quality_gates", ""),
                known_pitfalls=tool_input.get("known_pitfalls", ""),
            )
            await self.event_bus.emit_async(Event(
                event_type=EventType.SKILL_CREATED,
                agent_name="brain",
                data={"skill": tool_input["name"], "path": str(path)},
            ))
            return f"Skill '{tool_input['name']}' created at {path}"

        if tool_name == "update_skill" and self.skill_store:
            path = self.skill_store.update_skill(
                name=tool_input["name"],
                lessons_learned=tool_input.get("lessons_learned", ""),
                known_pitfalls=tool_input.get("known_pitfalls", ""),
                task_graph=tool_input.get("task_graph", ""),
            )
            await self.event_bus.emit_async(Event(
                event_type=EventType.SKILL_UPDATED,
                agent_name="brain",
                data={"skill": tool_input["name"]},
            ))
            return f"Skill '{tool_input['name']}' updated"

        if tool_name == "update_soul":
            update_soul_file(
                self.soul_path,
                capabilities_update=tool_input.get("capabilities_update"),
                strategy_update=tool_input.get("strategy_update"),
                lesson=tool_input.get("lesson"),
            )
            await self.event_bus.emit_async(Event(
                event_type=EventType.SOUL_UPDATED,
                agent_name="brain",
                data=tool_input,
            ))
            return "SOUL.md updated"

        return f"Unknown tool: {tool_name}"
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_brain_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/brain/orchestrator.py packages/core/tests/test_brain_orchestrator.py
git commit -m "feat: wire corpus search, skill store, and reflection into orchestrator"
```

---

### Task 10: Update Exports and Write Integration Test

**Files:**
- Modify: `packages/core/airees/__init__.py`
- Create: `packages/core/tests/test_phase4_integration.py`

**Step 1: Write the failing test**

Create `tests/test_phase4_integration.py`:

```python
"""Phase 4 integration: verify all new components are exported and work together."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_all_phase4_exports():
    """Verify every Phase 4 class is importable from airees."""
    mod = importlib.import_module("airees")
    for name in [
        "CorpusSearchEngine",
        "CorpusResult",
        "CorpusDocument",
        "SkillStore",
        "SkillResult",
        "SkillDocument",
        "ContextCompressor",
    ]:
        assert hasattr(mod, name), f"Missing export: {name}"


def test_phase4_event_types():
    from airees import EventType
    phase4_events = [
        "CORPUS_SEARCH",
        "SKILL_MATCHED",
        "SKILL_CREATED",
        "SKILL_UPDATED",
        "CONTEXT_COMPRESSED",
        "SOUL_UPDATED",
        "REFLECTION_TRIGGERED",
    ]
    for name in phase4_events:
        assert hasattr(EventType, name), f"Missing event type: {name}"


def test_corpus_and_skill_search_together(tmp_path: Path):
    """Test that corpus and skill engines can coexist and search independently."""
    from airees.corpus_search import CorpusSearchEngine
    from airees.skill_store import SkillStore

    # Create a mini corpus
    corpus_dir = tmp_path / "corpus"
    cat = corpus_dir / "01-fundamentals"
    cat.mkdir(parents=True)
    (cat / "01-basics.md").write_text(
        "# Agent Basics\n\nAgents use tools to accomplish tasks.\n",
        encoding="utf-8",
    )

    # Create a skill
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "api-builder.md").write_text(
        "---\nname: api-builder\ndescription: Build REST APIs\nversion: 1\n"
        "triggers:\n  - build an api\n---\n\n# API Builder\n",
        encoding="utf-8",
    )

    corpus = CorpusSearchEngine(corpus_dir=corpus_dir)
    skills = SkillStore(skills_dir=skills_dir)

    corpus_results = corpus.search("agent tools")
    skill_results = skills.search("build an api")

    assert len(corpus_results) == 1
    assert corpus_results[0].title == "Agent Basics"
    assert len(skill_results) == 1
    assert skill_results[0].name == "api-builder"


def test_reflection_functions_importable():
    from airees.brain.reflection import (
        compute_genesis_hash,
        update_soul_file,
        write_daily_log,
    )
    assert callable(compute_genesis_hash)
    assert callable(update_soul_file)
    assert callable(write_daily_log)
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_phase4_integration.py -v`
Expected: FAIL — Missing export errors

**Step 3: Update `__init__.py`**

Add these imports and exports to `packages/core/airees/__init__.py`:

```python
from airees.corpus_search import CorpusDocument, CorpusResult, CorpusSearchEngine
from airees.skill_store import SkillDocument, SkillResult, SkillStore
from airees.context_compressor import ContextCompressor
```

And add to `__all__`:
```python
    "ContextCompressor",
    "CorpusDocument",
    "CorpusResult",
    "CorpusSearchEngine",
    "SkillDocument",
    "SkillResult",
    "SkillStore",
```

**Step 4: Run ALL Phase 4 tests**

Run: `cd packages/core && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/airees/__init__.py packages/core/tests/test_phase4_integration.py
git commit -m "feat: update exports, add Phase 4 integration test"
```

---

### Task Summary

| Task | What It Does | New Files | Modified Files |
|------|-------------|-----------|----------------|
| 1 | Add 7 event types | - | events.py, test_events.py |
| 2 | Add rank-bm25 dependency | - | pyproject.toml |
| 3 | Corpus search engine | corpus_search.py, test_corpus_search.py | - |
| 4 | Skill store | skill_store.py, test_skill_store.py | - |
| 5 | Context compressor | context_compressor.py, test_context_compressor.py | - |
| 6 | Brain reflection | brain/reflection.py, test_reflection.py | - |
| 7 | Brain tools | - | brain/tools.py, test_brain_tools.py |
| 8 | Prompt injection points | - | brain/prompt.py, coordinator/worker_builder.py |
| 9 | Wire into orchestrator | - | brain/orchestrator.py, test_brain_orchestrator.py |
| 10 | Exports + integration test | test_phase4_integration.py | __init__.py |

**Total: 10 tasks, ~6 new files, ~6 modified files, ~10 test files updated**
