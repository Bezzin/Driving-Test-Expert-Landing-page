# Airees Phase 2 Design: Worker Tools, Parallel Execution, and Resilience

**Goal:** Transform Airees workers from one-shot text generators into tool-using parallel agents with web research capabilities, provider resilience, and intent-aware planning.

**Inspired by:** [Tavily](https://docs.tavily.com/documentation/about) (search/extract/crawl API for AI agents) and [oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode) (multi-agent orchestration patterns: concurrency control, provider fallback, intent classification).

**Builds on:** Phase 1 Brain Foundation (GoalStore, Brain orchestrator, Coordinator, Worker builder, state machine).

---

## 1. Parallel Worker Execution + Priority Queuing

**Problem:** Phase 1 runs workers sequentially. If a goal has 5 independent tasks, they execute one at a time.

**Solution:** The Coordinator dispatches all unblocked tasks concurrently using a priority-aware worker pool. Tasks execute in waves based on DAG dependencies.

```
Goal: "Build a research tool"
  Task 1 (HIGH): Research       ──┐
  Task 2 (NORMAL): Design       ──┤── Wave 1 (parallel)
  Task 3 (NORMAL): Build        ──── Wave 2 (after 1+2 complete)
  Task 4 (LOW): Test            ──── Wave 3 (after 3 completes)
```

### Priority System

Tasks have a `priority` field (enum):
- `CRITICAL = 0` — Must complete first, blocks everything
- `HIGH = 1` — Important, preferred scheduling
- `NORMAL = 2` — Default
- `LOW = 3` — Background, fills spare capacity

The Brain sets priority when creating plans via the `create_plan` tool. The `create_plan` tool schema gains an optional `priority` field per task.

### Concurrency Manager

Controls how many workers can hit each provider/model simultaneously.

```python
@dataclass
class ConcurrencyManager:
    provider_limits: dict[str, int]   # e.g., {"anthropic": 5, "openrouter": 10}
    model_limits: dict[str, int]      # e.g., {"claude-opus-4-6": 2, "haiku-4-5": 20}
    _semaphores: dict[str, asyncio.Semaphore]

    async def acquire(self, provider: str, model: str) -> None:
    async def release(self, provider: str, model: str) -> None:
```

### Worker Pool

Priority queue that respects concurrency limits.

```python
@dataclass
class WorkerPool:
    concurrency: ConcurrencyManager
    queue: asyncio.PriorityQueue

    async def submit(self, task: dict) -> None:
    async def run_until_empty(self, executor_fn) -> list[dict]:
```

**Error handling:** `return_exceptions=True` — a failed worker doesn't kill siblings. Failed tasks follow existing retry logic. If a CRITICAL task fails, remaining wave tasks can be cancelled (configurable).

### Schema Change

Add `priority INTEGER DEFAULT 2` to the `tasks` table.

---

## 2. Provider Fallback Chains

**Problem:** If a provider returns 429 or errors, the worker fails immediately.

**Solution:** `FallbackRouter` wraps the model router with retry logic across multiple providers.

```python
@dataclass
class FallbackRouter:
    providers: list[tuple[str, Any]]  # [(name, router), ...]
    max_retries: int = 3
    backoff_base: float = 1.0

    async def create_message(self, model: ModelConfig, **kwargs) -> Any:
        for attempt in range(self.max_retries):
            for provider_name, router in self.providers:
                try:
                    return await router.create_message(model=model, **kwargs)
                except RateLimitError:
                    await asyncio.sleep(self.backoff_base * (2 ** attempt))
                    continue
                except ProviderError as e:
                    last_error = e
                    continue
        raise last_error
```

### Provider Priority

1. Anthropic (direct) — lowest latency for Claude models
2. OpenRouter — universal fallback, supports most models
3. OpenAI — direct access for GPT models
4. Google — direct access for Gemini models

### Model Compatibility Map

Not all models are on all providers:
- `claude-opus-4-6` → Anthropic, OpenRouter
- `gpt-4o` → OpenAI, OpenRouter
- `gemini-2.5-pro` → Google, OpenRouter
- `haiku-4-5` → Anthropic, OpenRouter

The fallback router only tries providers that support the requested model.

---

## 3. Tavily Tool Provider

**Problem:** Workers can only generate text from training data. A "researcher" worker can't actually search the web.

**Solution:** Tavily integration as a tool provider. Workers with research roles get web search and extract tools.

### Tools Exposed

| Tool | Purpose | Tavily Endpoint |
|------|---------|-----------------|
| `web_search` | Search the web for current information | `/search` |
| `web_extract` | Extract content from specific URLs | `/extract` |

### Implementation

```python
@dataclass
class TavilyToolProvider:
    api_key: str  # from TAVILY_API_KEY env var

    def get_tools(self) -> list[ToolDefinition]:
        # Returns tool definitions for LLM tool_use

    async def execute(self, tool_name: str, tool_input: dict) -> str:
        # Executes tool call and returns result as string
```

### Role-to-Tools Mapping

Added to `worker_builder.py`:

```python
ROLE_TOOLS: dict[str, list[str]] = {
    "researcher": ["web_search", "web_extract"],
    "coder": [],
    "reviewer": ["web_search"],
    "planner": ["web_search"],
    "writer": ["web_search", "web_extract"],
}
```

### Graceful Degradation

If `TAVILY_API_KEY` is not set, the provider returns an empty tool list. Workers still function — they just rely on LLM knowledge only. No crash, no error, just reduced capability.

---

## 4. Tool_use Loop in Worker Execution

**Problem:** `_execute_worker` makes one LLM call and reads text. Tool calls are ignored.

**Solution:** Agentic loop — call LLM, process tool_use blocks, feed results back, repeat until `end_turn`.

```python
async def _execute_worker(self, goal_id: str, task: dict) -> None:
    tools = self._get_tools_for_role(task["agent_role"])
    messages = [{"role": "user", "content": task["description"]}]

    max_tool_rounds = 10
    for _ in range(max_tool_rounds):
        response = await self.router.create_message(
            model=model, system=worker_prompt,
            messages=messages, tools=tools,
        )

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await self.tool_provider.execute(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
```

**Token tracking:** Each round's tokens are accumulated. Total cost reflects all rounds, not just the first.

**Safety:** `max_tool_rounds = 10` prevents infinite loops. Configurable per task.

---

## 5. Intent Classifier

**Problem:** The Brain gets a raw goal string and plans from scratch. No pre-analysis of what kind of work this is.

**Solution:** Lightweight intent classification using a cheap model (Haiku) before Brain planning.

### Intent Types

```python
class GoalIntent(Enum):
    RESEARCH = "research"        # "Find out about X"
    BUILD = "build"              # "Create/implement X"
    FIX = "fix"                  # "Fix/debug X"
    INVESTIGATE = "investigate"  # "Why is X happening?"
    OPTIMIZE = "optimize"        # "Make X faster/better"
```

### How It's Used

1. User submits goal
2. `classify_intent()` calls Haiku (~100 tokens, <$0.001)
3. Intent passed to `build_brain_prompt()` — Brain knows what kind of plan to create
4. Intent influences default tool assignment (RESEARCH goals → all workers get search tools)
5. Intent influences default priorities (FIX goals → higher default priority)

### Cost

One Haiku call per goal (~$0.001). Negligible compared to the Opus planning call that follows.

---

## File Plan

| Feature | New Files | Modifies |
|---------|-----------|----------|
| Parallel execution | `concurrency.py`, `worker_pool.py` | `orchestrator.py`, `schema.py` |
| Provider fallback | `fallback_router.py` | `orchestrator.py` |
| Tavily tools | `tools/providers/__init__.py`, `tools/providers/tavily.py` | `worker_builder.py` |
| Tool_use loop | — | `orchestrator.py` |
| Intent classifier | `brain/intent.py` | `orchestrator.py`, `brain/prompt.py`, `brain/tools.py` |

**Estimated: ~8-10 tasks, ~500 lines new code, ~15 new tests.**

---

## What This Enables

After Phase 2, Airees can:
- Run 5 independent research tasks simultaneously
- Workers can search the web and extract content from URLs
- If Anthropic is rate-limited, automatically retry via OpenRouter
- Classify "Research quantum computing" as RESEARCH and give all workers search tools
- Classify "Fix the login bug" as FIX and prioritize debugging tasks
- Handle provider outages gracefully without failing goals

## What This Defers (Phase 3+)

- Code execution tools (sandboxed)
- File system / git tools for workers
- Circuit breaker pattern (disable provider after N failures)
- Worker-to-worker communication
- Skill creation and learning from completed goals
