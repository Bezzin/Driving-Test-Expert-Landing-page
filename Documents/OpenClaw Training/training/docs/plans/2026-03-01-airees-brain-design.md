# Airees Brain Architecture Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create the implementation plan from this design.

**Goal:** Transform Airees from a pipeline toolkit into an autonomous, self-improving orchestrator that takes any goal, builds and executes pipelines dynamically, iterates until satisfied, and learns from every execution.

**Architecture:** Brain (Opus) + Coordinator (cheap model) split. Brain handles strategy — planning, evaluation, pivoting, learning. Coordinator handles execution — task management, worker lifecycle, result collection. Workers are disposable sub-agents on the cheapest viable model. Heartbeat daemon runs continuously on a free local model.

**Inspired by:** Conway-Research/Automaton (orchestration state machine, task graph DAGs, progressive compression, skill trust boundaries, soul reflection, heartbeat daemon), OpenClaw Token Optimization Guide (session initialization, model routing, rate limits).

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        USER                             │
│                    (Chat / Dashboard)                    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    WEB UI (Next.js)                      │
│         Chat interface + Dashboard + Monitoring          │
└────────────────────────┬────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────┐
│                   SERVER (FastAPI)                       │
│            API gateway + Event streaming                 │
└──────┬─────────────────┬───────────────────┬────────────┘
       │                 │                   │
┌──────▼──────┐  ┌───────▼───────┐  ┌───────▼───────────┐
│   BRAIN     │  │  COORDINATOR  │  │  HEARTBEAT DAEMON  │
│  (Opus)     │  │  (Haiku)      │  │  (Ollama/local)    │
│             │  │               │  │                    │
│ Plans       │  │ Task graph    │  │ Health checks      │
│ Evaluates   │  │ Spins up      │  │ Project monitor    │
│ Pivots      │  │   workers     │  │ Wake events        │
│ Reflects    │  │ Collects      │  │ Alerts             │
│ Learns      │  │   results     │  │                    │
│ Creates     │  │ Retries       │  │                    │
│   skills    │  │ Escalates     │  │                    │
│             │  │   to Brain    │  │                    │
└──────┬──────┘  └───────┬───────┘  └───────────────────┘
       │                 │
       │          ┌──────▼──────┐
       │          │   WORKERS   │
       │          │ (OpenRouter) │
       │          │             │
       │          │ Fresh API    │
       │          │   call each  │
       │          │ Cheapest     │
       │          │   viable     │
       │          │   model      │
       │          │ Skills +     │
       │          │   corpus     │
       │          │   injected   │
       │          └─────────────┘
       │
┌──────▼──────────────────────────────────────────────────┐
│                    PERSISTENCE                           │
│  SQLite (goals, tasks, runs, metrics, skill registry)   │
│  Files (skills/, memory/, decisions/, corpus/)           │
└─────────────────────────────────────────────────────────┘
```

**Interaction flow:**
1. User sends goal via Chat. Server forwards to Brain.
2. Brain plans (task graph + model selection + skill assignment). Writes plan to SQLite. Hands off to Coordinator.
3. Coordinator executes the plan. Spins up workers, tracks progress, handles retries.
4. Coordinator escalates to Brain when: quality gate needs judgment, a discovery changes the plan, something unexpected happens, or all tasks complete.
5. Brain evaluates, decides to iterate or complete. If iterating, sends updated plan back to Coordinator.
6. On completion, Brain reflects, creates/updates skill, reports to user.
7. Heartbeat daemon runs independently. Monitors ongoing projects, triggers wakes.

---

## 2. The Brain (Airees Core)

The Brain is the strategic intelligence. Runs on **Claude Opus**. Only activates when executive thinking is needed.

### Brain State Machine

```
idle -> planning -> delegating -> waiting -> evaluating -> [adapting | completing]
                                                 |                |
                                            reflecting -> skill_creation -> idle
```

### Activation Triggers

| Trigger | What Brain Does |
|---------|-----------------|
| New goal from user | Breaks down into task graph, selects models, assigns skills |
| Coordinator escalates | Evaluates situation, decides: retry/pivot/continue/abort |
| All tasks complete | Reviews full output, decides: satisfied or iterate again |
| Discovery/opportunity | Rewrites parts of the plan based on new information |
| Reflection (periodic) | Reviews what worked, updates SOUL.md, creates/updates skills |

### Brain's System Prompt Built From

1. **SOUL.md** — identity, values, personality, operating principles
2. **Active skills** — relevant proven pipelines from the skills library
3. **Training corpus excerpts** — best practices relevant to the current goal (retrieved on demand, not loaded upfront)
4. **Current goal context** — what we're building, where we are, what's happened so far
5. **Coordinator's report** — latest task results, failures, discoveries

### Brain's Tools

- `create_plan` — output a task graph with dependencies
- `evaluate_result` — score and judge a worker's output
- `adapt_plan` — modify the task graph mid-execution
- `create_skill` — distill a successful pipeline into a skill.md
- `update_soul` — reflect and update SOUL.md
- `search_corpus` — retrieve relevant training material
- `search_skills` — find existing skills that match the goal
- `message_user` — report back to the user (only when done or genuinely stuck)

### Key Design Principle

The Brain never does the work itself. It only thinks, plans, evaluates, and learns. Every actual task is delegated.

---

## 3. The Coordinator

The Coordinator is the operations manager. Runs on a **cheap model** (Haiku or OpenRouter free tier). Handles the busy work of executing the Brain's plan.

### Coordinator's Loop

```
while goal is active:
    1. Get next ready tasks from task graph (dependencies satisfied)
    2. For each ready task:
       a. Select model (from Brain's recommendation or own heuristic)
       b. Build sub-agent (instructions from skill/corpus + task spec)
       c. Spin up worker via OpenRouter API call
       d. Collect result
    3. Run quality gate on each result
    4. If gate passes: mark task complete, unblock dependents
    5. If gate fails:
       a. Retry with same model (up to max_retries)
       b. If still failing: escalate to Brain
    6. If discovery/anomaly detected: escalate to Brain
    7. If all tasks complete: escalate to Brain for evaluation
    8. Log everything (results, costs, decisions, timing)
```

### Coordinator's Responsibilities

| Responsibility | Detail |
|----------------|--------|
| Task graph execution | Tracks dependencies, auto-unblocks, handles ordering |
| Worker lifecycle | Spins up, monitors, collects results, tears down |
| Model selection | Picks cheapest viable model per task type |
| Quality gates | Runs automated scoring. Only escalates judgment calls to Brain |
| Retry logic | Same task, same model first. Different model second. Escalate third |
| Cost tracking | Logs tokens/cost per worker, per task, per goal |
| Progress reporting | Streams events to dashboard via WebSocket |

### Escalation to Brain

- Quality gate fails after max retries
- Worker output contradicts the plan or reveals something unexpected
- A task produces a result that suggests a better approach
- All tasks in the current plan iteration are complete
- Budget anomaly (a task cost 10x what was expected)

### What Coordinator Does NOT Do

- Make strategic decisions (Brain)
- Decide to pivot or change approach (Brain)
- Interact with the user (Brain via `message_user`)
- Create or update skills (Brain)

### Coordinator's Context Is Kept Lean

- Only the current task graph + active task specs
- No full history — just what's needed right now
- Results summarized before passing to Brain (compression)

---

## 4. Workers (Sub-agents)

Workers are disposable, single-purpose agents. Each one is a fresh API call — no persistent state, no memory of previous tasks.

### Worker Lifecycle

```
Born -> Receive task + instructions + tools -> Execute -> Return result -> Die
```

### How Coordinator Builds a Worker

**1. Pick the model** — based on task type and Brain's recommendation:

| Task Type | Default Model | Escalation Model |
|-----------|--------------|------------------|
| Research/search | Free tier (e.g., llama-3.3-70b) | Haiku |
| Code writing | Haiku | Sonnet |
| Code review | Haiku | Sonnet |
| Content writing | Free tier | Haiku |
| Testing | Haiku | Sonnet |
| Security audit | Sonnet | Opus |
| Architecture | Sonnet | Opus |

**2. Build the system prompt** from:
- Task-specific instructions from the plan
- Relevant skill.md content (if one exists for this task type)
- Relevant training corpus excerpts (searched, not bulk loaded)
- Output format requirements (so Coordinator can parse the result)
- Constraints (token limit, tool permissions, scope boundaries)

**3. Assign tools** — scoped to only what this task needs (principle of least privilege)

**4. Execute via Agent SDK** — fresh `Runner.run()` call through OpenRouter

**5. Collect structured result:**
- `output` — the actual work product
- `confidence` — self-assessed quality (0-10)
- `discoveries` — anything unexpected the worker found
- `tokens_used` — for cost tracking

### Worker Isolation

- Workers cannot see other workers' outputs (unless explicitly provided as task input via `{{previous_output}}`)
- Workers cannot modify the task graph
- Workers cannot communicate with the user
- Workers have scoped tool access — only what their task needs
- Workers have no memory of previous runs

---

## 5. Adaptive Iteration Loop

The heart of what makes Airees different from a one-shot pipeline runner.

### The Loop

```
Brain plans -> Coordinator executes -> Brain evaluates
                                           |
                                    ┌──────┴──────┐
                                    |             |
                                Satisfied?    Not satisfied
                                    |             |
                               Complete +     WHY not?
                               create skill       |
                                    |─────────────|
                                    |      |      |
                                 Quality Discovery Better
                                 issue   changes  approach
                                    |    the plan  found
                                    |      |      |
                                    └──┬───┘──┬───┘
                                       |      |
                                   Adapt   Rewrite
                                   plan    plan
                                       |      |
                    ┌──────────────────┘──────┘
                    v
              Coordinator executes again
```

### Iteration Triggers (Not Just Retry)

| Trigger | Example | Brain's Response |
|---------|---------|------------------|
| Quality issue | Code works but is messy | Adapt: add refactoring task |
| Discovery | Worker found a better library | Rewrite: restructure around the library |
| Test failure | Integration tests reveal design flaw | Rewrite: redesign the component |
| Opportunity | Research reveals a SaaS API that replaces 3 tasks | Rewrite: simplify the pipeline |
| Scope expansion | Building auth revealed need for user management | Adapt: add new tasks to the graph |
| External feedback | Deployment failed, needs different infra | Adapt: swap deployment strategy |

### Mechanics

1. Coordinator completes all tasks. Sends full results + worker discoveries to Brain.
2. Brain evaluates holistically — not just "did each task pass" but "does the whole thing work together? Is this the best I can do?"
3. Brain decides: **Satisfied** (complete), **Adapt** (modify task graph), or **Rewrite** (scrap parts, redesign).
4. Iteration counter tracked per goal. Brain sees "iteration 3 of goal X."
5. Each iteration's reasoning logged as a DecisionDocument.

### Guardrails

- No hard iteration cap (the COO doesn't stop until the job is done)
- But Brain has self-awareness: "Am I going in circles?" — if 3 iterations haven't improved quality scores, Brain reassesses the entire approach
- Cost tracking visible to Brain — it can factor total spend into decisions
- Token optimization: each iteration, only the delta (what changed) is sent to Brain, not full history

### Key Difference From Simple Retry

Retry = "do the same thing again, hope it works."
Iteration = "think about what went wrong, change the approach, try something different."

---

## 6. Skills System

Skills are Airees' long-term memory of proven approaches. Every successful autonomous execution becomes a reusable, optimizable recipe.

### Skill Lifecycle

```
Goal succeeds -> Brain reflects -> Creates skill.md -> Stored in skills/
Similar goal arrives -> Brain searches skills -> Finds match -> Uses as starting point
Execution succeeds with improvements -> Brain updates the skill
```

### Skill Format

Markdown with YAML frontmatter:

```markdown
---
name: nextjs-saas-app
description: Build and deploy a Next.js SaaS with auth, payments, and landing page
version: 3
created: 2026-03-01
last_updated: 2026-03-15
success_rate: 0.85
iterations_avg: 2.3
total_executions: 7
models_preferred:
  research: llama-3.3-70b
  code: claude-haiku-4-5
  review: claude-haiku-4-5
  deploy: claude-haiku-4-5
tools_required:
  - web_search
  - file_write
  - code_execute
  - cli_execute
triggers:
  - "build a saas"
  - "create a web app with payments"
  - "nextjs application"
---

# Next.js SaaS App Pipeline

## Task Graph
1. Research — Analyze requirements, find best libraries/APIs
2. Scaffold — Create Next.js project with TypeScript, Tailwind
3. Auth (depends: 2) — Implement authentication (Clerk)
...

## Lessons Learned
- v1: Used custom auth, took 4 iterations. Switched to Clerk in v2.
- v3: Added landing page as parallel task, saved time.

## Quality Gates
- Code tasks: min_score 7, test coverage > 80%
- Deploy: health check must return 200

## Known Pitfalls
- Don't use SQLite for SaaS (concurrent users). Always PostgreSQL.
```

### How Brain Uses Skills

1. Goal arrives. Brain calls `search_skills` with goal description.
2. Match found: load skill as starting template, adapt to specific goal.
3. No match: plan from scratch using training corpus.
4. Partial match: use matching parts, plan the rest fresh.

### How Skills Evolve

- Version increments on each update
- `success_rate` tracked across executions
- `iterations_avg` tracked (are we getting more efficient?)
- `models_preferred` updated when Brain discovers cheaper models work
- `lessons_learned` appended with each execution's insights
- `known_pitfalls` captures failures to avoid

### Skill Trust Boundaries (From Automaton)

- Skills created by Airees itself are trusted
- Skills imported externally wrapped in `[SKILL: name — UNTRUSTED]` markers
- Injection patterns stripped (tool call JSON, identity overrides, etc.)

---

## 7. Memory & Context Management

Long-running autonomous goals can span hours or days. Without proper memory management, Brain and Coordinator hit context limits.

### Three Layers of Memory

```
┌─────────────────────────────────────────┐
│         WORKING MEMORY (context)        │
│   What's in the current LLM call        │
│   Brain: ~8KB on activation             │
│   Coordinator: current task graph only  │
│   Workers: task spec + skill only       │
└──────────────────┬──────────────────────┘
                   | overflow
┌──────────────────▼──────────────────────┐
│         SHORT-TERM MEMORY (SQLite)      │
│   Recent turns, task results, events    │
│   Searchable, retrievable on demand     │
│   Pruned after goal completion          │
└──────────────────┬──────────────────────┘
                   | distilled
┌──────────────────▼──────────────────────┐
│         LONG-TERM MEMORY (files)        │
│   Skills, SOUL.md, decision docs,       │
│   daily memory logs, training corpus    │
│   Permanent, grows over time            │
└─────────────────────────────────────────┘
```

### Session Initialization (Token Optimization)

When Brain activates, it loads ONLY:
1. `SOUL.md` — identity and principles (~2KB)
2. Goal summary — what we're working on (~1KB)
3. Coordinator's report — latest status, escalation reason (~2-3KB)
4. Relevant skill (if one matches) (~2-3KB)

It does NOT load: full history, all task results, previous turns, full training corpus. Uses on-demand retrieval (`search_corpus`, `get_task_result`, `get_decision_history`).

### Progressive Compression (Adapted from Automaton)

For the Coordinator, which runs many turns tracking task execution:

| Stage | Trigger | Action |
|-------|---------|--------|
| 1 (60%) | Compact worker results | Replace full outputs with summaries + file references |
| 2 (75%) | Compress completed tasks | Collapse finished task chains into one-line summaries |
| 3 (85%) | Checkpoint | Save full state to SQLite, reset context to active tasks only |
| 4 (95%) | Emergency | Keep only the current task + escalation context |

### Daily Memory Log

At the end of each day (or goal completion), Brain writes:
```
memory/2026-03-01.md
- Worked on: SaaS app for client X
- Decisions: Chose Clerk over NextAuth, PostgreSQL over SQLite
- Iterations: 3 (auth rework, Stripe fix, landing page parallelization)
- Skills created: nextjs-saas-app v1
- Cost: $2.40 total (Brain $0.30, Coordinator $0.35, Workers $1.75)
- Next steps: Monitor deployment, set up social accounts
```

---

## 8. Heartbeat Daemon

Keeps Airees alive when nobody's watching. Runs on a **free local model (Ollama)** so it costs nothing.

### Heartbeat Tasks

| Task | Interval | Model | Purpose |
|------|----------|-------|---------|
| `goal_monitor` | 5 min | Ollama (free) | Check if any active goal has stalled |
| `worker_health` | 2 min | None (DB query) | Check for timed-out/crashed workers, reset tasks |
| `deployment_health` | 30 min | None (HTTP ping) | Health-check deployed projects, alert if down |
| `inbox_check` | 1 min | None (DB query) | Check for new user messages or webhooks |
| `metrics_rollup` | 1 hour | None (DB query) | Aggregate cost/performance metrics for dashboard |
| `reflection_trigger` | 24 hours | None (timer) | Wake Brain for daily reflection |
| `skill_cleanup` | 24 hours | None (DB query) | Prune skills with 0% success after 3+ attempts |

### Wake Events (Triggers Brain Activation)

- User sends a new goal via chat
- Goal stalled > 30 minutes with no Coordinator activity
- Deployed project health check fails
- Daily reflection timer fires
- External webhook triggers

### Implementation

- Python `asyncio` background loop alongside FastAPI server
- Each task has `last_run` timestamp in SQLite with lease protection
- Configurable intervals via `scheduler_config` table
- Graceful shutdown — completes current task before stopping

---

## 9. Tool Discovery & Learning

Airees discovers tools dynamically via MCP and CLI, then saves successful usage as skills.

### Three Sources of Tools

1. **Built-in** — file_read, file_write, code_execute, web_search, web_fetch, git_*
2. **MCP Servers** — discovered dynamically via MCP protocol (e.g., Vercel, Stripe, Slack)
3. **CLI Tools** — discovered via PATH (e.g., docker, gh, curl)

### MCP Discovery Flow

1. Brain encounters goal needing unknown tool (e.g., "deploy to Vercel")
2. Brain searches skills — no match
3. Worker finds the MCP server, connects, lists tools
4. New tools registered in Tool Registry with `trust_level: discovered`
5. Worker uses tools to complete task
6. On success, Brain saves MCP connection + usage as a skill

### CLI Discovery Flow

1. Worker checks if CLI tool exists (`which gh`, `which docker`)
2. Reads help output to understand usage
3. Uses tool via `cli_execute` with scoped permissions
4. On success, saved as a skill with CLI patterns learned

### Tool Trust Levels

| Level | Source | Permissions |
|-------|--------|-------------|
| `builtin` | Ships with Airees | Full access, always available |
| `discovered` | Found via MCP/CLI | Available but logged, rate-limited until proven |
| `proven` | Used successfully 3+ times | Full access, included in relevant skills |
| `untrusted` | Imported externally | Sandboxed, requires explicit approval first time |

### Scoping Per Worker

Coordinator assigns only the tools a worker needs for its specific task. Principle of least privilege.

---

## 10. SOUL.md & Self-Reflection

SOUL.md is Airees' identity. It defines who Airees is, how it thinks, and how it evolves.

### Initial SOUL.md

```markdown
---
format: soul/v1
name: Airees
version: 1
created: 2026-03-01
last_reflection: null
genesis_hash: sha256:...
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

# Capabilities
(auto-updated by reflection)
- Skills mastered: 0
- Goals completed: 0
- Total iterations: 0

# Strategy
(auto-updated by reflection)
- Current focus: Learning and building initial skill library

# Boundaries
- Never expose API keys or secrets
- Never push to production without testing
- Never delete user data without explicit instruction
- Never spend on paid services without user-configured API keys
```

### Reflection Cycle (24h or per goal completion)

1. Load current SOUL.md
2. Gather evidence: goals completed, skills created, iterations, costs, failures, tools discovered
3. Auto-update Capabilities: increment counters, update favourite models, add tools
4. Auto-update Strategy: identify patterns, update priorities, note biggest lesson
5. Check genesis alignment: compare purpose against original hash. If drifting (< 0.5), re-anchor
6. Write updated SOUL.md
7. Write daily memory log

---

## 11. End-to-End Example

**User:** "Build me a SaaS app for tracking gym workouts with auth, payments, and deploy it live"

| Time | Actor | Action |
|------|-------|--------|
| 0 min | User | Sends goal via chat |
| 1 min | Brain | Searches skills, finds "nextjs-saas-app" (v3). Searches corpus for auth/deploy best practices. Builds 12-task graph with 4 parallel branches. Selects models. Hands to Coordinator. |
| 2-25 min | Coordinator | Executes tasks. Research, scaffold, then auth+db+landing in parallel. Core features, payments. Payments fails quality gate twice, escalates model to Sonnet, passes. Collects all results. |
| 26 min | Brain | Evaluates. Discovers research worker found wger API for exercise data. Decides to ITERATE — restructure core features to use API instead of hardcoded list. Logs DecisionDocument. |
| 27-35 min | Coordinator | Re-runs affected tasks only. Previous auth/payments/landing preserved. Tests pass. |
| 36 min | Brain | Evaluates. Satisfied. Proceeds to deploy. |
| 37-42 min | Coordinator | Deploy via Vercel skill. Configure DNS. Health check confirms 200 OK. |
| 43 min | Brain | Reflects. Updates nextjs-saas-app skill to v4. Creates wger-api-integration skill. Updates SOUL.md. Reports to user with results. Goes idle. |

**Total cost:** ~$2-3. **Iterations:** 2. **Skills created/updated:** 2.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Autonomy level | Fully autonomous | COO model — reports results, doesn't ask permission |
| Brain model | Claude Opus | Deepest reasoning for strategic decisions |
| Brain/Coordinator split | Yes | Cost optimization — Brain only activates for executive thinking |
| Worker models | Cheapest viable via OpenRouter | Token optimization — right model for each task type |
| Budget | No hard cap, token optimization strategy | Trust Airees to be efficient, guided by optimization rules |
| Persistence | SQLite + files | Structured data in DB, content as files |
| Skills storage | Local skills/ directory | Markdown with YAML frontmatter, human-readable |
| Tool discovery | MCP + CLI, saves as skills | Self-expanding capability set |
| Runtime | Always-on daemon | Heartbeat on free local model, can work while user sleeps |
| Iteration model | Adaptive (not retry) | Think, pivot, rewrite — not just "try again" |

## Sources

- Conway-Research/Automaton: orchestration FSM, task graph DAGs, compression cascade, skill trust boundaries, soul reflection, heartbeat daemon
- OpenClaw Token Optimization Guide: session initialization, model routing, heartbeat to Ollama, rate limits
- Airees training corpus (17 categories, 226 files): agent fundamentals, SDK patterns, orchestration, security
