# Phase 4: Memory & Learning System Design

> Wire the training corpus, skills system, progressive compression, and self-reflection into Airees' live execution pipeline so the Brain can search knowledge, create/reuse skills, manage context budgets, and evolve over time.

## Status

- **Created:** 2026-03-01
- **Approach:** Four-subsystem integration — Corpus Retrieval, Skills, Progressive Compression, Self-Reflection

## Context

Phase 1 built the Brain/Coordinator/Worker architecture. Phase 2 added worker tools, parallel execution, and resilience. Phase 3 wired factory primitives (QualityGate, ProjectState, ContextBudget, Scheduler, DecisionDocument, FeedbackLoop) into the live orchestration pipeline.

The Brain design doc (2026-03-01) specifies a complete memory/learning system — skills, corpus retrieval, progressive compression, self-reflection — but none of these are implemented. The training corpus (270 files, 53,570 lines across 18 categories) is completely disconnected from runtime. Workers receive no best-practice guidance. The Brain cannot create or search skills. Context grows unbounded during long goals. SOUL.md never updates.

Phase 4 connects all of this.

### Current Gaps

| Feature | Design Status | Implementation |
|---------|--------------|----------------|
| Corpus Retrieval | Designed in brain-design.md | Not started |
| Skills System | Designed in brain-design.md | Not started |
| Progressive Compression | Designed in brain-design.md | Not started |
| Self-Reflection (update_soul) | Designed in brain-design.md | Not started |
| Daily Memory Log | Designed in brain-design.md | Not started |

### Existing Infrastructure We Build On

| Component | File | What It Provides |
|-----------|------|-----------------|
| `build_brain_prompt()` | brain/prompt.py | `active_skill` parameter (already accepts skill content) |
| `build_worker_prompt()` | coordinator/worker_builder.py | `skill_content` parameter (already accepts skill injection) |
| `ContextBudget` | context_budget.py | Token tracking with `exceeds_threshold()` |
| `Runner` | runner.py | Token usage tracking, context warning events |
| `FileMemoryStore` | memory/file_store.py | File-based per-agent memory |
| `SQLiteRunStore` | memory/sqlite_store.py | Run history persistence |
| `Soul` | soul.py | SOUL.md loading with YAML frontmatter parsing |
| `FeedbackLoop` | feedback.py | Execution outcome tracking |
| `DecisionDocument` | decision_doc.py | Audit trail |
| `BrainOrchestrator` | brain/orchestrator.py | Phase 3 lifecycle hooks |
| Training Corpus | training/ (270 files) | 18 categories of best practices |

## Architecture

### Integration Map

```
submit_goal()
  |-- search_skills(goal) -> find matching skill
  |-- search_corpus(goal) -> get relevant best practices
  |-- Both injected into Brain's planning prompt

execute_goal()
  |-- plan()
  |   |-- Brain uses active_skill + corpus context to create better plans
  |
  |-- _execute_wave()
  |   |-- For each worker:
  |       |-- search_corpus(task_description) -> inject into worker prompt
  |       |-- Worker executes with corpus guidance
  |       |-- ContextCompressor checks budget after each turn
  |       |   |-- 60%: summarize completed outputs
  |       |   |-- 75%: collapse finished task chains
  |       |   |-- 85%: checkpoint to SQLite, reset
  |       |   |-- 95%: emergency trim to current task only
  |
  |-- _evaluate()
  |   |-- Brain evaluates with full context
  |
  |-- Completion
      |-- Brain calls create_skill() to distill successful pipeline
      |-- Brain calls update_soul() to reflect on execution
      |-- Daily memory log written to data/memory/{date}.md
```

## Subsystem 1: Corpus Retrieval

### Search Engine

BM25 keyword search over the training corpus. Pure Python, no external services.

**Why BM25 over vector search:**
- No embedding model dependency (no OpenAI/Cohere API, no local GPU)
- Fast enough for 270 documents (sub-100ms)
- Good enough for keyword-based retrieval of structured training files
- Zero infrastructure — just a Python library (`rank_bm25`)

```python
@dataclass
class CorpusSearchEngine:
    corpus_dir: Path
    _index: BM25Okapi | None = field(default=None, init=False)
    _documents: list[CorpusDocument] = field(default_factory=list, init=False)

    def _build_index(self) -> None:
        """Scan corpus_dir for .md files, tokenize, build BM25 index."""

    def search(self, query: str, top_k: int = 3) -> list[CorpusResult]:
        """Search corpus, return top-k results with path + score + excerpt."""
```

**CorpusDocument** stores: `path`, `title`, `category`, `content`, `tokens` (whitespace-split for BM25).

**CorpusResult** stores: `path`, `title`, `category`, `score`, `excerpt` (first 500 chars of content).

### Brain Tool: `search_corpus`

```python
{
    "name": "search_corpus",
    "description": "Search the training corpus for best practices relevant to a topic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "top_k": {"type": "integer", "default": 3, "description": "Number of results"}
        },
        "required": ["query"]
    }
}
```

Returns formatted markdown with file titles, categories, and excerpts.

### Worker Corpus Injection

Coordinator automatically searches corpus when building worker prompts:

```python
# In worker_builder.py or orchestrator
corpus_results = corpus_engine.search(task_description, top_k=2)
corpus_content = format_corpus_results(corpus_results)
prompt = build_worker_prompt(
    task_title=task["title"],
    task_description=task["description"],
    agent_role=task["agent_role"],
    skill_content=skill_content,      # existing
    corpus_context=corpus_content,     # new parameter
)
```

### Index Lifecycle

- Built lazily on first `search()` call
- Cached in memory for the process lifetime
- Invalidated if corpus files change (optional: check mtime of corpus_dir)
- ~270 documents, ~53K lines — fast to build, small memory footprint

## Subsystem 2: Skills System

### Skill Storage

```
data/skills/
  nextjs-saas-app.md
  api-integration.md
  ...
```

### Skill Format

```markdown
---
name: nextjs-saas-app
description: Build and deploy a Next.js SaaS with auth, payments, and landing page
version: 3
created: "2026-03-01"
last_updated: "2026-03-15"
success_rate: 0.85
iterations_avg: 2.3
total_executions: 7
models_preferred:
  research: llama-3.3-70b
  code: claude-haiku-4-5
  review: claude-haiku-4-5
tools_required:
  - web_search
  - file_write
triggers:
  - "build a saas"
  - "nextjs application"
---

# Next.js SaaS App Pipeline

## Task Graph
1. Research — Analyze requirements, find best libraries
2. Scaffold — Create Next.js project
3. Auth (depends: 2) — Implement authentication
...

## Lessons Learned
- v1: Used custom auth, took 4 iterations. Switched to Clerk in v2.

## Quality Gates
- Code tasks: min_score 7, test coverage > 80%

## Known Pitfalls
- Don't use SQLite for SaaS. Always PostgreSQL.
```

### Skill Search Engine

Reuses the same BM25 engine as corpus search, but indexed over skills:

```python
@dataclass
class SkillSearchEngine:
    skills_dir: Path
    _index: BM25Okapi | None = field(default=None, init=False)
    _skills: list[SkillDocument] = field(default_factory=list, init=False)

    def _build_index(self) -> None:
        """Scan skills_dir, parse YAML frontmatter, index triggers + description + content."""

    def search(self, query: str, top_k: int = 3) -> list[SkillResult]:
        """Search skills, return top-k matches with name + score + frontmatter."""

    def invalidate(self) -> None:
        """Force index rebuild (called after skill create/update)."""
```

**SkillDocument** stores: `path`, `name`, `description`, `version`, `triggers`, `success_rate`, `content`, `frontmatter` (full YAML dict).

**SkillResult** stores: `name`, `path`, `score`, `success_rate`, `version`, `content`.

### Brain Tools

**`search_skills`** — Find skills matching a goal:
```python
{
    "name": "search_skills",
    "description": "Search for existing skills that match this goal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Goal description to match against skills"}
        },
        "required": ["query"]
    }
}
```

**`create_skill`** — Distill successful execution into a reusable skill:
```python
{
    "name": "create_skill",
    "description": "Create a new skill from a successful goal execution.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name (kebab-case)"},
            "description": {"type": "string", "description": "What this skill does"},
            "triggers": {"type": "array", "items": {"type": "string"}, "description": "Goal phrases that should match this skill"},
            "task_graph": {"type": "string", "description": "Markdown task graph with dependencies"},
            "lessons_learned": {"type": "string", "description": "What worked, what didn't"},
            "quality_gates": {"type": "string", "description": "Quality criteria"},
            "known_pitfalls": {"type": "string", "description": "Warnings for future executions"}
        },
        "required": ["name", "description", "triggers", "task_graph"]
    }
}
```

**`update_skill`** — Update an existing skill with new learnings:
```python
{
    "name": "update_skill",
    "description": "Update an existing skill with improvements from the latest execution.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Existing skill name"},
            "lessons_learned": {"type": "string", "description": "New lessons to append"},
            "known_pitfalls": {"type": "string", "description": "New pitfalls to append"},
            "task_graph": {"type": "string", "description": "Updated task graph (replaces existing)"}
        },
        "required": ["name"]
    }
}
```

### Skill Lifecycle in Orchestrator

1. `submit_goal()` — Brain calls `search_skills(goal)`. If match found, loaded as `active_skill`.
2. `plan()` — Brain uses skill as template for task graph creation.
3. `_execute_wave()` — Skill content injected into worker prompts.
4. Completion — Brain calls `create_skill()` or `update_skill()` based on execution outcome.
5. `update_skill()` bumps version, updates `success_rate`, appends lessons.

### Skill Trust

- Skills created by Airees (`data/skills/`) are trusted by default
- Content sanitized on create: strip tool call JSON, identity overrides
- No external skill import in Phase 4 (future work)

## Subsystem 3: Progressive Compression

### Compression Engine

```python
@dataclass
class ContextCompressor:
    router: Any  # ModelRouter for Haiku summarization calls
    budget: ContextBudget

    async def compress(self, messages: list[dict], stage: int) -> list[dict]:
        """Compress messages according to the given stage."""

    def detect_stage(self) -> int:
        """Return compression stage based on budget usage percent."""
        # 0 = no compression needed
        # 1 = 60%+ usage
        # 2 = 75%+ usage
        # 3 = 85%+ usage
        # 4 = 95%+ usage
```

### Compression Stages

| Stage | Trigger | Action | Implementation |
|-------|---------|--------|----------------|
| 0 | < 60% | No compression | Pass through |
| 1 | 60-74% | Summarize completed outputs | Haiku call: "Summarize this output in 2 lines" |
| 2 | 75-84% | Collapse finished chains | Group completed tasks, replace with one-liner each |
| 3 | 85-94% | Checkpoint + reset | Save full messages to SQLite, reload only active tasks |
| 4 | 95%+ | Emergency trim | Keep only current task + latest assistant message |

### Stage 1: Summarize Outputs

Replace completed worker output messages with Haiku-generated 2-line summaries:

```python
async def _summarize_output(self, output: str) -> str:
    """Use Haiku to compress a worker output to 2 lines."""
    response = await self.router.create_message(
        model=ModelConfig(model_id="claude-haiku-4-5-20251001"),
        system="Summarize this output in exactly 2 lines. Preserve key facts.",
        messages=[{"role": "user", "content": output}],
    )
    return extract_text(response)
```

### Stage 2: Collapse Task Chains

Group completed task results into single-line summaries:

```
Before: [task1_prompt, task1_output, task2_prompt, task2_output, task3_prompt, task3_output]
After:  ["Completed: task1 (researched APIs), task2 (scaffolded project), task3 (implemented auth)"]
```

### Stage 3: Checkpoint to SQLite

```python
async def _checkpoint(self, messages: list[dict], goal_id: str) -> list[dict]:
    """Save full message history to SQLite, return only active task context."""
    await self.store.save_checkpoint(goal_id, json.dumps(messages))
    # Return only: system message + active task prompt + last 2 assistant messages
```

### Stage 4: Emergency Trim

Keep only the current task instruction and the last assistant response. Everything else discarded.

### Integration Point

In `Runner._run_loop()`, after each turn:

```python
# After tracking token usage
if agent.context_budget:
    stage = compressor.detect_stage()
    if stage > 0:
        messages = await compressor.compress(messages, stage)
        self.event_bus.emit(EventType.CONTEXT_WARNING, {
            "stage": stage, "usage_percent": budget.usage_percent
        })
```

## Subsystem 4: Self-Reflection

### Brain Tool: `update_soul`

```python
{
    "name": "update_soul",
    "description": "Reflect on execution and update SOUL.md with new capabilities, strategy, and lessons.",
    "input_schema": {
        "type": "object",
        "properties": {
            "capabilities_update": {
                "type": "object",
                "properties": {
                    "skills_mastered": {"type": "integer"},
                    "goals_completed": {"type": "integer"},
                    "total_iterations": {"type": "integer"}
                }
            },
            "strategy_update": {"type": "string", "description": "Updated strategy section"},
            "lesson": {"type": "string", "description": "Key lesson from this execution"}
        }
    }
}
```

### Soul Update Logic

```python
def update_soul(soul_path: Path, updates: dict) -> Soul:
    """Load current SOUL.md, apply updates, write back."""
    soul = load_soul(soul_path)
    raw = soul.raw

    # Update Capabilities section counters
    if "capabilities_update" in updates:
        # Parse and increment counters in markdown

    # Update Strategy section
    if "strategy_update" in updates:
        # Replace strategy content

    # Append lesson to a Lessons section
    if "lesson" in updates:
        # Append to lessons list

    # Bump version in YAML frontmatter
    # Write back to soul_path
    return load_soul(soul_path)
```

### Genesis Hash Guard

SOUL.md's core purpose section has a genesis hash in the YAML frontmatter. On each reflection:

1. Hash the current "Core Purpose" section
2. Compare against `genesis_hash` in frontmatter
3. If they don't match (someone or something changed core purpose), log a warning and re-anchor from the original

This prevents SOUL drift from injection or accumulated small changes.

### Daily Memory Log

On goal completion or daily reflection trigger:

```python
async def _write_daily_log(self, goal_id: str) -> None:
    date = datetime.now().strftime("%Y-%m-%d")
    log_path = self.memory_dir / f"{date}.md"

    entry = f"""
## Goal: {goal_id}
- **Completed:** {datetime.now().isoformat()}
- **Iterations:** {iteration_count}
- **Skills created/updated:** {skills_list}
- **Cost:** {total_cost}
- **Key decisions:** {decisions_summary}
- **Lesson:** {key_lesson}
"""
    # Append to daily log (multiple goals per day)
    with open(log_path, "a") as f:
        f.write(entry)
```

### Reflection Trigger

The GoalDaemon (Phase 3) already polls every 30s. Add a daily reflection check:

```python
async def _poll_once(self) -> None:
    # Existing: find pending goals, find interrupted goals
    # New: check if daily reflection is due
    if self._should_reflect():
        await self._trigger_reflection()
```

## New Brain Tools (Summary)

| Tool | Purpose | When Called |
|------|---------|------------|
| `search_corpus` | Find relevant training material | Planning, worker building |
| `search_skills` | Find matching skills | Goal submission |
| `create_skill` | Distill successful pipeline | Goal completion |
| `update_skill` | Improve existing skill | Goal completion (skill existed) |
| `update_soul` | Self-reflection | Goal completion, daily |

## New Event Types

```python
CORPUS_SEARCH = "corpus.search"
SKILL_MATCHED = "skill.matched"
SKILL_CREATED = "skill.created"
SKILL_UPDATED = "skill.updated"
CONTEXT_COMPRESSED = "context.compressed"
SOUL_UPDATED = "soul.updated"
REFLECTION_TRIGGERED = "reflection.triggered"
```

## Files Created

| File | Purpose |
|------|---------|
| `corpus_search.py` | CorpusSearchEngine with BM25 index |
| `skill_store.py` | SkillSearchEngine + create/update logic |
| `context_compressor.py` | Progressive compression engine |
| `brain/reflection.py` | Soul update + daily memory log |

## Files Modified

| File | Changes |
|------|---------|
| `brain/orchestrator.py` | Wire corpus search, skill search, reflection into lifecycle |
| `brain/prompt.py` | Add `corpus_context` parameter to `build_brain_prompt()` |
| `brain/tools.py` | Add 5 new tool definitions |
| `coordinator/worker_builder.py` | Add `corpus_context` parameter to `build_worker_prompt()` |
| `runner.py` | Wire ContextCompressor into turn loop |
| `events.py` | Add 7 new event types |
| `goal_daemon.py` | Add daily reflection trigger |
| `soul.py` | Add `update_soul()` function, genesis hash support |
| `__init__.py` | Export new classes |

## Test Files

| File | Coverage |
|------|----------|
| `tests/test_corpus_search.py` | BM25 index build, search, empty corpus, top-k |
| `tests/test_skill_store.py` | Create, search, update, versioning, YAML parsing |
| `tests/test_context_compressor.py` | All 4 stages, stage detection, checkpoint/restore |
| `tests/test_reflection.py` | Soul update, genesis hash guard, daily log |
| `tests/test_phase4_integration.py` | Full lifecycle with all subsystems |

## Dependencies

**New:**
- `rank-bm25` — BM25 keyword search (pure Python, no C extensions)

**Existing (no changes):**
- `aiosqlite` — SQLite for checkpoints
- `pyyaml` — YAML frontmatter parsing

## Data Directories

```
data/
  skills/           # Skill markdown files (NEW)
  memory/
    feedback.md     # Existing (Phase 3)
    2026-03-01.md   # Daily memory logs (NEW)
  states/           # Existing (Phase 3)
  decisions/        # Existing (Phase 3)
  SOUL.md           # Updated with genesis hash, reflection sections
```

## Design Decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Search engine | BM25 (rank_bm25) | No dependencies, fast for 270 docs, good enough |
| Corpus indexing | File-level granularity | Training files are well-structured, ~200 lines avg |
| Skill storage | Markdown + YAML frontmatter | Human-readable, git-friendly, matches existing patterns |
| Compression model | Haiku for summaries | Cheapest viable for text compression |
| Checkpoint storage | SQLite | Already in use, atomic writes, queryable |
| Soul guard | Genesis hash | Prevents identity drift from injection/accumulation |
| Reflection trigger | Goal completion + daily timer | Frequent enough for learning, not excessive |
| Skill trust | Only self-created trusted | No external import in Phase 4 (future work) |
| Index caching | In-memory, process lifetime | Fast enough to rebuild on restart |
