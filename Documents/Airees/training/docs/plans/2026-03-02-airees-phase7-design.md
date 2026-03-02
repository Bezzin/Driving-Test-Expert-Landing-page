# Airees Phase 7: Full Stack Autonomous Agent — Design

## Goal

Close the learning loop and extend Airees into a fully autonomous personal agent — one that learns from every interaction, searches personal knowledge, acts proactively on schedules, and communicates through Discord and voice.

## Context

Airees (Phases 1-6) provides: brain orchestrator with plan-execute-evaluate loops, multi-agent delegation via task DAGs, memory (SQLite + file-based), feedback loops, skill store (BM25), corpus search (BM25), model routing with fallback (Anthropic + OpenRouter), context compression (4-stage cascade), quality gates, event bus, MCP client, CLI with 8+ command groups, heartbeat daemon, goal daemon, gateway with channel adapters (CLI + Telegram), conversation manager with complexity routing, personal context (SOUL.md + USER.md), session management with TTL, cost tracking. 439 tests passing.

**Key gap:** The learning infrastructure (SkillStore, FeedbackLoop, CorpusSearch) exists but is not wired into the conversation path. The gateway's ConversationManager does not consult skills, past feedback, or semantic memory when handling messages. Cost tracking records data but does not optimize.

## Architecture

```
+-------------------------------------------------------------+
|                        CHANNELS                              |
|  [CLI]  [Telegram+Voice]  [Discord]  [Proactive Push]       |
+----------------------------+--------------------------------+
                             | InboundMessage
                    +--------v---------+
                    |     GATEWAY      |
                    +--------+---------+
                             |
                    +--------v---------+
                    | CONVERSATION MGR |  <-- NEW: skill lookup
                    |  + SkillStore    |  <-- NEW: knowledge search
                    |  + KnowledgeBase |  <-- NEW: adaptive routing
                    +--------+---------+
                             |
              +--------------v--------------+
              |        AIREES BRAIN         |
              |  Intent -> Plan -> Execute  |
              +--------------+--------------+
                             |
                    +--------v---------+
                    |   FEEDBACK LOOP  |  <-- NEW: wired to gateway
                    |  + Skill Create  |  <-- NEW: auto-capture
                    +--------+---------+
                             |
              +--------------v--------------+
              |      KNOWLEDGE STORE        |  NEW
              |  ChromaDB + Embeddings      |
              |  Personal doc ingestion     |
              +-----------------------------+
              |    PROACTIVE SCHEDULER      |  NEW
              |  Cron triggers -> Gateway   |
              |  Background goal streaming  |
              +-----------------------------+
```

## Components

### Layer 1: Learning Loop (wire existing infrastructure)

#### 1a. Skill-Aware Routing

ConversationManager gains a `SkillStore` reference. Before routing to the brain:
1. Query SkillStore with the user's message text
2. If a skill scores above a confidence threshold (e.g. 0.7), execute the cached workflow directly — skip brain planning
3. Use the skill's recorded model tier (could be Haiku) instead of escalating

This delivers the "gets cheaper" goal: proven patterns reuse cached plans at the cheapest model tier.

#### 1b. Auto-Skill Capture

After every successful goal completion via the brain:
1. FeedbackLoop.record() is already called — add a hook
2. If the goal succeeded and the pattern is novel (no existing skill match above 0.5), create a new skill via SkillStore.create()
3. Record the model tier that succeeded, so future invocations can use the same or cheaper tier

#### 1c. Adaptive Model Selection

CostTracker + FeedbackLoop data feed a heuristic:
- Track success rate per (complexity_tier, pattern_category) pair
- If a message pattern has succeeded with Haiku 3+ times without escalation, auto-downgrade from Sonnet to Haiku
- If a pattern fails at Haiku 2+ times, auto-upgrade to Sonnet
- Store these learned preferences in SQLite alongside cost records

### Layer 2: Knowledge Base (ChromaDB + semantic search)

#### 2a. KnowledgeStore

New module wrapping ChromaDB for personal document management:
- `ingest(path: Path)` — extract text from PDF/Markdown/text files, chunk, embed, store
- `search(query: str, top_k: int = 3) -> list[KnowledgeResult]` — semantic search
- `delete(doc_id: str)` — remove ingested document
- `stats() -> dict` — collection size, document count

Dependencies: `chromadb`, `sentence-transformers`, `pymupdf` (PDF extraction).

Embedding model: `all-MiniLM-L6-v2` (fast, 384-dim, runs on CPU).

Storage: `{data_dir}/knowledge/` directory, ChromaDB persistent client.

#### 2b. Context Enrichment

ConversationManager's `handle()` method queries the KnowledgeStore with the user's message before building the system prompt. Top 3 results are injected as:

```
Relevant knowledge:
- [source: notes.md] "User is working on the Airees project..."
- [source: meeting.pdf] "Budget approved for Q2 deployment..."
```

This gives Airees deep contextual awareness without stuffing everything into USER.md.

#### 2c. CLI Commands

```
airees kb ingest <path>     # Ingest file or directory
airees kb search <query>    # Search knowledge base
airees kb stats             # Show collection stats
airees kb delete <doc-id>   # Remove a document
```

### Layer 3: Proactive Agent (scheduled actions + push notifications)

#### 3a. CronTrigger

```python
@dataclass(frozen=True)
class CronTrigger:
    expression: str        # "0 9 * * *" (9am daily)
    goal_text: str         # "Check my calendar and summarize today"
    channel: str           # "telegram"
    recipient_id: str      # User ID for push notification
    enabled: bool = True
```

Stored in SQLite alongside goals.

#### 3b. ProactiveScheduler

Extends the existing Scheduler:
- On each heartbeat tick (default 15s), evaluate all CronTriggers
- When a trigger fires: submit as a goal, execute, route result back to the user's channel via Gateway
- Backpressure: skip if a trigger's previous execution is still running

#### 3c. Background Goal Streaming

When a complex goal is running via `_run_orchestrated`:
- Subscribe to EventBus events (step_completed, worker_finished)
- Forward progress updates to the user's channel as intermediate messages
- User sees "Planning... Step 1/3 complete... Finalizing..." instead of silence

#### 3d. CLI Commands

```
airees schedule add "0 9 * * *" "summarize my day" --channel telegram
airees schedule list
airees schedule remove <trigger-id>
```

### Layer 4: Extended Channels (Discord + Voice)

#### 4a. DiscordAdapter

Uses `discord.py` (async-native). Follows existing ChannelAdapter protocol:
- `start()` — connect to Discord gateway, register event handlers
- `send(OutboundMessage)` — send message to the target channel/DM
- Message handler: convert Discord Message to InboundMessage, invoke callback

Configuration: `DISCORD_BOT_TOKEN` env var. Single-server personal bot.

#### 4b. Voice Support (Telegram)

Voice is a decorator on the existing TelegramAdapter, not a separate adapter:

1. TelegramAdapter detects `voice` message type
2. Download OGG file via Telegram Bot API
3. Convert to WAV via `pydub` (or direct OGG decode)
4. Run `faster-whisper` for STT (local, model: `base` or `small`)
5. Create InboundMessage with transcribed text + original voice as attachment
6. Normal pipeline processes the text
7. Run `piper-tts` on the response (local, no API key)
8. Send back as voice message via `sendVoice`

All processing is local — no external API calls for voice. Only cost is the Claude API call for the text content.

Dependencies: `faster-whisper`, `piper-tts`, `pydub`.

## Dependencies

New required:
- chromadb >= 0.5.0 (vector store)
- sentence-transformers >= 3.0.0 (embeddings)
- pymupdf >= 1.24.0 (PDF extraction)

New optional:
- discord.py >= 2.4.0 (Discord adapter)
- faster-whisper >= 1.0.0 (STT)
- piper-tts >= 1.2.0 (TTS)
- pydub >= 0.25.1 (audio conversion)

Existing (already in project):
- anthropic, pydantic, aiosqlite, click, pyyaml, httpx, rank-bm25
- python-telegram-bot (already optional)

## Success Criteria

1. Ask a question that matches a previous successful goal — Airees reuses the skill, skips brain planning, responds faster and cheaper
2. Ingest a PDF, then ask a question about its contents — Airees finds and uses the relevant knowledge
3. Set a cron trigger for 9am daily — Airees sends a proactive message via Telegram at 9am
4. Send a message via Discord — get an intelligent response
5. Send a voice message via Telegram — get a voice response back
6. After 50+ interactions, observe measurable cost reduction (model tier downgrades for learned patterns)
7. All existing 439 tests continue passing
8. New test coverage >= 80%

## Out of Scope (future phases)

- WhatsApp adapter (unofficial APIs too fragile)
- Email adapter
- Web UI dashboard
- Mobile companion app
- Browser automation (Playwright-based)
- Multi-user support / user isolation
- Plugin/skill marketplace
- Cloud deployment (Docker, Railway)
