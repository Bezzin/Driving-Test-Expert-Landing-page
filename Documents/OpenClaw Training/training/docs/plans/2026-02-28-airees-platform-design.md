# Airees Multi-Agent Platform Design

**Date:** 2026-02-28
**Status:** Approved
**Author:** Nathaniel + Claude

## Overview

Airees is a reusable multi-agent platform built on the Anthropic Agent SDK (Python). It provides three progressive access layers: a Python SDK for developers, declarative YAML configs for technical users, and a Next.js web UI with a visual agent builder for everyone.

## Goals

- Let users define agents, tools, and workflows declaratively in YAML
- Ship pre-built agent archetypes (researcher, coder, reviewer, planner, etc.)
- Provide higher-level orchestration patterns (pipelines, parallel teams, shared-state teams, triage routers) as reusable building blocks
- Deliver a web dashboard for designing, deploying, and monitoring multi-agent systems visually
- Support Anthropic models natively with OpenRouter integration for multi-model selection per agent

## Constraints

- No external agent frameworks (LangChain, CrewAI, Supabase)
- Built on the Anthropic Agent SDK (`claude_agent_sdk`)
- SQLite + files for persistence (no external database services)
- Training corpus (261 files, 17 categories) serves as reference material

## Architecture

Three independent layers, each usable on its own:

```
Layer 3: Web UI (Next.js)     <- Visual builder, monitoring, dashboards
Layer 2: YAML Engine           <- Declarative configs, archetype library
Layer 1: Python SDK Core       <- Agent SDK wrapper, orchestration patterns, model routing
```

A FastAPI sidecar bridges the Next.js frontend to the Python engine via REST and WebSocket.

### Layer 1: Python SDK Core

The foundation. Wraps the Anthropic Agent SDK with higher-level abstractions.

**Model Router:**
- `AnthropicProvider`: Native integration, default provider
- `OpenRouterProvider`: Multi-model gateway, users configure per-agent model selection
- Per-agent model assignment (Opus for complex reasoning, Haiku for routing, third-party via OpenRouter)

**Orchestration Patterns:**

| Pattern | When to Use | SDK Mechanism |
|---------|------------|---------------|
| Pipeline | Sequential processing (extract -> transform -> validate) | Chained handoffs |
| ParallelTeam | Independent tasks run concurrently | Agent-as-tool, parallel tool calls |
| SharedStateTeam | Agents coordinate via shared files/state | Shared memory + agent-as-tool |
| TriageRouter | Route to specialist based on intent | Handoffs with triage agent |

**Tool Registry:**
- Tools registered centrally, then scoped to specific agents
- Each agent only sees its allowed tools (Principle of Least Privilege)

**Memory Manager:**
- Per-agent markdown files (personality, context, learned facts) following SOUL.md/USER.md/MEMORY.md patterns
- SQLite for run history, decisions, outcomes
- Shared memory files for team coordination (GOALS.md, DECISIONS.md pattern)

**Event System:**
- Hook-based observability: `agent.start`, `agent.tool_call`, `agent.handoff`, `agent.complete`, `run.start`, `run.complete`, `run.error`
- Events feed WebSocket (real-time UI), SQLite (persistence), and custom callbacks

**CLI:**
```bash
airees init                          # Scaffold a new project
airees run workflow.yaml             # Run a workflow
airees run --agent researcher "..."  # Run single agent
airees archetypes list               # List available archetypes
airees archetypes use researcher     # Add archetype to project
airees monitor                       # Watch running agents (TUI)
```

### Layer 2: YAML Engine

Parses declarative agent and workflow definitions, translates them into Layer 1 objects.

**Agent definition:**
```yaml
name: researcher
description: "Finds and synthesizes information from the web"
model: claude-sonnet-4-6
instructions: |
  You are a research specialist. Find comprehensive, accurate
  information and present it in structured summaries.
  Always cite your sources.
tools:
  - web_search
  - web_fetch
  - file_write
max_turns: 15
memory:
  personality: agents/researcher/SOUL.md
  context: agents/researcher/MEMORY.md
```

**Workflow definition:**
```yaml
name: research-pipeline
description: "Research a topic, analyze findings, produce report"
pattern: pipeline
steps:
  - agent: researcher
    task: "Research {{topic}} thoroughly. Save findings to research.md"
  - agent: analyst
    task: "Analyze research.md. Identify key themes, gaps, contradictions."
  - agent: writer
    task: "Produce a comprehensive report from the analysis."
variables:
  topic:
    description: "The topic to research"
    required: true
```

**Team definition:**
```yaml
name: content-team
description: "Collaborative content creation team"
pattern: shared_state
shared_memory:
  - GOALS.md
  - DECISIONS.md
  - DRAFT.md
agents:
  researcher:
    archetype: researcher
    model: claude-sonnet-4-6
  writer:
    archetype: writer
    model: claude-sonnet-4-6
  reviewer:
    archetype: reviewer
    model: openrouter/deepseek/deepseek-r1
triage:
  agent: router
  model: claude-haiku-4-5
  routes:
    - intent: "needs research" -> researcher
    - intent: "needs writing" -> writer
    - intent: "needs review" -> reviewer
```

**Archetype Library:**

| Archetype | Purpose | Default Model |
|-----------|---------|---------------|
| researcher | Web research and information synthesis | Sonnet |
| coder | Code generation and modification | Sonnet |
| reviewer | Code review and quality analysis | Sonnet |
| planner | Task decomposition and planning | Opus |
| writer | Content creation and editing | Sonnet |
| analyst | Data analysis and pattern recognition | Sonnet |
| router | Intent classification and triage | Haiku |
| security-auditor | Security review and threat analysis | Opus |

**Template System:**
- Variable interpolation (`{{topic}}`)
- Archetype inheritance with field overrides
- JSON Schema validation for all configs

### Layer 3: Web UI (Next.js)

**Pages:**

| Page | Purpose |
|------|---------|
| Dashboard | Active runs, recent history, cost tracking, system health |
| Agent Builder | Visual drag-and-drop flow builder for composing agents into workflows |
| Agent Library | Browse/search archetypes, create custom agents via form or YAML editor |
| Runs | List all runs with real-time streaming output, agent handoffs, tool calls |
| Run Detail | Timeline view: which agent acted when, tools called, handoff points, final output |
| Settings | Model provider config (Anthropic key, OpenRouter key), default models, memory settings |

**Visual Agent Builder:**
- Drag agent nodes from archetype library onto canvas
- Connect with edges (handoff or agent-as-tool)
- Pattern auto-detected from topology (pipeline, parallel, triage, shared-state)
- Each node opens config panel: model, tools, instructions, memory
- Generates exportable YAML behind the scenes

**Real-Time Run Monitoring:**
- WebSocket streams events from FastAPI
- Timeline shows agent activations, tool calls, handoffs
- Live output panel streams current agent response
- Cost counter tracks token usage per agent
- Pause/stop run controls

**Tech Stack:**
- Next.js 15 (App Router, Server Components)
- React Flow (or similar) for visual flow builder canvas
- Tailwind CSS
- WebSocket for real-time streaming from FastAPI

## Data Flow

```
User Action (CLI/YAML/UI)
  -> Parse and Validate (JSON Schema)
  -> Resolve Config (archetype inheritance, variable interpolation, model routing)
  -> Build Agent Graph (instantiate Agent SDK objects, wire handoffs/tools)
  -> Execute via Runner (Agent SDK Runner.run() with max_turns)
  -> Events emitted at each step
       -> WebSocket -> UI (real-time)
       -> SQLite log (persistence)
       -> Hook callbacks (custom)
  -> Result (final output + run metadata + cost summary)
```

## Error Handling

| Error Type | Strategy |
|-----------|----------|
| Invalid YAML/config | Validate against JSON Schema before execution. Clear error with line number. |
| API key invalid/missing | Fail fast with specific message and setup instructions. |
| Agent exceeds max_turns | Hard stop. Return partial results + warning. |
| Tool execution failure | Catch, log, let agent decide to retry or use alternative. |
| Model rate limit | Exponential backoff with configurable max retries. OpenRouter fallback model. |
| Agent handoff loop | Track handoff history. Break loop after 3 same-pair handoffs. |
| WebSocket disconnect | UI auto-reconnects. Run continues server-side. UI catches up on reconnect. |

## Security

- Per-agent tool scoping (Principle of Least Privilege)
- API keys in environment variables only, validated at startup
- All YAML configs validated against JSON Schema
- `code_execute` tool requires explicit grant and runs sandboxed
- Run isolation: each run gets its own working directory
- Optional SQLite encryption at rest
- API keys stored in OS keyring or env vars

## Project Structure

```
airees/
  packages/
    core/                    # Layer 1: Python SDK Core
      airees/
        agent.py             # Agent wrapper around SDK
        runner.py            # Enhanced Runner with events
        router/              # Model routing (Anthropic + OpenRouter)
        orchestration/       # Pipeline, Parallel, SharedState, Triage
        tools/               # Tool registry and builtins
        memory/              # Memory manager (SQLite + files)
        events.py            # Event bus and hooks
        cli/                 # CLI entry point
      pyproject.toml
      tests/

    engine/                  # Layer 2: YAML Engine
      airees_engine/
        parser.py            # YAML parsing and validation
        resolver.py          # Template resolution and inheritance
        schema.py            # JSON Schema definitions
        archetypes/          # Built-in archetype YAML files
      pyproject.toml
      tests/

    server/                  # FastAPI Sidecar
      airees_server/
        app.py               # FastAPI app
        routes/              # REST endpoints (agents, runs, archetypes, settings)
        ws/                  # WebSocket run streaming
      pyproject.toml
      tests/

    web/                     # Layer 3: Next.js Web UI
      src/
        app/                 # Pages (dashboard, agents, runs, builder, settings)
        components/          # Flow builder, agent nodes, run timeline, UI
        lib/                 # FastAPI client, WebSocket client
        hooks/               # React hooks (run stream, agent CRUD)
      package.json
      next.config.js

  data/                      # SQLite DB + file storage (gitignored)
  docs/plans/
  pyproject.toml             # Root workspace (monorepo)
  package.json               # Root for web package
```

## Persistence

- **SQLite** (`data/airees.db`): Agent configs, run history, metrics, settings
- **Files** (`data/memory/`): Agent memory (SOUL.md, MEMORY.md pattern), workflow definitions, run logs

## Target Users (Progressive Access)

1. **Python developers**: Use Layer 1 directly in code
2. **Technical professionals**: Define agents in YAML, run via CLI
3. **Non-technical users**: Visual agent builder and web dashboard
