# Airees Multi-Agent Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reusable multi-agent platform with three progressive access layers: Python SDK, YAML configs, and a Next.js web UI with visual agent builder.

**Architecture:** Three-layer platform (Core SDK -> YAML Engine -> Web UI) connected via FastAPI sidecar. Uses the `anthropic` Python SDK for API calls with a custom model router supporting both Anthropic native and OpenRouter for multi-model per-agent selection. Orchestration patterns (Pipeline, Parallel, SharedState, Triage) built as composable classes. SQLite + files for persistence.

**Tech Stack:** Python 3.12+, anthropic SDK, httpx (OpenRouter), FastAPI, SQLite, Pydantic, PyYAML, jsonschema, Next.js 15, React Flow, Tailwind CSS, WebSocket

**Design Doc:** `docs/plans/2026-02-28-airees-platform-design.md`

---

## Phase 1: Project Scaffolding

### Task 1: Initialize monorepo structure

**Files:**
- Create: `airees/pyproject.toml` (root workspace)
- Create: `airees/packages/core/pyproject.toml`
- Create: `airees/packages/core/airees/__init__.py`
- Create: `airees/packages/engine/pyproject.toml`
- Create: `airees/packages/engine/airees_engine/__init__.py`
- Create: `airees/packages/server/pyproject.toml`
- Create: `airees/packages/server/airees_server/__init__.py`
- Create: `airees/.gitignore`
- Create: `airees/README.md`

**Step 1: Create the airees directory and root pyproject.toml**

```toml
# airees/pyproject.toml
[project]
name = "airees"
version = "0.1.0"
description = "Multi-agent platform built on Anthropic"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["packages/*"]
```

**Step 2: Create core package**

```toml
# airees/packages/core/pyproject.toml
[project]
name = "airees-core"
version = "0.1.0"
description = "Airees core SDK - agents, orchestration, model routing"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.52.0",
    "httpx>=0.27.0",
    "pydantic>=2.10.0",
    "aiosqlite>=0.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.8.0",
]

[project.scripts]
airees = "airees.cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```python
# airees/packages/core/airees/__init__.py
"""Airees Core SDK - Multi-agent orchestration platform."""

__version__ = "0.1.0"
```

**Step 3: Create engine package**

```toml
# airees/packages/engine/pyproject.toml
[project]
name = "airees-engine"
version = "0.1.0"
description = "Airees YAML engine - declarative agent configs"
requires-python = ">=3.12"
dependencies = [
    "airees-core",
    "pyyaml>=6.0.0",
    "jsonschema>=4.23.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```python
# airees/packages/engine/airees_engine/__init__.py
"""Airees YAML Engine - Declarative agent configuration."""

__version__ = "0.1.0"
```

**Step 4: Create server package**

```toml
# airees/packages/server/pyproject.toml
[project]
name = "airees-server"
version = "0.1.0"
description = "Airees FastAPI server - REST + WebSocket bridge"
requires-python = ">=3.12"
dependencies = [
    "airees-core",
    "airees-engine",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "websockets>=14.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```python
# airees/packages/server/airees_server/__init__.py
"""Airees Server - FastAPI bridge between UI and Python engine."""

__version__ = "0.1.0"
```

**Step 5: Create .gitignore**

```gitignore
# airees/.gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/
.env
data/
*.db
node_modules/
.next/
.turbo/
```

**Step 6: Initialize git and commit**

```bash
cd airees
git init
git add .
git commit -m "chore: scaffold monorepo with core, engine, server packages"
```

---

### Task 2: Initialize Next.js web package

**Files:**
- Create: `airees/packages/web/package.json`
- Create: `airees/packages/web/next.config.js`
- Create: `airees/packages/web/tsconfig.json`
- Create: `airees/packages/web/tailwind.config.ts`
- Create: `airees/packages/web/postcss.config.js`
- Create: `airees/packages/web/src/app/layout.tsx`
- Create: `airees/packages/web/src/app/page.tsx`
- Create: `airees/packages/web/src/app/globals.css`

**Step 1: Create package.json**

```json
{
  "name": "airees-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.7.0"
  }
}
```

**Step 2: Create minimal Next.js app with Tailwind**

```tsx
// airees/packages/web/src/app/layout.tsx
import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Airees",
  description: "Multi-agent platform",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 antialiased">
        {children}
      </body>
    </html>
  )
}
```

```tsx
// airees/packages/web/src/app/page.tsx
export default function DashboardPage() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <h1 className="text-4xl font-bold">Airees</h1>
    </main>
  )
}
```

**Step 3: Install deps and verify build**

```bash
cd airees/packages/web
npm install
npm run build
```

**Step 4: Commit**

```bash
cd airees
git add packages/web
git commit -m "chore: add Next.js web package with Tailwind"
```

---

### Task 3: Set up Python virtual environment and verify packages

**Step 1: Create venv and install packages**

```bash
cd airees
python -m venv .venv
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
pip install -e "packages/core[dev]"
```

**Step 2: Verify imports work**

```bash
python -c "import airees; print(airees.__version__)"
```

Expected: `0.1.0`

**Step 3: Run empty test suite to verify pytest works**

```bash
mkdir -p packages/core/tests
touch packages/core/tests/__init__.py
pytest packages/core/tests -v
```

Expected: `no tests ran`

**Step 4: Commit**

```bash
git add .
git commit -m "chore: verify core package installs and pytest works"
```

---

## Phase 2: Core - Model Router

### Task 4: Define provider protocol and types

**Files:**
- Create: `airees/packages/core/airees/router/__init__.py`
- Create: `airees/packages/core/airees/router/types.py`
- Test: `airees/packages/core/tests/test_router_types.py`

**Step 1: Write failing test for ModelConfig**

```python
# tests/test_router_types.py
from airees.router.types import ModelConfig, ProviderType

def test_model_config_anthropic_default():
    config = ModelConfig(model_id="claude-sonnet-4-6")
    assert config.provider == ProviderType.ANTHROPIC
    assert config.model_id == "claude-sonnet-4-6"

def test_model_config_openrouter():
    config = ModelConfig(
        model_id="deepseek/deepseek-r1",
        provider=ProviderType.OPENROUTER,
    )
    assert config.provider == ProviderType.OPENROUTER

def test_model_config_shorthand():
    config = ModelConfig(model_id="openrouter/deepseek/deepseek-r1")
    assert config.provider == ProviderType.OPENROUTER
    assert config.model_id == "deepseek/deepseek-r1"
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_router_types.py -v
```
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement types**

```python
# airees/packages/core/airees/router/__init__.py
from airees.router.types import ModelConfig, ProviderType

__all__ = ["ModelConfig", "ProviderType"]
```

```python
# airees/packages/core/airees/router/types.py
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field


class ProviderType(Enum):
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    provider: ProviderType = field(default=ProviderType.ANTHROPIC)
    temperature: float = 1.0
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        if self.model_id.startswith("openrouter/"):
            object.__setattr__(self, "model_id", self.model_id[len("openrouter/"):])
            object.__setattr__(self, "provider", ProviderType.OPENROUTER)
```

**Step 4: Run test to verify it passes**

```bash
pytest packages/core/tests/test_router_types.py -v
```
Expected: 3 passed

**Step 5: Commit**

```bash
git add packages/core/airees/router packages/core/tests/test_router_types.py
git commit -m "feat: add ModelConfig and ProviderType for model routing"
```

---

### Task 5: Implement Anthropic provider

**Files:**
- Create: `airees/packages/core/airees/router/anthropic_provider.py`
- Test: `airees/packages/core/tests/test_anthropic_provider.py`

**Step 1: Write failing test**

```python
# tests/test_anthropic_provider.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from airees.router.anthropic_provider import AnthropicProvider
from airees.router.types import ModelConfig, ProviderType


@pytest.fixture
def provider():
    return AnthropicProvider(api_key="test-key")


def test_provider_creation(provider):
    assert provider.api_key == "test-key"
    assert provider.provider_type == ProviderType.ANTHROPIC


@pytest.mark.asyncio
async def test_create_message_calls_anthropic(provider):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Hello")]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
    mock_response.stop_reason = "end_turn"
    mock_response.model = "claude-sonnet-4-6"

    with patch.object(
        provider._client.messages, "create",
        new_callable=AsyncMock, return_value=mock_response,
    ):
        result = await provider.create_message(
            model=ModelConfig(model_id="claude-sonnet-4-6"),
            system="You are helpful",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result.content[0].text == "Hello"
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_anthropic_provider.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/router/anthropic_provider.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anthropic

from airees.router.types import ModelConfig, ProviderType


@dataclass
class AnthropicProvider:
    api_key: str
    provider_type: ProviderType = field(default=ProviderType.ANTHROPIC, init=False)
    _client: anthropic.AsyncAnthropic = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": model.model_id,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens or model.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        return await self._client.messages.create(**kwargs)
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_anthropic_provider.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/router/anthropic_provider.py packages/core/tests/test_anthropic_provider.py
git commit -m "feat: implement AnthropicProvider for native Claude API calls"
```

---

### Task 6: Implement OpenRouter provider

**Files:**
- Create: `airees/packages/core/airees/router/openrouter_provider.py`
- Test: `airees/packages/core/tests/test_openrouter_provider.py`

**Step 1: Write failing test**

```python
# tests/test_openrouter_provider.py
import pytest
from unittest.mock import AsyncMock, patch
from airees.router.openrouter_provider import OpenRouterProvider
from airees.router.types import ModelConfig, ProviderType


@pytest.fixture
def provider():
    return OpenRouterProvider(api_key="test-or-key")


def test_provider_creation(provider):
    assert provider.api_key == "test-or-key"
    assert provider.provider_type == ProviderType.OPENROUTER


@pytest.mark.asyncio
async def test_create_message_calls_openrouter(provider):
    mock_json = {
        "choices": [{"message": {"content": "Hello from DeepSeek"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "deepseek/deepseek-r1",
    }
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_json
    mock_response.raise_for_status = lambda: None

    with patch.object(
        provider._client, "post",
        new_callable=AsyncMock, return_value=mock_response,
    ):
        result = await provider.create_message(
            model=ModelConfig(
                model_id="deepseek/deepseek-r1",
                provider=ProviderType.OPENROUTER,
            ),
            system="You are helpful",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result["choices"][0]["message"]["content"] == "Hello from DeepSeek"
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_openrouter_provider.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/router/openrouter_provider.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from airees.router.types import ModelConfig, ProviderType

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class OpenRouterProvider:
    api_key: str
    provider_type: ProviderType = field(default=ProviderType.OPENROUTER, init=False)
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model.model_id,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            "max_tokens": max_tokens or model.max_tokens,
        }
        if tools:
            payload["tools"] = tools

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_openrouter_provider.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/router/openrouter_provider.py packages/core/tests/test_openrouter_provider.py
git commit -m "feat: implement OpenRouterProvider for multi-model support"
```

---

### Task 7: Implement ModelRouter (dispatcher)

**Files:**
- Create: `airees/packages/core/airees/router/model_router.py`
- Modify: `airees/packages/core/airees/router/__init__.py`
- Test: `airees/packages/core/tests/test_model_router.py`

**Step 1: Write failing test**

```python
# tests/test_model_router.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from airees.router.model_router import ModelRouter
from airees.router.types import ModelConfig, ProviderType


@pytest.fixture
def router():
    return ModelRouter(
        anthropic_api_key="test-anthropic",
        openrouter_api_key="test-openrouter",
    )


def test_router_has_both_providers(router):
    assert router._anthropic is not None
    assert router._openrouter is not None


def test_router_selects_anthropic_by_default(router):
    config = ModelConfig(model_id="claude-sonnet-4-6")
    provider = router._get_provider(config)
    assert provider.provider_type == ProviderType.ANTHROPIC


def test_router_selects_openrouter_for_openrouter_model(router):
    config = ModelConfig(
        model_id="deepseek/deepseek-r1",
        provider=ProviderType.OPENROUTER,
    )
    provider = router._get_provider(config)
    assert provider.provider_type == ProviderType.OPENROUTER


def test_router_without_openrouter_key():
    router = ModelRouter(anthropic_api_key="test")
    config = ModelConfig(
        model_id="deepseek/deepseek-r1",
        provider=ProviderType.OPENROUTER,
    )
    with pytest.raises(ValueError, match="OpenRouter API key not configured"):
        router._get_provider(config)
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_model_router.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/router/model_router.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from airees.router.types import ModelConfig, ProviderType
from airees.router.anthropic_provider import AnthropicProvider
from airees.router.openrouter_provider import OpenRouterProvider


@dataclass
class ModelRouter:
    anthropic_api_key: str
    openrouter_api_key: str | None = None
    _anthropic: AnthropicProvider = field(init=False, repr=False)
    _openrouter: OpenRouterProvider | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._anthropic = AnthropicProvider(api_key=self.anthropic_api_key)
        if self.openrouter_api_key:
            self._openrouter = OpenRouterProvider(api_key=self.openrouter_api_key)

    def _get_provider(self, model: ModelConfig) -> AnthropicProvider | OpenRouterProvider:
        if model.provider == ProviderType.OPENROUTER:
            if self._openrouter is None:
                raise ValueError("OpenRouter API key not configured")
            return self._openrouter
        return self._anthropic

    async def create_message(
        self,
        model: ModelConfig,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        provider = self._get_provider(model)
        return await provider.create_message(
            model=model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )

    async def close(self) -> None:
        if self._openrouter:
            await self._openrouter.close()
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_model_router.py -v
```
Expected: PASS

**Step 5: Update router __init__.py and commit**

```python
# airees/packages/core/airees/router/__init__.py
from airees.router.types import ModelConfig, ProviderType
from airees.router.model_router import ModelRouter

__all__ = ["ModelConfig", "ModelRouter", "ProviderType"]
```

```bash
git add packages/core/airees/router packages/core/tests/test_model_router.py
git commit -m "feat: implement ModelRouter dispatching to Anthropic or OpenRouter"
```

---

## Phase 3: Core - Agent & Tool Registry

### Task 8: Define Agent dataclass

**Files:**
- Create: `airees/packages/core/airees/agent.py`
- Test: `airees/packages/core/tests/test_agent.py`

**Step 1: Write failing test**

```python
# tests/test_agent.py
from airees.agent import Agent
from airees.router.types import ModelConfig


def test_agent_creation():
    agent = Agent(
        name="researcher",
        instructions="You are a research specialist.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    assert agent.name == "researcher"
    assert agent.instructions == "You are a research specialist."
    assert agent.model.model_id == "claude-sonnet-4-6"
    assert agent.tools == []
    assert agent.max_turns == 10


def test_agent_with_tools():
    agent = Agent(
        name="coder",
        instructions="You write code.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        tools=["file_read", "file_write"],
    )
    assert agent.tools == ["file_read", "file_write"]


def test_agent_is_immutable():
    agent = Agent(
        name="test",
        instructions="test",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    # Agent should be frozen (immutable)
    import pytest
    with pytest.raises(AttributeError):
        agent.name = "changed"
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_agent.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/agent.py
from __future__ import annotations

from dataclasses import dataclass, field

from airees.router.types import ModelConfig


@dataclass(frozen=True)
class Agent:
    name: str
    instructions: str
    model: ModelConfig
    tools: list[str] = field(default_factory=list)
    max_turns: int = 10
    description: str = ""
    memory_files: dict[str, str] = field(default_factory=dict)
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_agent.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/agent.py packages/core/tests/test_agent.py
git commit -m "feat: add Agent dataclass with model config and tool scoping"
```

---

### Task 9: Implement ToolRegistry

**Files:**
- Create: `airees/packages/core/airees/tools/__init__.py`
- Create: `airees/packages/core/airees/tools/registry.py`
- Test: `airees/packages/core/tests/test_tool_registry.py`

**Step 1: Write failing test**

```python
# tests/test_tool_registry.py
import pytest
from airees.tools.registry import ToolRegistry, ToolDefinition


def test_register_tool():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    registry.register(tool)
    assert "web_search" in registry


def test_scope_returns_only_requested_tools():
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="a", description="A", input_schema={}))
    registry.register(ToolDefinition(name="b", description="B", input_schema={}))
    registry.register(ToolDefinition(name="c", description="C", input_schema={}))

    scoped = registry.scope(["a", "c"])
    assert len(scoped) == 2
    names = [t.name for t in scoped]
    assert "a" in names
    assert "c" in names
    assert "b" not in names


def test_scope_raises_for_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="unknown_tool"):
        registry.scope(["unknown_tool"])


def test_to_anthropic_format():
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ))
    tools = registry.to_anthropic_format(["web_search"])
    assert tools[0]["name"] == "web_search"
    assert tools[0]["description"] == "Search the web"
    assert "input_schema" in tools[0]
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_tool_registry.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/tools/registry.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Any = None  # Optional async callable


@dataclass
class ToolRegistry:
    _tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def scope(self, tool_names: list[str]) -> list[ToolDefinition]:
        result = []
        for name in tool_names:
            if name not in self._tools:
                raise KeyError(f"Tool not registered: {name}")
            result.append(self._tools[name])
        return result

    def to_anthropic_format(self, tool_names: list[str]) -> list[dict[str, Any]]:
        tools = self.scope(tool_names)
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]
```

```python
# airees/packages/core/airees/tools/__init__.py
from airees.tools.registry import ToolDefinition, ToolRegistry

__all__ = ["ToolDefinition", "ToolRegistry"]
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_tool_registry.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/tools packages/core/tests/test_tool_registry.py
git commit -m "feat: implement ToolRegistry with scoping and Anthropic format conversion"
```

---

## Phase 4: Core - Event System

### Task 10: Implement EventBus

**Files:**
- Create: `airees/packages/core/airees/events.py`
- Test: `airees/packages/core/tests/test_events.py`

**Step 1: Write failing test**

```python
# tests/test_events.py
import pytest
from airees.events import EventBus, Event, EventType


def test_event_creation():
    event = Event(
        event_type=EventType.AGENT_START,
        agent_name="researcher",
        data={"task": "find info"},
    )
    assert event.event_type == EventType.AGENT_START
    assert event.agent_name == "researcher"


def test_subscribe_and_emit():
    bus = EventBus()
    received = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.AGENT_START, handler)
    bus.emit(Event(event_type=EventType.AGENT_START, agent_name="test"))

    assert len(received) == 1
    assert received[0].agent_name == "test"


def test_subscribe_wildcard():
    bus = EventBus()
    received = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe_all(handler)
    bus.emit(Event(event_type=EventType.AGENT_START, agent_name="a"))
    bus.emit(Event(event_type=EventType.AGENT_COMPLETE, agent_name="a"))

    assert len(received) == 2


@pytest.mark.asyncio
async def test_async_handler():
    bus = EventBus()
    received = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.TOOL_CALL, handler)
    await bus.emit_async(Event(event_type=EventType.TOOL_CALL, agent_name="test"))

    assert len(received) == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_events.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/events.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from datetime import datetime, timezone


class EventType(Enum):
    AGENT_START = "agent.start"
    AGENT_COMPLETE = "agent.complete"
    AGENT_HANDOFF = "agent.handoff"
    TOOL_CALL = "agent.tool_call"
    TOOL_RESULT = "agent.tool_result"
    RUN_START = "run.start"
    RUN_COMPLETE = "run.complete"
    RUN_ERROR = "run.error"


@dataclass(frozen=True)
class Event:
    event_type: EventType
    agent_name: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str = ""


EventHandler = Callable[[Event], Any]


@dataclass
class EventBus:
    _handlers: dict[EventType, list[EventHandler]] = field(default_factory=dict)
    _wildcard_handlers: list[EventHandler] = field(default_factory=list)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._wildcard_handlers.append(handler)

    def emit(self, event: Event) -> None:
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if asyncio.iscoroutine(result):
                raise RuntimeError("Use emit_async for async handlers")
        for handler in self._wildcard_handlers:
            result = handler(event)
            if asyncio.iscoroutine(result):
                raise RuntimeError("Use emit_async for async handlers")

    async def emit_async(self, event: Event) -> None:
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        for handler in self._wildcard_handlers:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_events.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/events.py packages/core/tests/test_events.py
git commit -m "feat: implement EventBus with sync/async handlers and wildcard subscriptions"
```

---

## Phase 5: Core - Runner

### Task 11: Implement the Runner (agent execution loop)

**Files:**
- Create: `airees/packages/core/airees/runner.py`
- Test: `airees/packages/core/tests/test_runner.py`

**Step 1: Write failing test**

```python
# tests/test_runner.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from airees.runner import Runner, RunResult
from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus


@pytest.fixture
def runner():
    router = ModelRouter(anthropic_api_key="test-key")
    return Runner(router=router, tool_registry=ToolRegistry(), event_bus=EventBus())


@pytest.fixture
def agent():
    return Agent(
        name="test-agent",
        instructions="You are a test assistant.",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )


def test_runner_creation(runner):
    assert runner.router is not None
    assert runner.tool_registry is not None


@pytest.mark.asyncio
async def test_run_simple_agent(runner, agent):
    """Agent responds with text (no tool calls) = single turn."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Hello world")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = MagicMock(input_tokens=50, output_tokens=10)
    mock_response.model = "claude-sonnet-4-6"

    with patch.object(
        runner.router, "create_message",
        new_callable=AsyncMock, return_value=mock_response,
    ):
        result = await runner.run(agent=agent, task="Say hello")
        assert isinstance(result, RunResult)
        assert result.output == "Hello world"
        assert result.turns == 1
        assert result.token_usage.input_tokens == 50


@pytest.mark.asyncio
async def test_run_respects_max_turns(runner, agent):
    """If agent keeps using tools, stop at max_turns."""
    tool_block = MagicMock(type="tool_use", id="t1", name="test", input={})
    text_block = MagicMock(type="text", text="Done")

    response_tool = MagicMock()
    response_tool.content = [tool_block]
    response_tool.stop_reason = "tool_use"
    response_tool.usage = MagicMock(input_tokens=10, output_tokens=5)

    response_final = MagicMock()
    response_final.content = [text_block]
    response_final.stop_reason = "end_turn"
    response_final.usage = MagicMock(input_tokens=10, output_tokens=5)

    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return response_tool
        return response_final

    agent_with_low_turns = Agent(
        name="test",
        instructions="test",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        max_turns=2,
    )

    with patch.object(runner.router, "create_message", side_effect=mock_create):
        result = await runner.run(agent=agent_with_low_turns, task="Do stuff")
        assert result.turns <= 3  # max_turns applies to tool loops
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_runner.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/runner.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from airees.agent import Agent
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus, Event, EventType


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class RunResult:
    output: str
    turns: int
    token_usage: TokenUsage
    run_id: str
    agent_name: str
    messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Runner:
    router: ModelRouter
    tool_registry: ToolRegistry
    event_bus: EventBus

    async def run(
        self,
        agent: Agent,
        task: str,
        run_id: str | None = None,
    ) -> RunResult:
        run_id = run_id or str(uuid.uuid4())
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": task},
        ]
        total_input = 0
        total_output = 0
        turns = 0

        await self.event_bus.emit_async(Event(
            event_type=EventType.RUN_START,
            agent_name=agent.name,
            run_id=run_id,
            data={"task": task},
        ))

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_START,
            agent_name=agent.name,
            run_id=run_id,
        ))

        tools = (
            self.tool_registry.to_anthropic_format(agent.tools)
            if agent.tools
            else None
        )

        while turns < agent.max_turns:
            turns += 1

            response = await self.router.create_message(
                model=agent.model,
                system=agent.instructions,
                messages=messages,
                tools=tools,
            )

            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

            assistant_content = []
            output_text = ""

            for block in response.content:
                if block.type == "text":
                    output_text += block.text
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.TOOL_CALL,
                        agent_name=agent.name,
                        run_id=run_id,
                        data={"tool": block.name, "input": block.input},
                    ))
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            messages.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await self._execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                    await self.event_bus.emit_async(Event(
                        event_type=EventType.TOOL_RESULT,
                        agent_name=agent.name,
                        run_id=run_id,
                        data={"tool": block.name, "result": result},
                    ))

            messages.append({"role": "user", "content": tool_results})

        await self.event_bus.emit_async(Event(
            event_type=EventType.AGENT_COMPLETE,
            agent_name=agent.name,
            run_id=run_id,
            data={"output": output_text, "turns": turns},
        ))

        await self.event_bus.emit_async(Event(
            event_type=EventType.RUN_COMPLETE,
            agent_name=agent.name,
            run_id=run_id,
        ))

        return RunResult(
            output=output_text,
            turns=turns,
            token_usage=TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
            ),
            run_id=run_id,
            agent_name=agent.name,
            messages=messages,
        )

    async def _execute_tool(self, name: str, input_data: dict[str, Any]) -> str:
        if name not in self.tool_registry:
            return f"Error: Tool '{name}' not found"
        tools = self.tool_registry.scope([name])
        tool_def = tools[0]
        if tool_def.handler is None:
            return f"Error: Tool '{name}' has no handler"
        try:
            result = await tool_def.handler(input_data)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {e}"
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_runner.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/runner.py packages/core/tests/test_runner.py
git commit -m "feat: implement Runner with agent execution loop, tool calls, and events"
```

---

## Phase 6: Core - Memory Manager

### Task 12: Implement file-based memory

**Files:**
- Create: `airees/packages/core/airees/memory/__init__.py`
- Create: `airees/packages/core/airees/memory/file_store.py`
- Test: `airees/packages/core/tests/test_memory_file.py`

**Step 1: Write failing test**

```python
# tests/test_memory_file.py
import pytest
import tempfile
from pathlib import Path
from airees.memory.file_store import FileMemoryStore


@pytest.fixture
def store(tmp_path):
    return FileMemoryStore(base_path=tmp_path)


def test_write_and_read(store):
    store.write("researcher", "SOUL.md", "You are a research specialist.")
    content = store.read("researcher", "SOUL.md")
    assert content == "You are a research specialist."


def test_read_nonexistent_returns_empty(store):
    content = store.read("unknown", "SOUL.md")
    assert content == ""


def test_append(store):
    store.write("agent", "MEMORY.md", "Fact 1\n")
    store.append("agent", "MEMORY.md", "Fact 2\n")
    content = store.read("agent", "MEMORY.md")
    assert "Fact 1" in content
    assert "Fact 2" in content


def test_list_files(store):
    store.write("agent", "SOUL.md", "soul")
    store.write("agent", "MEMORY.md", "memory")
    files = store.list_files("agent")
    assert set(files) == {"SOUL.md", "MEMORY.md"}
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_memory_file.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/memory/__init__.py
from airees.memory.file_store import FileMemoryStore

__all__ = ["FileMemoryStore"]
```

```python
# airees/packages/core/airees/memory/file_store.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileMemoryStore:
    base_path: Path

    def _agent_path(self, agent_name: str) -> Path:
        path = self.base_path / agent_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, agent_name: str, filename: str, content: str) -> None:
        path = self._agent_path(agent_name) / filename
        path.write_text(content, encoding="utf-8")

    def read(self, agent_name: str, filename: str) -> str:
        path = self._agent_path(agent_name) / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def append(self, agent_name: str, filename: str, content: str) -> None:
        path = self._agent_path(agent_name) / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(content)

    def list_files(self, agent_name: str) -> list[str]:
        path = self._agent_path(agent_name)
        return [f.name for f in path.iterdir() if f.is_file()]
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_memory_file.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/memory packages/core/tests/test_memory_file.py
git commit -m "feat: implement FileMemoryStore for per-agent markdown memory"
```

---

### Task 13: Implement SQLite run store

**Files:**
- Create: `airees/packages/core/airees/memory/sqlite_store.py`
- Test: `airees/packages/core/tests/test_memory_sqlite.py`

**Step 1: Write failing test**

```python
# tests/test_memory_sqlite.py
import pytest
from airees.memory.sqlite_store import SQLiteRunStore


@pytest.fixture
async def store(tmp_path):
    s = SQLiteRunStore(db_path=tmp_path / "test.db")
    await s.initialize()
    return s


@pytest.mark.asyncio
async def test_save_and_get_run(store):
    store = await store
    await store.save_run(
        run_id="r1",
        agent_name="researcher",
        task="Find info",
        output="Here is info",
        turns=3,
        input_tokens=100,
        output_tokens=50,
    )
    run = await store.get_run("r1")
    assert run is not None
    assert run["agent_name"] == "researcher"
    assert run["output"] == "Here is info"
    assert run["turns"] == 3


@pytest.mark.asyncio
async def test_list_runs(store):
    store = await store
    await store.save_run("r1", "agent1", "task1", "out1", 1, 10, 5)
    await store.save_run("r2", "agent2", "task2", "out2", 2, 20, 10)
    runs = await store.list_runs()
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_get_nonexistent_run(store):
    store = await store
    run = await store.get_run("nonexistent")
    assert run is None
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_memory_sqlite.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/memory/sqlite_store.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass
class SQLiteRunStore:
    db_path: Path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    task TEXT NOT NULL,
                    output TEXT NOT NULL,
                    turns INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def save_run(
        self,
        run_id: str,
        agent_name: str,
        task: str,
        output: str,
        turns: int,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO runs
                   (run_id, agent_name, task, output, turns, input_tokens, output_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, agent_name, task, output, turns, input_tokens, output_tokens),
            )
            await db.commit()

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_memory_sqlite.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/memory/sqlite_store.py packages/core/tests/test_memory_sqlite.py
git commit -m "feat: implement SQLiteRunStore for run history persistence"
```

---

## Phase 7: Core - Orchestration Patterns

### Task 14: Implement Pipeline pattern

**Files:**
- Create: `airees/packages/core/airees/orchestration/__init__.py`
- Create: `airees/packages/core/airees/orchestration/pipeline.py`
- Test: `airees/packages/core/tests/test_orchestration_pipeline.py`

**Step 1: Write failing test**

```python
# tests/test_orchestration_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch
from airees.orchestration.pipeline import Pipeline, PipelineStep
from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.runner import Runner, RunResult, TokenUsage
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus


@pytest.fixture
def runner():
    router = ModelRouter(anthropic_api_key="test")
    return Runner(router=router, tool_registry=ToolRegistry(), event_bus=EventBus())


@pytest.fixture
def agents():
    return {
        "researcher": Agent(
            name="researcher",
            instructions="Research the topic.",
            model=ModelConfig(model_id="claude-sonnet-4-6"),
        ),
        "writer": Agent(
            name="writer",
            instructions="Write a report.",
            model=ModelConfig(model_id="claude-sonnet-4-6"),
        ),
    }


def test_pipeline_creation(agents):
    pipeline = Pipeline(
        name="research-pipeline",
        steps=[
            PipelineStep(agent=agents["researcher"], task_template="Research {{topic}}"),
            PipelineStep(agent=agents["writer"], task_template="Write report based on: {{previous_output}}"),
        ],
    )
    assert len(pipeline.steps) == 2


@pytest.mark.asyncio
async def test_pipeline_runs_sequentially(runner, agents):
    pipeline = Pipeline(
        name="test",
        steps=[
            PipelineStep(agent=agents["researcher"], task_template="Research AI"),
            PipelineStep(agent=agents["writer"], task_template="Write about: {{previous_output}}"),
        ],
    )

    run_result_1 = RunResult(
        output="AI is transformative",
        turns=1,
        token_usage=TokenUsage(input_tokens=50, output_tokens=20),
        run_id="r1",
        agent_name="researcher",
    )
    run_result_2 = RunResult(
        output="Report: AI is transformative and growing.",
        turns=1,
        token_usage=TokenUsage(input_tokens=60, output_tokens=30),
        run_id="r2",
        agent_name="writer",
    )

    with patch.object(
        runner, "run",
        new_callable=AsyncMock,
        side_effect=[run_result_1, run_result_2],
    ):
        result = await pipeline.execute(runner=runner, variables={"topic": "AI"})

    assert result.output == "Report: AI is transformative and growing."
    assert result.total_turns == 2
    assert len(result.step_results) == 2
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_orchestration_pipeline.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/orchestration/__init__.py
from airees.orchestration.pipeline import Pipeline, PipelineStep

__all__ = ["Pipeline", "PipelineStep"]
```

```python
# airees/packages/core/airees/orchestration/pipeline.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from airees.agent import Agent
from airees.runner import Runner, RunResult, TokenUsage


@dataclass(frozen=True)
class PipelineStep:
    agent: Agent
    task_template: str


@dataclass(frozen=True)
class PipelineResult:
    output: str
    total_turns: int
    total_tokens: TokenUsage
    step_results: list[RunResult]
    run_id: str


@dataclass(frozen=True)
class Pipeline:
    name: str
    steps: list[PipelineStep]

    async def execute(
        self,
        runner: Runner,
        variables: dict[str, str] | None = None,
        run_id: str | None = None,
    ) -> PipelineResult:
        import uuid
        run_id = run_id or str(uuid.uuid4())
        variables = dict(variables or {})
        step_results: list[RunResult] = []
        total_input = 0
        total_output = 0
        total_turns = 0

        for step in self.steps:
            task = self._interpolate(step.task_template, variables)
            result = await runner.run(
                agent=step.agent,
                task=task,
                run_id=run_id,
            )
            step_results.append(result)
            total_input += result.token_usage.input_tokens
            total_output += result.token_usage.output_tokens
            total_turns += result.turns
            variables["previous_output"] = result.output

        final_output = step_results[-1].output if step_results else ""

        return PipelineResult(
            output=final_output,
            total_turns=total_turns,
            total_tokens=TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
            ),
            step_results=step_results,
            run_id=run_id,
        )

    def _interpolate(self, template: str, variables: dict[str, str]) -> str:
        def replace(match: re.Match) -> str:
            key = match.group(1)
            return variables.get(key, match.group(0))
        return re.sub(r"\{\{(\w+)\}\}", replace, template)
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_orchestration_pipeline.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/orchestration packages/core/tests/test_orchestration_pipeline.py
git commit -m "feat: implement Pipeline orchestration pattern with variable interpolation"
```

---

### Task 15: Implement ParallelTeam pattern

**Files:**
- Create: `airees/packages/core/airees/orchestration/parallel.py`
- Test: `airees/packages/core/tests/test_orchestration_parallel.py`

**Step 1: Write failing test**

```python
# tests/test_orchestration_parallel.py
import pytest
from unittest.mock import AsyncMock, patch
from airees.orchestration.parallel import ParallelTeam, ParallelTask
from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.runner import Runner, RunResult, TokenUsage
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus


@pytest.fixture
def runner():
    router = ModelRouter(anthropic_api_key="test")
    return Runner(router=router, tool_registry=ToolRegistry(), event_bus=EventBus())


@pytest.fixture
def agents():
    return {
        "analyst_a": Agent(name="analyst_a", instructions="Analyze A.", model=ModelConfig(model_id="claude-sonnet-4-6")),
        "analyst_b": Agent(name="analyst_b", instructions="Analyze B.", model=ModelConfig(model_id="claude-sonnet-4-6")),
    }


@pytest.mark.asyncio
async def test_parallel_runs_concurrently(runner, agents):
    team = ParallelTeam(
        name="analysis-team",
        tasks=[
            ParallelTask(agent=agents["analyst_a"], task="Analyze market trends"),
            ParallelTask(agent=agents["analyst_b"], task="Analyze competitor data"),
        ],
    )

    result_a = RunResult(output="Trends up", turns=1, token_usage=TokenUsage(10, 5), run_id="r1", agent_name="analyst_a")
    result_b = RunResult(output="Competitor strong", turns=1, token_usage=TokenUsage(10, 5), run_id="r2", agent_name="analyst_b")

    with patch.object(runner, "run", new_callable=AsyncMock, side_effect=[result_a, result_b]):
        result = await team.execute(runner=runner)

    assert len(result.task_results) == 2
    assert result.total_turns == 2
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_orchestration_parallel.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/orchestration/parallel.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from airees.agent import Agent
from airees.runner import Runner, RunResult, TokenUsage


@dataclass(frozen=True)
class ParallelTask:
    agent: Agent
    task: str


@dataclass(frozen=True)
class ParallelResult:
    task_results: list[RunResult]
    total_turns: int
    total_tokens: TokenUsage
    run_id: str


@dataclass(frozen=True)
class ParallelTeam:
    name: str
    tasks: list[ParallelTask]

    async def execute(
        self,
        runner: Runner,
        run_id: str | None = None,
    ) -> ParallelResult:
        run_id = run_id or str(uuid.uuid4())

        async def run_task(task: ParallelTask) -> RunResult:
            return await runner.run(
                agent=task.agent,
                task=task.task,
                run_id=run_id,
            )

        results = await asyncio.gather(*[run_task(t) for t in self.tasks])
        result_list = list(results)

        total_input = sum(r.token_usage.input_tokens for r in result_list)
        total_output = sum(r.token_usage.output_tokens for r in result_list)
        total_turns = sum(r.turns for r in result_list)

        return ParallelResult(
            task_results=result_list,
            total_turns=total_turns,
            total_tokens=TokenUsage(input_tokens=total_input, output_tokens=total_output),
            run_id=run_id,
        )
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_orchestration_parallel.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/airees/orchestration/parallel.py packages/core/tests/test_orchestration_parallel.py
git commit -m "feat: implement ParallelTeam orchestration pattern with concurrent execution"
```

---

### Task 16: Implement TriageRouter pattern

**Files:**
- Create: `airees/packages/core/airees/orchestration/triage.py`
- Test: `airees/packages/core/tests/test_orchestration_triage.py`

**Step 1: Write failing test**

```python
# tests/test_orchestration_triage.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from airees.orchestration.triage import TriageRouter, Route
from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.runner import Runner, RunResult, TokenUsage
from airees.router.model_router import ModelRouter
from airees.tools.registry import ToolRegistry
from airees.events import EventBus


@pytest.fixture
def runner():
    router = ModelRouter(anthropic_api_key="test")
    return Runner(router=router, tool_registry=ToolRegistry(), event_bus=EventBus())


@pytest.fixture
def agents():
    return {
        "researcher": Agent(name="researcher", instructions="Research.", model=ModelConfig(model_id="claude-sonnet-4-6")),
        "coder": Agent(name="coder", instructions="Code.", model=ModelConfig(model_id="claude-sonnet-4-6")),
    }


@pytest.mark.asyncio
async def test_triage_routes_to_correct_agent(runner, agents):
    triage = TriageRouter(
        name="router",
        router_model=ModelConfig(model_id="claude-haiku-4-5"),
        routes=[
            Route(intent="needs research", agent=agents["researcher"]),
            Route(intent="needs coding", agent=agents["coder"]),
        ],
    )

    # Mock the router deciding "researcher"
    router_response = MagicMock()
    router_response.content = [MagicMock(type="text", text="researcher")]
    router_response.stop_reason = "end_turn"
    router_response.usage = MagicMock(input_tokens=20, output_tokens=5)

    agent_result = RunResult(
        output="Found the answer",
        turns=1,
        token_usage=TokenUsage(50, 20),
        run_id="r1",
        agent_name="researcher",
    )

    with patch.object(runner.router, "create_message", new_callable=AsyncMock, return_value=router_response):
        with patch.object(runner, "run", new_callable=AsyncMock, return_value=agent_result):
            result = await triage.execute(runner=runner, task="Find info about AI safety")

    assert result.selected_agent == "researcher"
    assert result.output == "Found the answer"
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_orchestration_triage.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/orchestration/triage.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from airees.agent import Agent
from airees.router.types import ModelConfig
from airees.runner import Runner, RunResult, TokenUsage


@dataclass(frozen=True)
class Route:
    intent: str
    agent: Agent


@dataclass(frozen=True)
class TriageResult:
    output: str
    selected_agent: str
    run_result: RunResult
    run_id: str


@dataclass(frozen=True)
class TriageRouter:
    name: str
    router_model: ModelConfig
    routes: list[Route]

    async def execute(
        self,
        runner: Runner,
        task: str,
        run_id: str | None = None,
    ) -> TriageResult:
        run_id = run_id or str(uuid.uuid4())

        agent_descriptions = "\n".join(
            f"- {route.agent.name}: {route.intent}"
            for route in self.routes
        )
        agent_names = [route.agent.name for route in self.routes]

        routing_prompt = (
            f"Given the following task, select the most appropriate agent.\n\n"
            f"Available agents:\n{agent_descriptions}\n\n"
            f"Task: {task}\n\n"
            f"Respond with ONLY the agent name, one of: {', '.join(agent_names)}"
        )

        response = await runner.router.create_message(
            model=self.router_model,
            system="You are a routing agent. Select the best agent for the task. Respond with only the agent name.",
            messages=[{"role": "user", "content": routing_prompt}],
        )

        selected_name = ""
        for block in response.content:
            if block.type == "text":
                selected_name = block.text.strip().lower()
                break

        agent_map = {route.agent.name.lower(): route.agent for route in self.routes}
        selected_agent = agent_map.get(selected_name)

        if selected_agent is None:
            selected_agent = self.routes[0].agent
            selected_name = selected_agent.name

        result = await runner.run(
            agent=selected_agent,
            task=task,
            run_id=run_id,
        )

        return TriageResult(
            output=result.output,
            selected_agent=selected_name,
            run_result=result,
            run_id=run_id,
        )
```

**Step 4: Run test**

```bash
pytest packages/core/tests/test_orchestration_triage.py -v
```
Expected: PASS

**Step 5: Update orchestration __init__.py and commit**

```python
# airees/packages/core/airees/orchestration/__init__.py
from airees.orchestration.pipeline import Pipeline, PipelineStep
from airees.orchestration.parallel import ParallelTeam, ParallelTask
from airees.orchestration.triage import TriageRouter, Route

__all__ = ["Pipeline", "PipelineStep", "ParallelTeam", "ParallelTask", "TriageRouter", "Route"]
```

```bash
git add packages/core/airees/orchestration packages/core/tests/test_orchestration_triage.py
git commit -m "feat: implement TriageRouter orchestration pattern with LLM-based routing"
```

---

## Phase 8: Core - CLI

### Task 17: Implement basic CLI with Click

**Files:**
- Create: `airees/packages/core/airees/cli/__init__.py`
- Create: `airees/packages/core/airees/cli/main.py`
- Test: `airees/packages/core/tests/test_cli.py`

**Note:** Add `click>=8.1.0` to core dependencies in `pyproject.toml`.

**Step 1: Write failing test**

```python
# tests/test_cli.py
from click.testing import CliRunner
from airees.cli.main import app


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Airees" in result.output


def test_cli_init(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--path", str(tmp_path / "myproject")])
    assert result.exit_code == 0
    assert (tmp_path / "myproject" / "airees.yaml").exists()
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/core/tests/test_cli.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/core/airees/cli/__init__.py
```

```python
# airees/packages/core/airees/cli/main.py
from __future__ import annotations

from pathlib import Path

import click

from airees import __version__


@click.group()
@click.version_option(version=__version__, prog_name="Airees")
def app() -> None:
    """Airees - Multi-agent orchestration platform."""
    pass


@app.command()
@click.option("--path", type=click.Path(), default=".", help="Project directory")
def init(path: str) -> None:
    """Initialize a new Airees project."""
    project_path = Path(path)
    project_path.mkdir(parents=True, exist_ok=True)

    config = project_path / "airees.yaml"
    config.write_text(
        "# Airees project configuration\n"
        "name: my-project\n"
        "version: 0.1.0\n\n"
        "providers:\n"
        "  anthropic:\n"
        "    # Set ANTHROPIC_API_KEY env var\n"
        "  openrouter:\n"
        "    # Set OPENROUTER_API_KEY env var (optional)\n\n"
        "agents: {}\n"
        "workflows: {}\n",
        encoding="utf-8",
    )

    agents_dir = project_path / "agents"
    agents_dir.mkdir(exist_ok=True)

    workflows_dir = project_path / "workflows"
    workflows_dir.mkdir(exist_ok=True)

    click.echo(f"Initialized Airees project at {project_path.resolve()}")


if __name__ == "__main__":
    app()
```

**Step 4: Run test**

```bash
pip install click && pytest packages/core/tests/test_cli.py -v
```
Expected: PASS

**Step 5: Update pyproject.toml to add click dep, then commit**

Add `"click>=8.1.0"` to dependencies in `packages/core/pyproject.toml`.

```bash
git add packages/core/airees/cli packages/core/tests/test_cli.py packages/core/pyproject.toml
git commit -m "feat: implement CLI with init command and project scaffolding"
```

---

## Phase 9: YAML Engine

### Task 18: Define JSON Schema for agent/workflow configs

**Files:**
- Create: `airees/packages/engine/airees_engine/schema.py`
- Test: `airees/packages/engine/tests/__init__.py`
- Test: `airees/packages/engine/tests/test_schema.py`

**Step 1: Write failing test**

```python
# tests/test_schema.py
import pytest
from airees_engine.schema import validate_agent_config, validate_workflow_config


def test_valid_agent_config():
    config = {
        "name": "researcher",
        "description": "Finds info",
        "model": "claude-sonnet-4-6",
        "instructions": "You are a researcher.",
        "tools": ["web_search"],
    }
    errors = validate_agent_config(config)
    assert errors == []


def test_invalid_agent_config_missing_name():
    config = {
        "description": "Finds info",
        "model": "claude-sonnet-4-6",
        "instructions": "You are a researcher.",
    }
    errors = validate_agent_config(config)
    assert len(errors) > 0
    assert any("name" in e for e in errors)


def test_valid_workflow_config():
    config = {
        "name": "my-pipeline",
        "description": "A pipeline",
        "pattern": "pipeline",
        "steps": [
            {"agent": "researcher", "task": "Research {{topic}}"},
            {"agent": "writer", "task": "Write about {{previous_output}}"},
        ],
    }
    errors = validate_workflow_config(config)
    assert errors == []


def test_invalid_workflow_missing_pattern():
    config = {
        "name": "bad-workflow",
        "steps": [],
    }
    errors = validate_workflow_config(config)
    assert len(errors) > 0
```

**Step 2: Run test to verify it fails**

```bash
pip install -e "packages/engine[dev]" && pytest packages/engine/tests/test_schema.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/engine/airees_engine/schema.py
from __future__ import annotations

import jsonschema

AGENT_SCHEMA = {
    "type": "object",
    "required": ["name", "instructions", "model"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "model": {"type": "string", "minLength": 1},
        "instructions": {"type": "string", "minLength": 1},
        "tools": {"type": "array", "items": {"type": "string"}},
        "max_turns": {"type": "integer", "minimum": 1, "maximum": 100},
        "memory": {
            "type": "object",
            "properties": {
                "personality": {"type": "string"},
                "context": {"type": "string"},
            },
        },
    },
}

WORKFLOW_SCHEMA = {
    "type": "object",
    "required": ["name", "pattern"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "pattern": {"type": "string", "enum": ["pipeline", "parallel", "shared_state", "triage"]},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["agent", "task"],
                "properties": {
                    "agent": {"type": "string"},
                    "task": {"type": "string"},
                },
            },
        },
        "agents": {"type": "object"},
        "variables": {"type": "object"},
    },
}


def validate_agent_config(config: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(AGENT_SCHEMA)
    return [e.message for e in validator.iter_errors(config)]


def validate_workflow_config(config: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(WORKFLOW_SCHEMA)
    return [e.message for e in validator.iter_errors(config)]
```

**Step 4: Run test**

```bash
pytest packages/engine/tests/test_schema.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/engine
git commit -m "feat: add JSON Schema validation for agent and workflow configs"
```

---

### Task 19: Implement YAML parser

**Files:**
- Create: `airees/packages/engine/airees_engine/parser.py`
- Test: `airees/packages/engine/tests/test_parser.py`

**Step 1: Write failing test**

```python
# tests/test_parser.py
import pytest
from pathlib import Path
from airees_engine.parser import parse_agent_file, parse_workflow_file


def test_parse_agent_file(tmp_path):
    agent_yaml = tmp_path / "researcher.yaml"
    agent_yaml.write_text("""
name: researcher
description: "Finds info"
model: claude-sonnet-4-6
instructions: |
  You are a research specialist.
tools:
  - web_search
  - web_fetch
max_turns: 15
""")
    config = parse_agent_file(agent_yaml)
    assert config["name"] == "researcher"
    assert config["model"] == "claude-sonnet-4-6"
    assert len(config["tools"]) == 2
    assert config["max_turns"] == 15


def test_parse_workflow_file(tmp_path):
    wf_yaml = tmp_path / "pipeline.yaml"
    wf_yaml.write_text("""
name: research-pipeline
description: "Research and write"
pattern: pipeline
steps:
  - agent: researcher
    task: "Research {{topic}}"
  - agent: writer
    task: "Write about {{previous_output}}"
variables:
  topic:
    description: "The topic"
    required: true
""")
    config = parse_workflow_file(wf_yaml)
    assert config["name"] == "research-pipeline"
    assert config["pattern"] == "pipeline"
    assert len(config["steps"]) == 2


def test_parse_invalid_yaml(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("name: \n  invalid: [unbalanced")
    with pytest.raises(ValueError):
        parse_agent_file(bad_yaml)
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/engine/tests/test_parser.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/engine/airees_engine/parser.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from airees_engine.schema import validate_agent_config, validate_workflow_config


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML mapping, got {type(data).__name__}")
        return data
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e


def parse_agent_file(path: Path) -> dict[str, Any]:
    config = _load_yaml(path)
    errors = validate_agent_config(config)
    if errors:
        raise ValueError(f"Invalid agent config in {path}: {'; '.join(errors)}")
    return config


def parse_workflow_file(path: Path) -> dict[str, Any]:
    config = _load_yaml(path)
    errors = validate_workflow_config(config)
    if errors:
        raise ValueError(f"Invalid workflow config in {path}: {'; '.join(errors)}")
    return config
```

**Step 4: Run test**

```bash
pytest packages/engine/tests/test_parser.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/engine/airees_engine/parser.py packages/engine/tests/test_parser.py
git commit -m "feat: implement YAML parser with validation for agent and workflow files"
```

---

### Task 20: Implement template resolver and archetype inheritance

**Files:**
- Create: `airees/packages/engine/airees_engine/resolver.py`
- Test: `airees/packages/engine/tests/test_resolver.py`

**Step 1: Write failing test**

```python
# tests/test_resolver.py
import pytest
from airees_engine.resolver import resolve_agent_config, resolve_variables


def test_resolve_variables():
    template = "Research {{topic}} and summarize findings about {{topic}}"
    result = resolve_variables(template, {"topic": "AI safety"})
    assert result == "Research AI safety and summarize findings about AI safety"


def test_resolve_variables_missing():
    template = "Research {{topic}}"
    result = resolve_variables(template, {})
    assert result == "Research {{topic}}"


def test_resolve_agent_with_archetype():
    archetypes = {
        "researcher": {
            "name": "researcher",
            "model": "claude-sonnet-4-6",
            "instructions": "You are a researcher.",
            "tools": ["web_search", "web_fetch"],
            "max_turns": 15,
        },
    }
    override = {
        "archetype": "researcher",
        "model": "openrouter/deepseek/deepseek-r1",
        "tools": ["web_search", "web_fetch", "arxiv_search"],
    }
    resolved = resolve_agent_config(override, archetypes)
    assert resolved["model"] == "openrouter/deepseek/deepseek-r1"
    assert "arxiv_search" in resolved["tools"]
    assert resolved["instructions"] == "You are a researcher."
    assert resolved["max_turns"] == 15
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/engine/tests/test_resolver.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/engine/airees_engine/resolver.py
from __future__ import annotations

import re
from typing import Any


def resolve_variables(template: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))
    return re.sub(r"\{\{(\w+)\}\}", replace, template)


def resolve_agent_config(
    config: dict[str, Any],
    archetypes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    archetype_name = config.get("archetype")
    if archetype_name is None:
        return dict(config)

    if archetype_name not in archetypes:
        raise ValueError(f"Unknown archetype: {archetype_name}")

    base = dict(archetypes[archetype_name])
    overrides = {k: v for k, v in config.items() if k != "archetype"}
    return {**base, **overrides}
```

**Step 4: Run test**

```bash
pytest packages/engine/tests/test_resolver.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/engine/airees_engine/resolver.py packages/engine/tests/test_resolver.py
git commit -m "feat: implement template resolver with variable interpolation and archetype inheritance"
```

---

### Task 21: Create archetype library

**Files:**
- Create: `airees/packages/engine/airees_engine/archetypes/researcher.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/coder.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/reviewer.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/planner.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/writer.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/analyst.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/router.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/security_auditor.yaml`
- Create: `airees/packages/engine/airees_engine/archetypes/loader.py`
- Test: `airees/packages/engine/tests/test_archetypes.py`

**Step 1: Write failing test**

```python
# tests/test_archetypes.py
from airees_engine.archetypes.loader import load_all_archetypes, load_archetype


def test_load_all_archetypes():
    archetypes = load_all_archetypes()
    assert len(archetypes) >= 8
    assert "researcher" in archetypes
    assert "coder" in archetypes
    assert "router" in archetypes


def test_archetype_has_required_fields():
    archetypes = load_all_archetypes()
    for name, config in archetypes.items():
        assert "name" in config, f"Archetype {name} missing 'name'"
        assert "model" in config, f"Archetype {name} missing 'model'"
        assert "instructions" in config, f"Archetype {name} missing 'instructions'"


def test_load_single_archetype():
    config = load_archetype("researcher")
    assert config["name"] == "researcher"
    assert "tools" in config
```

**Step 2: Run test to verify it fails**

```bash
pytest packages/engine/tests/test_archetypes.py -v
```
Expected: FAIL

**Step 3: Create the archetype YAML files and loader**

Each archetype YAML follows this pattern (showing researcher as example):

```yaml
# airees/packages/engine/airees_engine/archetypes/researcher.yaml
name: researcher
description: "Web research and information synthesis specialist"
model: claude-sonnet-4-6
instructions: |
  You are a research specialist. Your role is to find comprehensive,
  accurate information on any topic.

  When researching:
  - Search for multiple sources to cross-reference facts
  - Prioritize authoritative and recent sources
  - Present findings in structured, clear summaries
  - Always cite your sources with URLs
  - Acknowledge uncertainty when information is conflicting
tools:
  - web_search
  - web_fetch
  - file_write
max_turns: 15
```

Create similar files for all 8 archetypes with appropriate instructions, tools, and models. Then the loader:

```python
# airees/packages/engine/airees_engine/archetypes/loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ARCHETYPES_DIR = Path(__file__).parent


def load_archetype(name: str) -> dict[str, Any]:
    path = ARCHETYPES_DIR / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"Archetype not found: {name}")
    content = path.read_text(encoding="utf-8")
    return yaml.safe_load(content)


def load_all_archetypes() -> dict[str, dict[str, Any]]:
    archetypes = {}
    for path in ARCHETYPES_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        archetypes[data["name"]] = data
    return archetypes
```

**Step 4: Run test**

```bash
pytest packages/engine/tests/test_archetypes.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/engine/airees_engine/archetypes
git commit -m "feat: add 8 built-in agent archetypes with YAML configs and loader"
```

---

## Phase 10: FastAPI Server

### Task 22: Set up FastAPI app with agent CRUD routes

**Files:**
- Create: `airees/packages/server/airees_server/app.py`
- Create: `airees/packages/server/airees_server/routes/__init__.py`
- Create: `airees/packages/server/airees_server/routes/agents.py`
- Create: `airees/packages/server/airees_server/routes/archetypes.py`
- Create: `airees/packages/server/airees_server/routes/runs.py`
- Test: `airees/packages/server/tests/__init__.py`
- Test: `airees/packages/server/tests/test_routes.py`

**Step 1: Write failing test**

```python
# tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from airees_server.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(data_dir=tmp_path)
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_archetypes(client):
    response = client.get("/api/archetypes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8
    assert any(a["name"] == "researcher" for a in data)


def test_create_and_get_agent(client):
    agent_config = {
        "name": "my-researcher",
        "model": "claude-sonnet-4-6",
        "instructions": "You research things.",
        "tools": ["web_search"],
    }
    response = client.post("/api/agents", json=agent_config)
    assert response.status_code == 201

    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()
    assert any(a["name"] == "my-researcher" for a in agents)
```

**Step 2: Run test to verify it fails**

```bash
pip install -e "packages/server[dev]" && pytest packages/server/tests/test_routes.py -v
```
Expected: FAIL

**Step 3: Implement**

```python
# airees/packages/server/airees_server/app.py
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from airees_server.routes.agents import create_agents_router
from airees_server.routes.archetypes import create_archetypes_router
from airees_server.routes.runs import create_runs_router


def create_app(data_dir: Path | None = None) -> FastAPI:
    data_dir = data_dir or Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Airees", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.data_dir = data_dir
    app.state.agents = {}  # In-memory for now, SQLite later

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(create_agents_router(), prefix="/api")
    app.include_router(create_archetypes_router(), prefix="/api")
    app.include_router(create_runs_router(), prefix="/api")

    return app
```

```python
# airees/packages/server/airees_server/routes/__init__.py
```

```python
# airees/packages/server/airees_server/routes/agents.py
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    model: str
    instructions: str
    tools: list[str] = []
    description: str = ""
    max_turns: int = 10


def create_agents_router() -> APIRouter:
    router = APIRouter()

    @router.get("/agents")
    def list_agents(request: Request):
        return list(request.app.state.agents.values())

    @router.post("/agents", status_code=201)
    def create_agent(request: Request, agent: AgentCreate):
        if agent.name in request.app.state.agents:
            raise HTTPException(400, "Agent already exists")
        request.app.state.agents[agent.name] = agent.model_dump()
        return agent.model_dump()

    @router.get("/agents/{name}")
    def get_agent(request: Request, name: str):
        if name not in request.app.state.agents:
            raise HTTPException(404, "Agent not found")
        return request.app.state.agents[name]

    return router
```

```python
# airees/packages/server/airees_server/routes/archetypes.py
from __future__ import annotations

from fastapi import APIRouter
from airees_engine.archetypes.loader import load_all_archetypes


def create_archetypes_router() -> APIRouter:
    router = APIRouter()

    @router.get("/archetypes")
    def list_archetypes():
        archetypes = load_all_archetypes()
        return list(archetypes.values())

    return router
```

```python
# airees/packages/server/airees_server/routes/runs.py
from __future__ import annotations

from fastapi import APIRouter


def create_runs_router() -> APIRouter:
    router = APIRouter()

    @router.get("/runs")
    def list_runs():
        return []  # Placeholder

    return router
```

**Step 4: Run test**

```bash
pytest packages/server/tests/test_routes.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add packages/server
git commit -m "feat: add FastAPI server with agent CRUD, archetypes, and health endpoints"
```

---

### Task 23: Add WebSocket run streaming

**Files:**
- Create: `airees/packages/server/airees_server/ws/__init__.py`
- Create: `airees/packages/server/airees_server/ws/stream.py`
- Modify: `airees/packages/server/airees_server/app.py`
- Test: `airees/packages/server/tests/test_ws.py`

This task adds a WebSocket endpoint at `/ws/runs/{run_id}` that streams events from the EventBus to connected clients as JSON messages. Implementation includes a `RunManager` that creates a Runner, subscribes to events, and forwards them to WebSocket clients.

**Step 1: Write failing test, Step 2: Run, Step 3: Implement, Step 4: Verify, Step 5: Commit**

Follow the same TDD pattern. The WebSocket handler should:
- Accept connection at `/ws/runs/{run_id}`
- Subscribe to EventBus for that run_id
- Forward events as JSON: `{"type": "agent.start", "agent": "researcher", "data": {}}`
- Close when run completes

```bash
git commit -m "feat: add WebSocket endpoint for real-time run event streaming"
```

---

## Phase 11: Web UI Foundation

### Task 24: Set up Next.js app shell with navigation

**Files:**
- Create: `airees/packages/web/src/components/sidebar.tsx`
- Create: `airees/packages/web/src/components/header.tsx`
- Modify: `airees/packages/web/src/app/layout.tsx`
- Modify: `airees/packages/web/src/app/page.tsx`

**Step 1: Install dependencies**

```bash
cd packages/web
npm install @tanstack/react-query lucide-react
```

**Step 2: Create sidebar with navigation links**

Sidebar with links to: Dashboard, Agents, Builder, Runs, Settings. Use Lucide icons. Dark theme (gray-950 background).

**Step 3: Create dashboard page with placeholder cards**

Show cards for: Active Runs (count), Total Agents, Total Runs, Token Usage. Each card is a placeholder that will later fetch from FastAPI.

**Step 4: Verify build passes**

```bash
npm run build
```
Expected: Build succeeds

**Step 5: Commit**

```bash
git commit -m "feat: add Next.js app shell with sidebar navigation and dashboard placeholders"
```

---

### Task 25: Create Agent Library page

**Files:**
- Create: `airees/packages/web/src/app/agents/page.tsx`
- Create: `airees/packages/web/src/components/agent-card.tsx`
- Create: `airees/packages/web/src/lib/api.ts`

**Step 1: Create API client**

```typescript
// src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function fetchAgents() {
  const res = await fetch(`${API_BASE}/api/agents`)
  return res.json()
}

export async function fetchArchetypes() {
  const res = await fetch(`${API_BASE}/api/archetypes`)
  return res.json()
}

export async function createAgent(agent: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/api/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(agent),
  })
  return res.json()
}
```

**Step 2: Create agent card component**

Display: name, description, model, tools count, with "Use" button.

**Step 3: Create agents page**

Two sections: "Archetypes" (pre-built) and "My Agents" (custom). Grid layout.

**Step 4: Verify build, Step 5: Commit**

```bash
git commit -m "feat: add Agent Library page with archetype browser and agent cards"
```

---

### Task 26: Create Settings page

**Files:**
- Create: `airees/packages/web/src/app/settings/page.tsx`

Settings page with form fields for:
- Anthropic API Key (password input, saved to env/localStorage)
- OpenRouter API Key (optional)
- Default model selection (dropdown)

```bash
git commit -m "feat: add Settings page for API key and model configuration"
```

---

## Phase 12: Web UI - Visual Agent Builder

### Task 27: Set up React Flow canvas

**Files:**
- Create: `airees/packages/web/src/app/builder/page.tsx`
- Create: `airees/packages/web/src/components/flow-builder/canvas.tsx`
- Create: `airees/packages/web/src/components/flow-builder/agent-node.tsx`

**Step 1: Install React Flow**

```bash
cd packages/web
npm install @xyflow/react
```

**Step 2: Create agent node component**

Custom React Flow node that displays: agent name, model badge, tool count, connection handles (top/bottom).

**Step 3: Create canvas component**

React Flow canvas with:
- Background grid
- Controls (zoom, fit)
- MiniMap
- Drop zone for adding agents from sidebar panel

**Step 4: Create builder page**

Split layout: sidebar (archetype palette) + main area (canvas). Drag archetypes from palette onto canvas.

**Step 5: Verify build and commit**

```bash
git commit -m "feat: add visual agent builder with React Flow canvas and draggable agent nodes"
```

---

### Task 28: Add edge connections and pattern detection

**Files:**
- Modify: `airees/packages/web/src/components/flow-builder/canvas.tsx`
- Create: `airees/packages/web/src/lib/pattern-detector.ts`

**Step 1: Implement pattern detection**

```typescript
// src/lib/pattern-detector.ts
type Pattern = "pipeline" | "parallel" | "triage" | "shared_state" | "unknown"

export function detectPattern(nodes: Node[], edges: Edge[]): Pattern {
  // Pipeline: linear chain (each node has 1 outgoing, 1 incoming)
  // Parallel: one node fans out to multiple with no connections between them
  // Triage: one node fans out to multiple (same as parallel but with router)
  // Shared state: all nodes connected to a central "memory" node
}
```

**Step 2: Show detected pattern as badge on canvas**

**Step 3: Enable YAML export from canvas topology**

Button that generates YAML from the current node/edge configuration.

**Step 4: Verify build and commit**

```bash
git commit -m "feat: add edge connections, pattern auto-detection, and YAML export to builder"
```

---

## Phase 13: Web UI - Run Monitoring

### Task 29: Create Runs page with real-time streaming

**Files:**
- Create: `airees/packages/web/src/app/runs/page.tsx`
- Create: `airees/packages/web/src/app/runs/[id]/page.tsx`
- Create: `airees/packages/web/src/components/run-timeline.tsx`
- Create: `airees/packages/web/src/hooks/use-run-stream.ts`
- Create: `airees/packages/web/src/lib/ws.ts`

**Step 1: Create WebSocket client**

```typescript
// src/lib/ws.ts
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"

export function connectToRun(runId: string, onEvent: (event: RunEvent) => void) {
  const ws = new WebSocket(`${WS_BASE}/ws/runs/${runId}`)
  ws.onmessage = (msg) => onEvent(JSON.parse(msg.data))
  return ws
}
```

**Step 2: Create use-run-stream hook**

React hook that connects to WebSocket, accumulates events, and provides current state.

**Step 3: Create run timeline component**

Timeline view showing: agent activations (colored bars), tool calls (icons), handoffs (arrows), output text (expandable).

**Step 4: Create runs list page**

Table of all runs: name, status, agent count, duration, token usage.

**Step 5: Create run detail page**

Full-page view with timeline, live output panel, and cost counter.

**Step 6: Verify build and commit**

```bash
git commit -m "feat: add Runs page with WebSocket streaming and timeline visualization"
```

---

## Phase 14: Integration & Polish

### Task 30: Wire up end-to-end: UI -> FastAPI -> Core -> LLM

**Files:**
- Modify: `airees/packages/server/airees_server/routes/runs.py`
- Test: `airees/packages/server/tests/test_e2e.py`

**Step 1: Add POST /api/runs endpoint**

Accepts: `{ workflow: "pipeline", agents: [...], task: "..." }`
Executes via Runner, streams events via WebSocket.

**Step 2: Write integration test**

Test that creates an agent via API, starts a run, and receives events via WebSocket.

**Step 3: Test with real API key (manual)**

```bash
ANTHROPIC_API_KEY=sk-... python -m airees_server
# In another terminal:
curl -X POST http://localhost:8000/api/runs -d '{"agent": "researcher", "task": "What is quantum computing?"}'
```

**Step 4: Commit**

```bash
git commit -m "feat: wire end-to-end run execution from API to LLM with event streaming"
```

---

### Task 31: Run full test suite and verify coverage

**Step 1: Run all tests**

```bash
pytest packages/core/tests packages/engine/tests packages/server/tests -v --cov=packages --cov-report=term-missing
```
Expected: All tests pass, coverage >= 80%

**Step 2: Fix any failures**

**Step 3: Verify web build**

```bash
cd packages/web && npm run build
```

**Step 4: Final commit**

```bash
git commit -m "test: verify full test suite passes with 80%+ coverage"
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1. Scaffolding | 1-3 | Monorepo with 4 packages, Python venv, Next.js app |
| 2. Model Router | 4-7 | Anthropic + OpenRouter providers, ModelRouter dispatcher |
| 3. Agent & Tools | 8-9 | Agent dataclass, ToolRegistry with scoping |
| 4. Events | 10 | EventBus with sync/async handlers |
| 5. Runner | 11 | Agent execution loop with tool calls and events |
| 6. Memory | 12-13 | FileMemoryStore + SQLiteRunStore |
| 7. Orchestration | 14-16 | Pipeline, ParallelTeam, TriageRouter patterns |
| 8. CLI | 17 | `airees init` command |
| 9. YAML Engine | 18-21 | Schema validation, parser, resolver, 8 archetypes |
| 10. FastAPI Server | 22-23 | REST API + WebSocket streaming |
| 11. Web UI Foundation | 24-26 | App shell, Agent Library, Settings |
| 12. Visual Builder | 27-28 | React Flow canvas, pattern detection, YAML export |
| 13. Run Monitoring | 29 | Real-time timeline, WebSocket streaming |
| 14. Integration | 30-31 | End-to-end wiring, test coverage verification |

**Total: 31 tasks across 14 phases**
