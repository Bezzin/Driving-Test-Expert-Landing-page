# Full Stack Autonomous Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the learning loop, add a personal knowledge base, enable proactive scheduling, and extend channels with Discord and voice support.

**Architecture:** Four layers built bottom-up: (1) Learning Loop wires existing SkillStore/FeedbackLoop into the conversation path for skill reuse and adaptive model selection; (2) Knowledge Base adds ChromaDB semantic search over personal documents; (3) Proactive Agent adds cron-triggered goals with push notifications; (4) Extended Channels adds Discord adapter and voice (STT/TTS) to Telegram.

**Tech Stack:** Python 3.11+, chromadb, sentence-transformers, pymupdf, discord.py, faster-whisper, piper-tts, pydub, pytest, pytest-asyncio

---

## Layer 1: Learning Loop

### Task 1: Skill-Aware Routing

Wire SkillStore into ConversationManager so proven patterns skip brain planning.

**Files:**
- Modify: `airees/gateway/conversation.py`
- Test: `tests/test_conversation_manager.py`

**Step 1: Write the failing tests**

Add to `tests/test_conversation_manager.py`:

```python
import tempfile
from pathlib import Path

from airees.skill_store import SkillStore


def _make_skill_store(tmp_path: Path) -> SkillStore:
    """Create a SkillStore with one test skill."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    store = SkillStore(skills_dir=skills_dir)
    store.create_skill(
        name="daily-summary",
        description="Summarize my day",
        triggers=["summarize my day", "daily summary", "what happened today"],
        task_graph="1. Gather calendar events\n2. Summarize",
    )
    return store


@pytest.mark.asyncio
async def test_skill_match_skips_brain():
    """When SkillStore matches with high confidence, skip the brain."""
    router = FakeRouter(reply="skill-based reply")
    store = _make_skill_store(Path(tempfile.mkdtemp()))
    mgr = _make_manager(router=router)
    mgr.skill_store = store

    msg = InboundMessage(channel="cli", sender_id="user-1", text="summarize my day")
    response = await mgr.handle(msg)

    assert isinstance(response, OutboundMessage)
    assert response.text  # Should get a response
    # Router should be called (skill content passed as context to quick path)
    assert len(router._calls) == 1


@pytest.mark.asyncio
async def test_no_skill_store_falls_through():
    """Without a SkillStore, routing works as before."""
    router = FakeRouter(reply="normal reply")
    mgr = _make_manager(router=router)
    # skill_store is None by default

    msg = InboundMessage(channel="cli", sender_id="user-1", text="summarize my day")
    response = await mgr.handle(msg)

    assert response.text == "normal reply"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_conversation_manager.py -v -k "skill"`
Expected: FAIL — `AttributeError: 'ConversationManager' has no attribute 'skill_store'`

**Step 3: Implement skill-aware routing**

In `airees/gateway/conversation.py`:

1. Add import: `from airees.skill_store import SkillStore`
2. Add field to ConversationManager: `skill_store: SkillStore | None = None`
3. Add `_SKILL_CONFIDENCE_THRESHOLD = 0.5`
4. In `handle()`, before complexity classification, check skill store:

```python
# Check skill store for a cached pattern
skill_result = None
if self.skill_store is not None:
    results = self.skill_store.search(message.text, top_k=1)
    if results and results[0].score >= _SKILL_CONFIDENCE_THRESHOLD:
        skill_result = results[0]
        log.info("Skill match: %s (score=%.2f)", skill_result.name, skill_result.score)

if skill_result is not None:
    # Use skill content as context, route through quick path at Haiku
    reply_text = await self._run_skill(
        message.text, context_messages, personal, skill_result,
        channel=message.channel,
    )
else:
    # Normal complexity-based routing
    complexity = await classify_complexity(message.text)
    ...
```

5. Add `_run_skill()` method:

```python
async def _run_skill(
    self,
    text: str,
    context_messages: list[dict[str, str]],
    personal: PersonalContext,
    skill: Any,
    *,
    channel: str = "unknown",
) -> str:
    """Handle a message using a cached skill pattern."""
    soul = self._get_soul()
    system_prompt = (
        soul.to_prompt() + "\n\n" + personal.to_prompt()
        + f"\n\nYou have a proven approach for this type of request:\n{skill.content}"
    )
    messages = [*context_messages, {"role": "user", "content": text}]
    model = _MODEL_MAP["haiku"]  # Skills always use cheapest model

    try:
        response = await self.router.create_message(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=1024,
        )
        reply_text = response.content[0].text

        if self.cost_tracker is not None:
            context_text = " ".join(m["content"] for m in messages)
            input_tokens = (len(system_prompt) + len(context_text)) // 4
            output_tokens = len(reply_text) // 4
            self.cost_tracker.record(
                model=model, input_tokens=input_tokens,
                output_tokens=output_tokens, channel=channel,
            )

        return reply_text
    except Exception as exc:
        log.error("_run_skill failed: %s", exc, exc_info=True)
        return "I'm sorry, something went wrong. Please try again."
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_conversation_manager.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: 439+ tests PASS

**Step 6: Commit**

```bash
git add airees/gateway/conversation.py tests/test_conversation_manager.py
git commit -m "feat: add skill-aware routing to ConversationManager"
```

---

### Task 2: Auto-Skill Capture

After successful brain-orchestrated goals, automatically create skills for novel patterns.

**Files:**
- Create: `airees/gateway/learning.py`
- Test: `tests/test_learning.py`

**Step 1: Write the failing tests**

Create `tests/test_learning.py`:

```python
"""Tests for auto-skill capture after successful goals."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.learning import AutoSkillCapture
from airees.skill_store import SkillStore


@pytest.fixture
def skill_store(tmp_path: Path) -> SkillStore:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return SkillStore(skills_dir=skills_dir)


def test_capture_creates_skill_for_novel_pattern(skill_store: SkillStore):
    """A novel successful goal creates a new skill."""
    capture = AutoSkillCapture(skill_store=skill_store)

    capture.maybe_create_skill(
        goal_text="summarize the quarterly report",
        result_text="Here is the summary...",
        success=True,
    )

    results = skill_store.search("summarize quarterly report")
    assert len(results) >= 1
    assert results[0].name  # Should have a name


def test_capture_skips_existing_skill(skill_store: SkillStore):
    """If a skill already matches, don't create a duplicate."""
    skill_store.create_skill(
        name="summarize-report",
        description="Summarize reports",
        triggers=["summarize the quarterly report"],
        task_graph="1. Read report\n2. Summarize",
    )

    capture = AutoSkillCapture(skill_store=skill_store)
    initial_count = len(list(skill_store.skills_dir.glob("*.md")))

    capture.maybe_create_skill(
        goal_text="summarize the quarterly report",
        result_text="Summary here",
        success=True,
    )

    final_count = len(list(skill_store.skills_dir.glob("*.md")))
    assert final_count == initial_count  # No new skill created


def test_capture_skips_failed_goals(skill_store: SkillStore):
    """Failed goals should not create skills."""
    capture = AutoSkillCapture(skill_store=skill_store)

    capture.maybe_create_skill(
        goal_text="do something complex",
        result_text="Error occurred",
        success=False,
    )

    results = skill_store.search("do something complex")
    assert len(results) == 0


def test_capture_updates_existing_on_repeat_success(skill_store: SkillStore):
    """If a skill exists and succeeds again, update its success rate."""
    skill_store.create_skill(
        name="daily-summary",
        description="Daily summary",
        triggers=["summarize my day"],
        task_graph="1. Gather\n2. Summarize",
    )

    capture = AutoSkillCapture(skill_store=skill_store)
    capture.maybe_create_skill(
        goal_text="summarize my day",
        result_text="Done",
        success=True,
    )

    # Skill should still exist (updated, not duplicated)
    results = skill_store.search("summarize my day")
    assert len(results) >= 1
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_learning.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'airees.gateway.learning'`

**Step 3: Implement AutoSkillCapture**

Create `airees/gateway/learning.py`:

```python
"""Auto-skill capture — learn from successful goal executions."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from airees.skill_store import SkillStore

log = logging.getLogger(__name__)

_DUPLICATE_THRESHOLD = 0.5  # Skip creation if existing skill scores above this


@dataclass
class AutoSkillCapture:
    """Captures successful goal patterns as reusable skills."""

    skill_store: SkillStore

    def maybe_create_skill(
        self,
        *,
        goal_text: str,
        result_text: str,
        success: bool,
    ) -> bool:
        """Create a skill if the goal was novel and successful.

        Returns True if a skill was created or updated, False otherwise.
        """
        if not success:
            log.debug("Skipping skill capture for failed goal")
            return False

        # Check if a skill already matches
        existing = self.skill_store.search(goal_text, top_k=1)
        if existing and existing[0].score >= _DUPLICATE_THRESHOLD:
            # Update existing skill's success rate
            try:
                self.skill_store.update_skill(
                    name=existing[0].name,
                    success=True,
                )
                log.info("Updated existing skill: %s", existing[0].name)
            except FileNotFoundError:
                pass
            return True

        # Create a new skill
        name = _slugify(goal_text)
        triggers = [goal_text.lower().strip()]
        self.skill_store.create_skill(
            name=name,
            description=goal_text[:200],
            triggers=triggers,
            task_graph=f"Goal: {goal_text}\nResult: {result_text[:500]}",
        )
        log.info("Created new skill: %s", name)
        return True


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower().strip())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:60]
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_learning.py -v`
Expected: ALL PASS

**Step 5: Run full suite and commit**

Run: `python -m pytest tests/ -v`

```bash
git add airees/gateway/learning.py tests/test_learning.py
git commit -m "feat: add auto-skill capture for successful goals"
```

---

### Task 3: Adaptive Model Selection

Track success rates per complexity tier and auto-adjust routing.

**Files:**
- Create: `airees/gateway/model_preference.py`
- Test: `tests/test_model_preference.py`

**Step 1: Write the failing tests**

Create `tests/test_model_preference.py`:

```python
"""Tests for adaptive model preference learning."""
from __future__ import annotations

import pytest

from airees.gateway.model_preference import ModelPreference


def test_default_preference_returns_hint():
    """With no history, returns the default model hint."""
    pref = ModelPreference()
    assert pref.get_model("quick") == "haiku"
    assert pref.get_model("moderate") == "sonnet"
    assert pref.get_model("complex") == "opus"


def test_record_success_at_cheaper_tier():
    """After enough successes at a cheaper tier, prefer it."""
    pref = ModelPreference(downgrade_threshold=3)

    # Record 3 successes of "moderate" tasks at "haiku"
    for _ in range(3):
        pref.record(complexity="moderate", model_used="haiku", success=True)

    # Should now prefer haiku for moderate
    assert pref.get_model("moderate") == "haiku"


def test_record_failure_upgrades():
    """After failures at a tier, don't downgrade."""
    pref = ModelPreference(downgrade_threshold=3, upgrade_threshold=2)

    # Record 2 failures at haiku for moderate
    pref.record(complexity="moderate", model_used="haiku", success=False)
    pref.record(complexity="moderate", model_used="haiku", success=False)

    # Should keep sonnet for moderate (not downgrade)
    assert pref.get_model("moderate") == "sonnet"


def test_stats_returns_counts():
    pref = ModelPreference()
    pref.record(complexity="quick", model_used="haiku", success=True)
    pref.record(complexity="quick", model_used="haiku", success=True)
    pref.record(complexity="quick", model_used="haiku", success=False)

    stats = pref.stats()
    assert stats["quick"]["haiku"]["successes"] == 2
    assert stats["quick"]["haiku"]["failures"] == 1
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_model_preference.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement ModelPreference**

Create `airees/gateway/model_preference.py`:

```python
"""Adaptive model preference — learn which models work for which complexity."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_HINTS: dict[str, str] = {
    "quick": "haiku",
    "moderate": "sonnet",
    "complex": "opus",
}

_DOWNGRADE_MAP: dict[str, str] = {
    "sonnet": "haiku",
    "opus": "sonnet",
}


@dataclass
class ModelPreference:
    """Tracks success/failure rates and recommends model tiers.

    Attributes:
        downgrade_threshold: Consecutive successes at a cheaper tier
            needed before recommending it as default.
        upgrade_threshold: Consecutive failures at a tier before
            reverting to the original default.
    """

    downgrade_threshold: int = 3
    upgrade_threshold: int = 2
    _records: dict[str, dict[str, dict[str, int]]] = field(
        default_factory=dict, init=False
    )
    _overrides: dict[str, str] = field(default_factory=dict, init=False)

    def record(self, *, complexity: str, model_used: str, success: bool) -> None:
        """Record a success or failure for a complexity+model pair."""
        if complexity not in self._records:
            self._records[complexity] = {}
        if model_used not in self._records[complexity]:
            self._records[complexity][model_used] = {"successes": 0, "failures": 0}

        bucket = self._records[complexity][model_used]
        if success:
            bucket["successes"] += 1
        else:
            bucket["failures"] += 1

        self._recompute(complexity)

    def get_model(self, complexity: str) -> str:
        """Return the recommended model tier for this complexity."""
        return self._overrides.get(complexity, _DEFAULT_HINTS.get(complexity, "sonnet"))

    def stats(self) -> dict[str, Any]:
        """Return raw success/failure counts."""
        return dict(self._records)

    def _recompute(self, complexity: str) -> None:
        """Recompute the override for a complexity tier."""
        default = _DEFAULT_HINTS.get(complexity, "sonnet")
        cheaper = _DOWNGRADE_MAP.get(default)

        if cheaper and cheaper in self._records.get(complexity, {}):
            bucket = self._records[complexity][cheaper]
            if bucket["successes"] >= self.downgrade_threshold:
                failure_rate = bucket["failures"] / max(
                    bucket["successes"] + bucket["failures"], 1
                )
                if failure_rate < 0.3:
                    self._overrides[complexity] = cheaper
                    log.info(
                        "Downgraded %s from %s to %s",
                        complexity, default, cheaper,
                    )
                    return

        # Check if cheaper model is failing too much
        if cheaper and cheaper in self._records.get(complexity, {}):
            bucket = self._records[complexity][cheaper]
            if bucket["failures"] >= self.upgrade_threshold:
                self._overrides.pop(complexity, None)
                log.info("Reverted %s to default %s", complexity, default)
                return
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_model_preference.py -v`
Expected: ALL PASS

**Step 5: Run full suite and commit**

```bash
git add airees/gateway/model_preference.py tests/test_model_preference.py
git commit -m "feat: add adaptive model preference learning"
```

---

### Task 4: Wire Learning into ConversationManager and Bootstrap

Connect all learning components into the pipeline.

**Files:**
- Modify: `airees/gateway/conversation.py`
- Modify: `airees/cli/bootstrap.py`
- Modify: `airees/__init__.py`
- Test: `tests/test_learning_integration.py`

**Step 1: Write integration test**

Create `tests/test_learning_integration.py`:

```python
"""Integration test: learning loop wired end-to-end."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.cost_tracker import CostTracker
from airees.gateway.learning import AutoSkillCapture
from airees.gateway.model_preference import ModelPreference
from airees.gateway.session import SessionStore
from airees.gateway.types import InboundMessage
from airees.skill_store import SkillStore

# Reuse FakeRouter from test_conversation_manager
from tests.test_conversation_manager import FakeRouter


@pytest.mark.asyncio
async def test_learning_loop_wired():
    """ConversationManager with all learning components responds."""
    tmp = Path(tempfile.mkdtemp())
    skills_dir = tmp / "skills"
    skills_dir.mkdir()

    store = SkillStore(skills_dir=skills_dir)
    tracker = CostTracker()
    pref = ModelPreference()

    mgr = ConversationManager(
        router=FakeRouter(reply="learned reply"),
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        skill_store=store,
        cost_tracker=tracker,
        model_preference=pref,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="hello there")
    response = await mgr.handle(msg)

    assert response.text == "learned reply"
    assert tracker.total_turns >= 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_learning_integration.py -v`
Expected: FAIL — `TypeError: unexpected keyword argument 'model_preference'`

**Step 3: Wire ModelPreference into ConversationManager**

In `airees/gateway/conversation.py`:
1. Add import: `from airees.gateway.model_preference import ModelPreference`
2. Add field: `model_preference: ModelPreference | None = None`
3. In `_run_quick()`, if `model_preference` is set, use it instead of `_MODEL_MAP`:

```python
if self.model_preference is not None:
    hint = self.model_preference.get_model(complexity.value)
else:
    hint = complexity.model_hint
model = _MODEL_MAP.get(hint, _MODEL_MAP["haiku"])
```

4. After successful response, record the outcome:

```python
if self.model_preference is not None:
    self.model_preference.record(
        complexity=complexity.value,
        model_used=hint,
        success=True,
    )
```

**Step 4: Wire into bootstrap**

In `airees/cli/bootstrap.py`:
1. Add imports: `from airees.skill_store import SkillStore`, `from airees.gateway.cost_tracker import CostTracker`, `from airees.gateway.model_preference import ModelPreference`
2. In `bootstrap_gateway()`, create and pass these components:

```python
skill_store = SkillStore(skills_dir=data_dir / "skills")
cost_tracker = CostTracker()
model_preference = ModelPreference()

manager = ConversationManager(
    router=orch.router,
    event_bus=orch.event_bus,
    soul_path=data_dir / "SOUL.md",
    user_path=data_dir / "USER.md",
    orchestrator=orch,
    skill_store=skill_store,
    cost_tracker=cost_tracker,
    model_preference=model_preference,
)
```

**Step 5: Update exports in `__init__.py`**

Add to imports and `__all__`:
- `AutoSkillCapture` from `airees.gateway.learning`
- `ModelPreference` from `airees.gateway.model_preference`

**Step 6: Run full suite and commit**

Run: `python -m pytest tests/ -v`

```bash
git add airees/gateway/conversation.py airees/cli/bootstrap.py airees/__init__.py tests/test_learning_integration.py
git commit -m "feat: wire learning loop into ConversationManager and bootstrap"
```

---

## Layer 2: Knowledge Base

### Task 5: KnowledgeStore with ChromaDB

Core knowledge storage and semantic search.

**Files:**
- Create: `airees/knowledge/__init__.py`
- Create: `airees/knowledge/store.py`
- Test: `tests/test_knowledge_store.py`

**Step 1: Write the failing tests**

Create `tests/test_knowledge_store.py`:

```python
"""Tests for KnowledgeStore — ChromaDB-based semantic search."""
from __future__ import annotations

from pathlib import Path

import pytest

from airees.knowledge.store import KnowledgeResult, KnowledgeStore


@pytest.fixture
def store(tmp_path: Path) -> KnowledgeStore:
    return KnowledgeStore(data_dir=tmp_path / "knowledge")


def test_ingest_text_file(store: KnowledgeStore, tmp_path: Path):
    """Ingesting a text file makes it searchable."""
    doc = tmp_path / "notes.txt"
    doc.write_text("The quarterly budget was approved for $50,000.", encoding="utf-8")

    store.ingest(doc)
    results = store.search("budget approved")

    assert len(results) >= 1
    assert "budget" in results[0].text.lower()


def test_ingest_markdown_file(store: KnowledgeStore, tmp_path: Path):
    """Ingesting a markdown file works."""
    doc = tmp_path / "meeting.md"
    doc.write_text("# Meeting Notes\n\nDiscussed the new AI deployment timeline.", encoding="utf-8")

    store.ingest(doc)
    results = store.search("AI deployment timeline")

    assert len(results) >= 1


def test_search_empty_store_returns_empty(store: KnowledgeStore):
    """Searching an empty store returns empty list."""
    results = store.search("anything")
    assert results == []


def test_delete_removes_document(store: KnowledgeStore, tmp_path: Path):
    """Deleting a document removes it from search."""
    doc = tmp_path / "temp.txt"
    doc.write_text("Temporary data for testing.", encoding="utf-8")

    store.ingest(doc)
    assert len(store.search("temporary data")) >= 1

    store.delete(str(doc))
    assert len(store.search("temporary data")) == 0


def test_stats_reports_counts(store: KnowledgeStore, tmp_path: Path):
    """stats() returns document count."""
    assert store.stats()["document_count"] == 0

    doc = tmp_path / "a.txt"
    doc.write_text("Test content.", encoding="utf-8")
    store.ingest(doc)

    assert store.stats()["document_count"] >= 1
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_knowledge_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Install dependencies and implement**

Run: `pip install chromadb sentence-transformers pymupdf`

Create `airees/knowledge/__init__.py`:

```python
"""Knowledge base — personal document ingestion and semantic search."""
```

Create `airees/knowledge/store.py`:

```python
"""KnowledgeStore — ChromaDB wrapper for personal document search."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_CHUNK_SIZE = 500  # characters per chunk
_CHUNK_OVERLAP = 50


@dataclass(frozen=True)
class KnowledgeResult:
    """A search result from the knowledge store."""

    text: str
    source: str
    score: float


@dataclass
class KnowledgeStore:
    """ChromaDB-backed semantic search over personal documents.

    Attributes:
        data_dir: Directory for ChromaDB persistence.
    """

    data_dir: Path
    _collection: Any = field(default=None, init=False, repr=False)

    def _get_collection(self) -> Any:
        """Lazy-init ChromaDB collection."""
        if self._collection is None:
            import chromadb

            self.data_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.data_dir))
            self._collection = client.get_or_create_collection(
                name="personal_knowledge",
            )
            log.info("ChromaDB collection initialized at %s", self.data_dir)
        return self._collection

    def ingest(self, path: Path) -> int:
        """Ingest a file into the knowledge store.

        Supports: .txt, .md, .pdf

        Returns:
            Number of chunks ingested.
        """
        text = self._extract_text(path)
        if not text.strip():
            log.warning("No text extracted from %s", path)
            return 0

        chunks = self._chunk_text(text)
        collection = self._get_collection()

        ids = [f"{path}::chunk-{i}" for i in range(len(chunks))]
        metadatas = [{"source": str(path), "chunk_index": i} for i in range(len(chunks))]

        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas,
        )
        log.info("Ingested %d chunks from %s", len(chunks), path)
        return len(chunks)

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeResult]:
        """Semantic search over ingested documents."""
        collection = self._get_collection()
        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
        )

        output = []
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0.0
            source = results["metadatas"][0][i].get("source", "unknown")
            output.append(
                KnowledgeResult(
                    text=doc,
                    source=source,
                    score=1.0 / (1.0 + distance),  # Convert distance to similarity
                )
            )
        return output

    def delete(self, source: str) -> int:
        """Delete all chunks from a specific source. Returns count deleted."""
        collection = self._get_collection()
        # Get all IDs matching this source
        results = collection.get(where={"source": source})
        if not results["ids"]:
            return 0
        collection.delete(ids=results["ids"])
        log.info("Deleted %d chunks from source %s", len(results["ids"]), source)
        return len(results["ids"])

    def stats(self) -> dict[str, Any]:
        """Return collection statistics."""
        collection = self._get_collection()
        return {
            "document_count": collection.count(),
            "data_dir": str(self.data_dir),
        }

    def _extract_text(self, path: Path) -> str:
        """Extract text from a file based on extension."""
        suffix = path.suffix.lower()
        if suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8")
        elif suffix == ".pdf":
            return self._extract_pdf(path)
        else:
            log.warning("Unsupported file type: %s", suffix)
            return path.read_text(encoding="utf-8", errors="ignore")

    def _extract_pdf(self, path: Path) -> str:
        """Extract text from a PDF file."""
        try:
            import pymupdf
            doc = pymupdf.open(str(path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            log.error("pymupdf not installed — cannot extract PDF")
            return ""

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + _CHUNK_SIZE
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - _CHUNK_OVERLAP
        return chunks
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_knowledge_store.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/knowledge/__init__.py airees/knowledge/store.py tests/test_knowledge_store.py
git commit -m "feat: add KnowledgeStore with ChromaDB semantic search"
```

---

### Task 6: Context Enrichment — Wire KnowledgeStore into ConversationManager

**Files:**
- Modify: `airees/gateway/conversation.py`
- Test: `tests/test_knowledge_enrichment.py`

**Step 1: Write the failing test**

Create `tests/test_knowledge_enrichment.py`:

```python
"""Tests for knowledge-enriched conversation context."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.types import InboundMessage
from airees.knowledge.store import KnowledgeStore
from tests.test_conversation_manager import FakeRouter


@pytest.mark.asyncio
async def test_knowledge_enriches_system_prompt():
    """When knowledge_store has relevant docs, they appear in the prompt."""
    tmp = Path(tempfile.mkdtemp())

    # Create and populate knowledge store
    kb = KnowledgeStore(data_dir=tmp / "knowledge")
    doc = tmp / "project.txt"
    doc.write_text("The Airees project deadline is March 15th 2026.", encoding="utf-8")
    kb.ingest(doc)

    router = FakeRouter(reply="noted")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        knowledge_store=kb,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="when is the Airees deadline?")
    await mgr.handle(msg)

    # Check that the router received enriched context
    assert len(router._calls) == 1
    system_prompt = router._calls[0]["system"]
    assert "Relevant knowledge" in system_prompt or "deadline" in system_prompt.lower()
```

**Step 2: Run test to fail**

Run: `python -m pytest tests/test_knowledge_enrichment.py -v`
Expected: FAIL — `TypeError: unexpected keyword argument 'knowledge_store'`

**Step 3: Implement**

In `airees/gateway/conversation.py`:
1. Add import: `from airees.knowledge.store import KnowledgeStore`
2. Add field: `knowledge_store: KnowledgeStore | None = None`
3. In `_run_quick()` and `_run_skill()`, before building the system prompt, query knowledge store:

```python
# Build system prompt
soul = self._get_soul()
system_prompt = soul.to_prompt() + "\n\n" + personal.to_prompt()

# Enrich with knowledge base results
if self.knowledge_store is not None:
    kb_results = self.knowledge_store.search(text, top_k=3)
    if kb_results:
        kb_context = "\n\nRelevant knowledge:\n" + "\n".join(
            f"- [{r.source}] {r.text[:200]}" for r in kb_results
        )
        system_prompt += kb_context
```

Extract this into a private method `_build_system_prompt(text, personal)` to avoid duplication across `_run_quick`, `_run_skill`.

**Step 4: Run tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add airees/gateway/conversation.py tests/test_knowledge_enrichment.py
git commit -m "feat: wire KnowledgeStore into ConversationManager context enrichment"
```

---

### Task 7: Knowledge Base CLI Commands

**Files:**
- Modify: `airees/cli/main.py`
- Test: `tests/test_kb_cli.py`

**Step 1: Write tests**

Create `tests/test_kb_cli.py`:

```python
"""Tests for knowledge base CLI commands."""
from __future__ import annotations

from click.testing import CliRunner

from airees.cli.main import app


def test_kb_group_exists():
    """The 'kb' command group exists."""
    runner = CliRunner()
    result = runner.invoke(app, ["kb", "--help"])
    assert result.exit_code == 0
    assert "ingest" in result.output
    assert "search" in result.output
    assert "stats" in result.output
```

**Step 2: Run test to fail, implement, verify, commit**

Add to `airees/cli/main.py`:

```python
@app.group()
def kb() -> None:
    """Manage the knowledge base."""
    pass


@kb.command("ingest")
@click.argument("path", type=click.Path(exists=True))
@click.option("--data-dir", type=click.Path(), default="data")
def kb_ingest(path: str, data_dir: str) -> None:
    """Ingest a file or directory into the knowledge base."""
    from airees.knowledge.store import KnowledgeStore

    store = KnowledgeStore(data_dir=Path(data_dir) / "knowledge")
    target = Path(path)

    if target.is_file():
        count = store.ingest(target)
        click.echo(f"Ingested {count} chunks from {target.name}")
    elif target.is_dir():
        total = 0
        for f in target.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".txt", ".md", ".pdf"):
                total += store.ingest(f)
        click.echo(f"Ingested {total} chunks from {target}")


@kb.command("search")
@click.argument("query")
@click.option("--data-dir", type=click.Path(), default="data")
@click.option("--top-k", type=int, default=3)
def kb_search(query: str, data_dir: str, top_k: int) -> None:
    """Search the knowledge base."""
    from airees.knowledge.store import KnowledgeStore

    store = KnowledgeStore(data_dir=Path(data_dir) / "knowledge")
    results = store.search(query, top_k=top_k)
    if not results:
        click.echo("No results found.")
        return
    for r in results:
        click.echo(f"[{r.score:.2f}] {r.source}")
        click.echo(f"  {r.text[:200]}")
        click.echo()


@kb.command("stats")
@click.option("--data-dir", type=click.Path(), default="data")
def kb_stats(data_dir: str) -> None:
    """Show knowledge base statistics."""
    from airees.knowledge.store import KnowledgeStore

    store = KnowledgeStore(data_dir=Path(data_dir) / "knowledge")
    s = store.stats()
    click.echo(f"Documents: {s['document_count']}")
    click.echo(f"Data dir: {s['data_dir']}")


@kb.command("delete")
@click.argument("source")
@click.option("--data-dir", type=click.Path(), default="data")
def kb_delete(source: str, data_dir: str) -> None:
    """Delete a document from the knowledge base."""
    from airees.knowledge.store import KnowledgeStore

    store = KnowledgeStore(data_dir=Path(data_dir) / "knowledge")
    count = store.delete(source)
    click.echo(f"Deleted {count} chunks from {source}")
```

```bash
git add airees/cli/main.py tests/test_kb_cli.py
git commit -m "feat: add knowledge base CLI commands (ingest, search, stats, delete)"
```

---

### Task 8: Update pyproject.toml Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add new dependency groups**

```toml
[project.optional-dependencies]
gateway = ["starlette>=0.40.0", "uvicorn>=0.30.0"]
telegram = ["python-telegram-bot>=21.0"]
knowledge = ["chromadb>=0.5.0", "sentence-transformers>=3.0.0", "pymupdf>=1.24.0"]
discord = ["discord.py>=2.4.0"]
voice = ["faster-whisper>=1.0.0", "piper-tts>=1.2.0", "pydub>=0.25.1"]
all = ["airees[gateway,telegram,knowledge,discord,voice]"]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add optional dependency groups for knowledge, discord, voice"
```

---

## Layer 3: Proactive Agent

### Task 9: CronTrigger Data Model

**Files:**
- Create: `airees/gateway/cron.py`
- Test: `tests/test_cron.py`

**Step 1: Write tests**

Create `tests/test_cron.py`:

```python
"""Tests for CronTrigger data model and evaluation."""
from __future__ import annotations

from datetime import datetime

import pytest

from airees.gateway.cron import CronTrigger, is_due


def test_cron_trigger_creation():
    trigger = CronTrigger(
        id="t1",
        expression="0 9 * * *",
        goal_text="Check calendar",
        channel="telegram",
        recipient_id="user-1",
    )
    assert trigger.id == "t1"
    assert trigger.enabled is True


def test_is_due_matching():
    """A trigger matching the current minute is due."""
    trigger = CronTrigger(
        id="t1",
        expression="* * * * *",  # Every minute
        goal_text="test",
        channel="cli",
        recipient_id="u1",
    )
    assert is_due(trigger, datetime(2026, 3, 2, 9, 0)) is True


def test_is_due_not_matching():
    """A trigger not matching the current time is not due."""
    trigger = CronTrigger(
        id="t1",
        expression="0 9 * * *",  # 9am only
        goal_text="test",
        channel="cli",
        recipient_id="u1",
    )
    # 10am should not match
    assert is_due(trigger, datetime(2026, 3, 2, 10, 0)) is False


def test_disabled_trigger_never_due():
    trigger = CronTrigger(
        id="t1",
        expression="* * * * *",
        goal_text="test",
        channel="cli",
        recipient_id="u1",
        enabled=False,
    )
    assert is_due(trigger, datetime(2026, 3, 2, 9, 0)) is False
```

**Step 2: Implement**

Create `airees/gateway/cron.py`:

```python
"""Cron trigger definitions and evaluation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CronTrigger:
    """A scheduled task trigger.

    Attributes:
        id: Unique trigger identifier.
        expression: Cron expression (minute hour day month weekday).
        goal_text: Goal to submit when triggered.
        channel: Channel to deliver the result to.
        recipient_id: User ID for the push notification.
        enabled: Whether this trigger is active.
    """

    id: str
    expression: str
    goal_text: str
    channel: str
    recipient_id: str
    enabled: bool = True


def is_due(trigger: CronTrigger, now: datetime) -> bool:
    """Check if a trigger is due at the given time.

    Supports standard 5-field cron: minute hour day month weekday.
    '*' matches any value. Specific values must match exactly.
    """
    if not trigger.enabled:
        return False

    parts = trigger.expression.strip().split()
    if len(parts) != 5:
        log.warning("Invalid cron expression: %s", trigger.expression)
        return False

    fields = [
        (parts[0], now.minute),
        (parts[1], now.hour),
        (parts[2], now.day),
        (parts[3], now.month),
        (parts[4], now.weekday()),  # 0=Monday
    ]

    for pattern, value in fields:
        if pattern == "*":
            continue
        try:
            if int(pattern) != value:
                return False
        except ValueError:
            log.warning("Invalid cron field: %s", pattern)
            return False

    return True
```

```bash
git add airees/gateway/cron.py tests/test_cron.py
git commit -m "feat: add CronTrigger data model with cron expression evaluation"
```

---

### Task 10: ProactiveScheduler

**Files:**
- Create: `airees/gateway/proactive.py`
- Test: `tests/test_proactive.py`

**Step 1: Write tests**

Create `tests/test_proactive.py`:

```python
"""Tests for ProactiveScheduler — cron-triggered goal execution."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from airees.gateway.cron import CronTrigger
from airees.gateway.proactive import ProactiveScheduler


@pytest.fixture
def scheduler() -> ProactiveScheduler:
    gateway = AsyncMock()
    gateway.handle_message = AsyncMock(return_value=None)
    return ProactiveScheduler(gateway=gateway)


def test_add_trigger(scheduler: ProactiveScheduler):
    trigger = CronTrigger(
        id="t1", expression="0 9 * * *",
        goal_text="morning check", channel="telegram", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)
    assert len(scheduler.triggers) == 1


def test_remove_trigger(scheduler: ProactiveScheduler):
    trigger = CronTrigger(
        id="t1", expression="0 9 * * *",
        goal_text="test", channel="cli", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)
    assert scheduler.remove_trigger("t1") is True
    assert len(scheduler.triggers) == 0


def test_remove_nonexistent(scheduler: ProactiveScheduler):
    assert scheduler.remove_trigger("nope") is False


@pytest.mark.asyncio
async def test_evaluate_fires_due_triggers(scheduler: ProactiveScheduler):
    trigger = CronTrigger(
        id="t1", expression="* * * * *",  # Every minute
        goal_text="do it", channel="cli", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)

    await scheduler.evaluate(datetime(2026, 3, 2, 9, 0))

    scheduler.gateway.handle_message.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_skips_running_trigger(scheduler: ProactiveScheduler):
    """If a trigger's previous execution is still running, skip it."""
    trigger = CronTrigger(
        id="t1", expression="* * * * *",
        goal_text="slow task", channel="cli", recipient_id="u1",
    )
    scheduler.add_trigger(trigger)
    scheduler._running.add("t1")

    await scheduler.evaluate(datetime(2026, 3, 2, 9, 0))

    scheduler.gateway.handle_message.assert_not_called()
```

**Step 2: Implement**

Create `airees/gateway/proactive.py`:

```python
"""ProactiveScheduler — evaluate cron triggers and fire goals."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from airees.gateway.cron import CronTrigger, is_due
from airees.gateway.types import InboundMessage

log = logging.getLogger(__name__)


@dataclass
class ProactiveScheduler:
    """Evaluates cron triggers and submits matching goals via the gateway.

    Attributes:
        gateway: The Gateway instance (used to send messages).
        triggers: Active cron triggers.
    """

    gateway: Any
    triggers: list[CronTrigger] = field(default_factory=list)
    _running: set[str] = field(default_factory=set, init=False)

    def add_trigger(self, trigger: CronTrigger) -> None:
        self.triggers.append(trigger)
        log.info("Added trigger: %s (%s)", trigger.id, trigger.expression)

    def remove_trigger(self, trigger_id: str) -> bool:
        before = len(self.triggers)
        self.triggers = [t for t in self.triggers if t.id != trigger_id]
        removed = len(self.triggers) < before
        if removed:
            self._running.discard(trigger_id)
            log.info("Removed trigger: %s", trigger_id)
        return removed

    async def evaluate(self, now: datetime) -> int:
        """Check all triggers against *now* and fire matching ones.

        Returns:
            Number of triggers fired.
        """
        fired = 0
        for trigger in self.triggers:
            if trigger.id in self._running:
                log.debug("Skipping trigger %s — still running", trigger.id)
                continue

            if is_due(trigger, now):
                log.info("Firing trigger: %s (%s)", trigger.id, trigger.goal_text)
                self._running.add(trigger.id)
                try:
                    message = InboundMessage(
                        channel=trigger.channel,
                        sender_id=trigger.recipient_id,
                        text=trigger.goal_text,
                    )
                    await self.gateway.handle_message(message)
                    fired += 1
                except Exception as exc:
                    log.error("Trigger %s failed: %s", trigger.id, exc, exc_info=True)
                finally:
                    self._running.discard(trigger.id)
        return fired
```

```bash
git add airees/gateway/proactive.py tests/test_proactive.py
git commit -m "feat: add ProactiveScheduler with cron-triggered goal execution"
```

---

### Task 11: Schedule CLI Commands

**Files:**
- Modify: `airees/cli/main.py`
- Test: `tests/test_schedule_cli.py`

**Step 1: Write test**

```python
"""Tests for schedule CLI commands."""
from click.testing import CliRunner
from airees.cli.main import app


def test_schedule_group_exists():
    runner = CliRunner()
    result = runner.invoke(app, ["schedule", "--help"])
    assert result.exit_code == 0
    assert "add" in result.output
    assert "list" in result.output
    assert "remove" in result.output
```

**Step 2: Implement schedule commands in `main.py`**

Add `schedule` group with `add`, `list`, `remove` subcommands. Store triggers as JSON in `{data_dir}/triggers.json`.

```bash
git add airees/cli/main.py tests/test_schedule_cli.py
git commit -m "feat: add schedule CLI commands (add, list, remove)"
```

---

## Layer 4: Extended Channels

### Task 12: Discord Adapter

**Files:**
- Create: `airees/gateway/adapters/discord_adapter.py`
- Test: `tests/test_discord_adapter.py`

**Step 1: Write tests**

Create `tests/test_discord_adapter.py`:

```python
"""Tests for DiscordAdapter — structural tests (no live Discord)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from airees.gateway.adapters.discord_adapter import DiscordAdapter
from airees.gateway.types import OutboundMessage


def test_discord_adapter_name():
    adapter = DiscordAdapter(bot_token="fake-token")
    assert adapter.name == "discord"


def test_discord_adapter_requires_token():
    with pytest.raises(TypeError):
        DiscordAdapter()


def test_discord_set_message_handler():
    adapter = DiscordAdapter(bot_token="fake-token")
    handler = AsyncMock()
    adapter.set_message_handler(handler)
    assert adapter._handler is handler


@pytest.mark.asyncio
async def test_discord_send_without_bot():
    """send() before start() logs a warning but doesn't crash."""
    adapter = DiscordAdapter(bot_token="fake-token")
    msg = OutboundMessage(channel="discord", recipient_id="12345", text="hello")
    # Should not raise
    await adapter.send(msg)
```

**Step 2: Implement**

Create `airees/gateway/adapters/discord_adapter.py`:

```python
"""Discord channel adapter using discord.py."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from airees.gateway.types import InboundMessage, OutboundMessage

log = logging.getLogger(__name__)

MessageHandler = Callable[[InboundMessage], Awaitable[None]]


@dataclass
class DiscordAdapter:
    """Discord bot adapter following the ChannelAdapter protocol.

    Attributes:
        bot_token: Discord bot token (from Discord Developer Portal).
    """

    bot_token: str
    name: str = field(default="discord", init=False)
    _handler: MessageHandler | None = field(default=None, init=False, repr=False)
    _bot: Any = field(default=None, init=False, repr=False)

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    async def start(self) -> None:
        """Start the Discord bot. Requires discord.py."""
        try:
            import discord
        except ImportError:
            raise ImportError(
                "discord.py is required for the Discord adapter. "
                "Install it with: pip install 'airees[discord]'"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        self._bot = discord.Client(intents=intents)

        adapter = self

        @self._bot.event
        async def on_message(message: discord.Message) -> None:
            if message.author == self._bot.user:
                return
            if adapter._handler is not None:
                inbound = InboundMessage(
                    channel="discord",
                    sender_id=str(message.author.id),
                    text=message.content,
                    metadata={"guild_id": str(message.guild.id) if message.guild else "dm",
                              "channel_id": str(message.channel.id)},
                )
                await adapter._handler(inbound)

        # Run bot in background (non-blocking)
        import asyncio
        asyncio.create_task(self._bot.start(self.bot_token))
        log.info("Discord adapter started")

    async def stop(self) -> None:
        if self._bot is not None:
            await self._bot.close()
            log.info("Discord adapter stopped")

    async def send(self, message: OutboundMessage) -> None:
        if self._bot is None:
            log.warning("Discord bot not started — cannot send message")
            return

        try:
            channel = self._bot.get_channel(int(message.metadata.get("channel_id", 0)))
            if channel is None:
                user = await self._bot.fetch_user(int(message.recipient_id))
                channel = await user.create_dm()
            await channel.send(message.text)
        except Exception as exc:
            log.error("Failed to send Discord message: %s", exc, exc_info=True)
```

```bash
git add airees/gateway/adapters/discord_adapter.py tests/test_discord_adapter.py
git commit -m "feat: add Discord channel adapter"
```

---

### Task 13: Voice Pipeline — STT Module

**Files:**
- Create: `airees/voice/__init__.py`
- Create: `airees/voice/stt.py`
- Test: `tests/test_voice_stt.py`

**Step 1: Write tests**

Create `tests/test_voice_stt.py`:

```python
"""Tests for voice STT pipeline."""
from __future__ import annotations

import pytest

from airees.voice.stt import SpeechToText


def test_stt_creation():
    stt = SpeechToText()
    assert stt.model_size == "base"


def test_stt_creation_custom_model():
    stt = SpeechToText(model_size="small")
    assert stt.model_size == "small"


def test_stt_transcribe_no_faster_whisper(monkeypatch):
    """Without faster-whisper installed, transcribe raises ImportError."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("No module named 'faster_whisper'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    stt = SpeechToText()
    with pytest.raises(ImportError, match="faster-whisper"):
        stt.transcribe(b"fake audio bytes")
```

**Step 2: Implement**

Create `airees/voice/__init__.py`:
```python
"""Voice processing — speech-to-text and text-to-speech."""
```

Create `airees/voice/stt.py`:

```python
"""Speech-to-text using faster-whisper."""
from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SpeechToText:
    """Transcribe audio to text using faster-whisper.

    Attributes:
        model_size: Whisper model size (tiny, base, small, medium, large).
    """

    model_size: str = "base"
    _model: object | None = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise ImportError(
                    "faster-whisper is required for voice support. "
                    "Install it with: pip install 'airees[voice]'"
                )
            self._model = WhisperModel(self.model_size, compute_type="int8")
            log.info("Loaded Whisper model: %s", self.model_size)
        return self._model

    def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio bytes (WAV or OGG format).
            language: Language code for transcription.

        Returns:
            Transcribed text.
        """
        model = self._get_model()

        # Write to temp file (faster-whisper requires a file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            segments, _info = model.transcribe(temp_path, language=language)
            text = " ".join(segment.text.strip() for segment in segments)
            log.info("Transcribed %d bytes -> %d chars", len(audio_data), len(text))
            return text
        finally:
            Path(temp_path).unlink(missing_ok=True)
```

```bash
git add airees/voice/__init__.py airees/voice/stt.py tests/test_voice_stt.py
git commit -m "feat: add speech-to-text module using faster-whisper"
```

---

### Task 14: Voice Pipeline — TTS Module

**Files:**
- Create: `airees/voice/tts.py`
- Test: `tests/test_voice_tts.py`

**Step 1: Write tests**

Create `tests/test_voice_tts.py`:

```python
"""Tests for voice TTS pipeline."""
from __future__ import annotations

import pytest

from airees.voice.tts import TextToSpeech


def test_tts_creation():
    tts = TextToSpeech()
    assert tts.voice is not None


def test_tts_synthesize_no_piper(monkeypatch):
    """Without piper-tts installed, synthesize raises ImportError."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "piper" in name:
            raise ImportError("No module named 'piper'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    tts = TextToSpeech()
    with pytest.raises(ImportError, match="piper"):
        tts.synthesize("Hello world")
```

**Step 2: Implement**

Create `airees/voice/tts.py`:

```python
"""Text-to-speech using piper-tts."""
from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class TextToSpeech:
    """Synthesize text to audio using piper-tts.

    Attributes:
        voice: Piper voice model name.
    """

    voice: str = "en_US-lessac-medium"
    _engine: object | None = None

    def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (WAV format).

        Args:
            text: Text to synthesize.

        Returns:
            WAV audio bytes.
        """
        try:
            from piper import PiperVoice
        except ImportError:
            raise ImportError(
                "piper-tts is required for voice synthesis. "
                "Install it with: pip install 'airees[voice]'"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            voice = PiperVoice.load(self.voice)
            with open(temp_path, "wb") as wav_file:
                voice.synthesize(text, wav_file)

            audio_data = Path(temp_path).read_bytes()
            log.info("Synthesized %d chars -> %d bytes", len(text), len(audio_data))
            return audio_data
        finally:
            Path(temp_path).unlink(missing_ok=True)
```

```bash
git add airees/voice/tts.py tests/test_voice_tts.py
git commit -m "feat: add text-to-speech module using piper-tts"
```

---

### Task 15: Telegram Voice Extension

Extend TelegramAdapter to handle voice messages.

**Files:**
- Modify: `airees/gateway/adapters/telegram_adapter.py`
- Test: `tests/test_telegram_voice.py`

**Step 1: Write tests**

Create `tests/test_telegram_voice.py`:

```python
"""Tests for Telegram voice message handling."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from airees.gateway.adapters.telegram_adapter import TelegramAdapter


def test_telegram_has_voice_support_flag():
    adapter = TelegramAdapter(bot_token="fake")
    assert hasattr(adapter, "voice_enabled")


def test_telegram_voice_disabled_by_default():
    adapter = TelegramAdapter(bot_token="fake")
    assert adapter.voice_enabled is False


def test_telegram_voice_can_be_enabled():
    adapter = TelegramAdapter(bot_token="fake", voice_enabled=True)
    assert adapter.voice_enabled is True
```

**Step 2: Implement**

Add `voice_enabled: bool = False` field to TelegramAdapter. When `voice_enabled=True` and a voice message arrives:
1. Download voice OGG via Telegram Bot API
2. Lazy-load SpeechToText, transcribe to text
3. Create InboundMessage with transcribed text + voice attachment
4. After getting response, lazy-load TextToSpeech, synthesize, send as voice

```bash
git add airees/gateway/adapters/telegram_adapter.py tests/test_telegram_voice.py
git commit -m "feat: add voice message support to Telegram adapter"
```

---

### Task 16: Wire Everything into Bootstrap and Exports

**Files:**
- Modify: `airees/cli/bootstrap.py`
- Modify: `airees/__init__.py`
- Test: `tests/test_phase7_exports.py`

**Step 1: Write tests**

Create `tests/test_phase7_exports.py`:

```python
"""Tests for Phase 7 exports."""
from __future__ import annotations


def test_learning_exports():
    from airees import AutoSkillCapture, ModelPreference
    assert AutoSkillCapture is not None
    assert ModelPreference is not None


def test_knowledge_exports():
    from airees.knowledge.store import KnowledgeStore, KnowledgeResult
    assert KnowledgeStore is not None
    assert KnowledgeResult is not None


def test_cron_exports():
    from airees.gateway.cron import CronTrigger, is_due
    assert CronTrigger is not None
    assert is_due is not None


def test_proactive_exports():
    from airees.gateway.proactive import ProactiveScheduler
    assert ProactiveScheduler is not None


def test_discord_exports():
    from airees.gateway.adapters.discord_adapter import DiscordAdapter
    assert DiscordAdapter is not None


def test_voice_exports():
    from airees.voice.stt import SpeechToText
    from airees.voice.tts import TextToSpeech
    assert SpeechToText is not None
    assert TextToSpeech is not None
```

**Step 2: Update `__init__.py`**

Add imports and `__all__` entries for:
- `AutoSkillCapture` from `airees.gateway.learning`
- `ModelPreference` from `airees.gateway.model_preference`
- `KnowledgeStore`, `KnowledgeResult` from `airees.knowledge.store`
- `CronTrigger` from `airees.gateway.cron`
- `ProactiveScheduler` from `airees.gateway.proactive`

**Step 3: Update `bootstrap_gateway()`**

Wire KnowledgeStore into the ConversationManager:

```python
knowledge_store = KnowledgeStore(data_dir=data_dir / "knowledge")

manager = ConversationManager(
    router=orch.router,
    event_bus=orch.event_bus,
    soul_path=data_dir / "SOUL.md",
    user_path=data_dir / "USER.md",
    orchestrator=orch,
    skill_store=skill_store,
    cost_tracker=cost_tracker,
    model_preference=model_preference,
    knowledge_store=knowledge_store,
)
```

Register Discord adapter if token is available:

```python
import os
discord_token = os.environ.get("DISCORD_BOT_TOKEN")
if discord_token:
    from airees.gateway.adapters.discord_adapter import DiscordAdapter
    gateway.adapters.register(DiscordAdapter(bot_token=discord_token))
```

```bash
git add airees/__init__.py airees/cli/bootstrap.py tests/test_phase7_exports.py
git commit -m "feat: wire Phase 7 components into bootstrap and update exports"
```

---

### Task 17: Integration and E2E Tests

**Files:**
- Create: `tests/test_phase7_integration.py`

**Step 1: Write integration tests**

```python
"""Phase 7 integration tests — full pipeline with learning + knowledge."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from airees.gateway.conversation import ConversationManager
from airees.gateway.cost_tracker import CostTracker
from airees.gateway.learning import AutoSkillCapture
from airees.gateway.model_preference import ModelPreference
from airees.gateway.types import InboundMessage
from airees.knowledge.store import KnowledgeStore
from airees.skill_store import SkillStore
from tests.test_conversation_manager import FakeRouter, FakeOrchestrator


@pytest.mark.asyncio
async def test_full_pipeline_with_knowledge_and_skills():
    """Message flows through skill check -> knowledge enrichment -> router."""
    tmp = Path(tempfile.mkdtemp())

    # Set up knowledge
    kb = KnowledgeStore(data_dir=tmp / "knowledge")
    doc = tmp / "info.txt"
    doc.write_text("Project deadline is March 15th.", encoding="utf-8")
    kb.ingest(doc)

    # Set up skill store
    skills_dir = tmp / "skills"
    skills_dir.mkdir()
    store = SkillStore(skills_dir=skills_dir)

    router = FakeRouter(reply="Got it, deadline is March 15th")
    mgr = ConversationManager(
        router=router,
        event_bus=None,
        soul_path=Path("/nonexistent/SOUL.md"),
        user_path=Path("/nonexistent/USER.md"),
        skill_store=store,
        cost_tracker=CostTracker(),
        model_preference=ModelPreference(),
        knowledge_store=kb,
    )

    msg = InboundMessage(channel="cli", sender_id="user-1", text="when is the deadline?")
    response = await mgr.handle(msg)

    assert response.text == "Got it, deadline is March 15th"
    # Knowledge should have enriched the system prompt
    assert len(router._calls) == 1
    system = router._calls[0]["system"]
    assert "deadline" in system.lower() or "march" in system.lower()


@pytest.mark.asyncio
async def test_auto_skill_capture_after_orchestrated():
    """After orchestrated goal, skill is auto-captured."""
    tmp = Path(tempfile.mkdtemp())
    skills_dir = tmp / "skills"
    skills_dir.mkdir()
    store = SkillStore(skills_dir=skills_dir)
    capture = AutoSkillCapture(skill_store=store)

    capture.maybe_create_skill(
        goal_text="analyze the sales report",
        result_text="Sales increased 15% QoQ",
        success=True,
    )

    # Skill should now exist
    results = store.search("analyze sales report")
    assert len(results) >= 1
    assert results[0].success_rate == 1.0
```

**Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL tests PASS (439 existing + ~35 new)

**Step 3: Commit**

```bash
git add tests/test_phase7_integration.py
git commit -m "test: add Phase 7 integration tests for learning + knowledge pipeline"
```

---

### Task 18: Final Verification

**Step 1: Run the full test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: 475+ tests PASS, 0 failures.

**Step 2: Verify all CLI commands work**

```bash
airees --help
airees kb --help
airees schedule --help
```

**Step 3: Verify imports work**

```bash
python -c "from airees import AutoSkillCapture, ModelPreference; print('Learning OK')"
python -c "from airees.knowledge.store import KnowledgeStore; print('Knowledge OK')"
python -c "from airees.gateway.cron import CronTrigger; print('Cron OK')"
python -c "from airees.gateway.proactive import ProactiveScheduler; print('Proactive OK')"
python -c "from airees.gateway.adapters.discord_adapter import DiscordAdapter; print('Discord OK')"
python -c "from airees.voice.stt import SpeechToText; print('STT OK')"
python -c "from airees.voice.tts import TextToSpeech; print('TTS OK')"
```

**Step 4: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: Phase 7 final verification — all tests passing"
```
