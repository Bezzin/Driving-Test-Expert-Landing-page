# Airees Phase 6: Personal Autonomous Agent — Design

## Goal

Transform Airees from an orchestration engine into a personal autonomous agent — like OpenClaw but built on the Anthropic SDK, for single-user personal use, that gets smarter and cheaper over time.

## Context

Airees (Phases 1-5) provides: brain orchestrator with plan-execute-evaluate loops, multi-agent delegation via task DAGs, memory (SQLite + file-based), feedback loops, skill store, model routing with fallback (Anthropic + OpenRouter), context compression (4-stage cascade), quality gates, event bus, MCP client, CLI, heartbeat daemon, goal daemon. 342 tests passing.

OpenClaw (245k GitHub stars) is a personal AI assistant with 50+ messaging channels, voice, browser automation, and a Markdown-based memory system. Its brain is a standard ReAct loop (Pydantic AI). It runs on Node.js/TypeScript.

**Key insight:** Airees has a better brain. OpenClaw has better ears and a mouth. This phase gives Airees a face.

## Architecture

```
+---------------------------------------------------------+
|                      CHANNELS                           |
|  [CLI]  [Telegram]  [WhatsApp*]  [Discord*]  [Web*]    |
+----------------------------+----------------------------+
                             | InboundMessage
                    +--------v---------+
                    |     GATEWAY      |  ASGI server (Starlette)
                    |  WebSocket + HTTP |  Session management
                    +--------+---------+  Channel routing
                             |
                    +--------v---------+
                    | CONVERSATION MGR |  Context assembly
                    |                  |  Complexity routing
                    +--------+---------+  Turn management
                             |
              +--------------v--------------+
              |        AIREES BRAIN         |  Existing orchestrator
              |  Intent -> Plan -> Execute  |  Quality gates
              +--------------+--------------+  Feedback loops
                             |
         +--------+----------+----------+---------+
         v        v          v          v         v
     [Quick    [Deep     [Task      [Proactive [Background
      Reply]   Think]    Plan]      Action]    Worker]
      Haiku    Sonnet    Opus       Scheduler  Daemon

* = future phases
```

## Components

### 1. Gateway (new)

Python ASGI server (Starlette) with WebSocket support. Responsibilities:
- Accept connections from channel adapters
- Normalize messages into InboundMessage/OutboundMessage types
- Route responses back through correct channel
- Manage sessions (channel + user + conversation state)
- Health endpoint for monitoring

Binds to localhost by default (no public exposure).

### 2. Message Types (new)

```python
@dataclass(frozen=True)
class InboundMessage:
    channel: str          # "telegram", "cli", etc.
    sender_id: str        # Channel-specific user ID
    text: str
    attachments: tuple[Attachment, ...] = ()
    reply_to: str | None = None
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class OutboundMessage:
    channel: str
    recipient_id: str
    text: str
    attachments: tuple[Attachment, ...] = ()
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Attachment:
    type: str             # "image", "file", "voice", "link"
    url: str | None = None
    data: bytes | None = None
    filename: str | None = None
    mime_type: str | None = None
```

### 3. Channel Adapter Interface (new)

```python
class ChannelAdapter(Protocol):
    name: str

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def send(self, message: OutboundMessage) -> None: ...
    async def on_message(self, callback: Callable[[InboundMessage], Awaitable[None]]) -> None: ...
```

Phase 6 implements: CLI adapter, Telegram adapter.

### 4. Conversation Manager (new)

Sits between Gateway and Brain. Responsibilities:
- Assemble context per turn (SOUL.md + USER.md + history + relevant memories)
- Classify complexity for model routing
- Manage multi-turn conversation state
- Inject personal context

**Complexity classification:**
- Level 0 (Haiku): greetings, simple questions, quick lookups
- Level 1 (Sonnet): summarization, analysis, moderate reasoning
- Level 2 (Opus brain): multi-step goals, planning, complex research

80%+ of daily interactions should route to Haiku.

### 5. Personal Context (new)

**USER.md** — user profile loaded into every conversation:
- Name, timezone, preferences
- Communication style
- Recurring tasks, important dates
- Key contacts and projects

**Conversation Memory** — extend SQLiteMemoryStore:
- Store conversation summaries per session
- Semantic search across past conversations
- Auto-extract facts from conversations

### 6. Proactive Scheduler (extend existing)

Extend HeartbeatDaemon with:
- Cron-style user-defined triggers
- Event-driven triggers (message from X, time-based)
- Background task completion notifications via channel

### 7. Cost Optimization (extend existing)

- Smart model routing: Haiku (80%), Sonnet (15%), Opus (5%)
- Skill caching: proven workflows skip brain planning
- Prompt caching: SOUL.md + USER.md cached across turns (0.1x price on hits)
- Compaction API: long conversations compressed server-side
- Batch API: non-urgent background tasks at 50% discount
- Learning: fewer brain iterations as patterns are learned

Projected trajectory: ~$5-10/day (month 1) -> ~$1-3/day (month 6).

### 8. Security

- No credentials in context window (env vars only)
- Tool sandboxing via TrustLevel (existing)
- Channel authentication per adapter
- Rate limiting via ConcurrencyManager (existing)
- Gateway binds to localhost (access via VPN/Tailscale)
- Command validation (existing _validate_command)

## Phase 6 Scope

**In scope:**
- Gateway server + message types
- Channel adapter interface + CLI adapter + Telegram adapter
- Conversation manager (context assembly, complexity routing, turn management)
- USER.md personal context support
- Conversation memory extensions
- Cron scheduler extensions
- Cost tracking data model

**Out of scope (future phases):**
- WhatsApp, Discord, Signal adapters
- Voice/speech (TTS/STT)
- Web UI dashboard
- Mobile companion
- Browser automation
- Plugin/skill marketplace

## Dependencies

New:
- starlette >= 0.40.0 (ASGI framework)
- uvicorn >= 0.30.0 (ASGI server)
- websockets >= 13.0 (WebSocket support)
- python-telegram-bot >= 21.0 (Telegram adapter)

Existing (already in project):
- anthropic, pydantic, aiosqlite, click, httpx, pyyaml

## Success Criteria

1. Send a message via CLI -> get intelligent response using appropriate model tier
2. Send a message via Telegram -> get response in Telegram
3. Multi-turn conversations maintain context across turns
4. Complex goals trigger full brain orchestrator (plan-execute-evaluate)
5. Simple queries use Haiku and cost < 0.1 cents per turn
6. Agent remembers facts from previous conversations
7. Background tasks complete and notify via channel
8. All existing 342 tests continue passing
9. New test coverage >= 80%
