# Airees Phase 6: Personal Autonomous Agent — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Gateway, channel adapters (CLI + Telegram), and conversation manager to transform Airees into a personal autonomous agent with smart model routing.

**Architecture:** Thin Gateway (Starlette ASGI) normalizes messages from channel adapters into InboundMessage types. A ConversationManager classifies complexity (Haiku/Sonnet/Opus), assembles personal context (SOUL + USER.md + memory), and routes to either a direct Runner call or the full BrainOrchestrator. Channel adapters are pluggable via a Protocol interface.

**Tech Stack:** Python 3.12, Starlette (ASGI), uvicorn, websockets, python-telegram-bot, existing Airees core (anthropic, aiosqlite, pydantic, click)

---

## Layer 1: Message Types & Channel Interface (Tasks 1-3)

### Task 1: InboundMessage, OutboundMessage, and Attachment Types

**Files:**
- Create: `airees/gateway/types.py`
- Create: `airees/gateway/__init__.py`
- Test: `tests/test_gateway_types.py`

**Step 1: Write the failing tests**

```python
"""Tests for gateway message types."""
import pytest
import time

from airees.gateway.types import Attachment, InboundMessage, OutboundMessage


def test_inbound_message_is_frozen():
    """InboundMessage should be immutable."""
    msg = InboundMessage(channel="cli", sender_id="user1", text="hello")
    with pytest.raises(AttributeError):
        msg.text = "changed"


def test_inbound_message_defaults():
    """InboundMessage should have sensible defaults."""
    msg = InboundMessage(channel="telegram", sender_id="u1", text="hi")
    assert msg.attachments == ()
    assert msg.reply_to is None
    assert msg.metadata == {}
    assert msg.timestamp > 0


def test_outbound_message_is_frozen():
    """OutboundMessage should be immutable."""
    msg = OutboundMessage(channel="cli", recipient_id="user1", text="hi")
    with pytest.raises(AttributeError):
        msg.text = "changed"


def test_attachment_is_frozen():
    """Attachment should be immutable."""
    att = Attachment(type="image", filename="pic.png")
    with pytest.raises(AttributeError):
        att.type = "file"


def test_attachment_defaults():
    """Attachment should default to None for optional fields."""
    att = Attachment(type="file")
    assert att.url is None
    assert att.data is None
    assert att.filename is None
    assert att.mime_type is None


def test_inbound_message_with_attachments():
    """InboundMessage should accept a tuple of Attachments."""
    att = Attachment(type="image", url="https://example.com/pic.png", mime_type="image/png")
    msg = InboundMessage(
        channel="telegram",
        sender_id="user1",
        text="Check this",
        attachments=(att,),
    )
    assert len(msg.attachments) == 1
    assert msg.attachments[0].mime_type == "image/png"
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'airees.gateway'`

**Step 3: Write minimal implementation**

Create `airees/gateway/__init__.py`:
```python
"""Gateway — message routing and channel adapters."""
```

Create `airees/gateway/types.py`:
```python
"""Immutable message types for the Gateway layer."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Attachment:
    """Immutable file/media attachment."""

    type: str  # "image", "file", "voice", "link"
    url: str | None = None
    data: bytes | None = None
    filename: str | None = None
    mime_type: str | None = None


@dataclass(frozen=True)
class InboundMessage:
    """Normalized incoming message from any channel."""

    channel: str
    sender_id: str
    text: str
    attachments: tuple[Attachment, ...] = ()
    reply_to: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboundMessage:
    """Response message to send back through a channel."""

    channel: str
    recipient_id: str
    text: str
    attachments: tuple[Attachment, ...] = ()
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_types.py -v`
Expected: 7 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/__init__.py airees/packages/core/airees/gateway/types.py airees/packages/core/tests/test_gateway_types.py
git commit -m "feat: add gateway message types (InboundMessage, OutboundMessage, Attachment)"
```

---

### Task 2: ChannelAdapter Protocol and AdapterRegistry

**Files:**
- Create: `airees/gateway/adapter.py`
- Test: `tests/test_gateway_adapter.py`

**Step 1: Write the failing tests**

```python
"""Tests for channel adapter protocol and registry."""
import asyncio
import pytest
from unittest.mock import AsyncMock

from airees.gateway.adapter import AdapterRegistry
from airees.gateway.types import InboundMessage, OutboundMessage


class FakeAdapter:
    """Minimal adapter that satisfies the ChannelAdapter protocol."""

    name = "fake"

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send(self, message: OutboundMessage) -> None:
        pass

    def set_message_handler(self, handler):
        self._handler = handler


def test_registry_register_and_get():
    """AdapterRegistry should register and retrieve adapters by name."""
    registry = AdapterRegistry()
    adapter = FakeAdapter()
    registry.register(adapter)
    assert registry.get("fake") is adapter


def test_registry_get_unknown_returns_none():
    """AdapterRegistry.get should return None for unknown channel."""
    registry = AdapterRegistry()
    assert registry.get("nonexistent") is None


def test_registry_list_channels():
    """AdapterRegistry.channels should list all registered channel names."""
    registry = AdapterRegistry()
    registry.register(FakeAdapter())
    assert "fake" in registry.channels


@pytest.mark.asyncio
async def test_registry_start_all():
    """start_all should call start() on every registered adapter."""
    adapter = FakeAdapter()
    adapter.start = AsyncMock()
    registry = AdapterRegistry()
    registry.register(adapter)
    await registry.start_all()
    adapter.start.assert_called_once()


@pytest.mark.asyncio
async def test_registry_stop_all():
    """stop_all should call stop() on every registered adapter."""
    adapter = FakeAdapter()
    adapter.stop = AsyncMock()
    registry = AdapterRegistry()
    registry.register(adapter)
    await registry.stop_all()
    adapter.stop.assert_called_once()


def test_registry_duplicate_name_raises():
    """Registering two adapters with the same name should raise ValueError."""
    registry = AdapterRegistry()
    registry.register(FakeAdapter())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeAdapter())
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'airees.gateway.adapter'`

**Step 3: Write minimal implementation**

Create `airees/gateway/adapter.py`:
```python
"""Channel adapter protocol and registry."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from airees.gateway.types import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)

MessageHandler = Callable[[InboundMessage], Awaitable[None]]


@runtime_checkable
class ChannelAdapter(Protocol):
    """Protocol that every channel adapter must satisfy."""

    name: str

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def send(self, message: OutboundMessage) -> None: ...
    def set_message_handler(self, handler: MessageHandler) -> None: ...


@dataclass
class AdapterRegistry:
    """Registry of channel adapters keyed by name."""

    _adapters: dict[str, ChannelAdapter] = field(default_factory=dict)

    def register(self, adapter: ChannelAdapter) -> None:
        """Register an adapter. Raises ValueError on duplicate name."""
        if adapter.name in self._adapters:
            raise ValueError(f"Channel '{adapter.name}' already registered")
        self._adapters[adapter.name] = adapter

    def get(self, channel: str) -> ChannelAdapter | None:
        """Retrieve adapter by channel name."""
        return self._adapters.get(channel)

    @property
    def channels(self) -> list[str]:
        """List all registered channel names."""
        return list(self._adapters.keys())

    async def start_all(self) -> None:
        """Start all registered adapters."""
        for adapter in self._adapters.values():
            try:
                await adapter.start()
                logger.info("Started channel adapter: %s", adapter.name)
            except Exception as e:
                logger.error("Failed to start adapter '%s': %s", adapter.name, e)

    async def stop_all(self) -> None:
        """Stop all registered adapters."""
        for adapter in self._adapters.values():
            try:
                await adapter.stop()
                logger.info("Stopped channel adapter: %s", adapter.name)
            except Exception as e:
                logger.warning("Error stopping adapter '%s': %s", adapter.name, e)
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_adapter.py -v`
Expected: 6 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/adapter.py airees/packages/core/tests/test_gateway_adapter.py
git commit -m "feat: add ChannelAdapter protocol and AdapterRegistry"
```

---

### Task 3: CLI Channel Adapter

**Files:**
- Create: `airees/gateway/adapters/__init__.py`
- Create: `airees/gateway/adapters/cli_adapter.py`
- Test: `tests/test_cli_adapter.py`

**Step 1: Write the failing tests**

```python
"""Tests for CLI channel adapter."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from airees.gateway.adapters.cli_adapter import CLIAdapter
from airees.gateway.types import InboundMessage, OutboundMessage


def test_cli_adapter_name():
    """CLIAdapter should have name 'cli'."""
    adapter = CLIAdapter()
    assert adapter.name == "cli"


def test_cli_adapter_set_message_handler():
    """set_message_handler should store the callback."""
    adapter = CLIAdapter()
    handler = AsyncMock()
    adapter.set_message_handler(handler)
    assert adapter._handler is handler


@pytest.mark.asyncio
async def test_cli_adapter_process_line():
    """_process_line should create InboundMessage and call handler."""
    adapter = CLIAdapter()
    handler = AsyncMock()
    adapter.set_message_handler(handler)

    await adapter._process_line("hello world")

    handler.assert_called_once()
    msg = handler.call_args[0][0]
    assert isinstance(msg, InboundMessage)
    assert msg.channel == "cli"
    assert msg.text == "hello world"
    assert msg.sender_id == "local"


@pytest.mark.asyncio
async def test_cli_adapter_send_prints_text(capsys):
    """send() should print the outbound message text to stdout."""
    adapter = CLIAdapter()
    msg = OutboundMessage(channel="cli", recipient_id="local", text="Hello user!")
    await adapter.send(msg)
    captured = capsys.readouterr()
    assert "Hello user!" in captured.out


@pytest.mark.asyncio
async def test_cli_adapter_ignores_empty_lines():
    """_process_line should skip empty/whitespace-only input."""
    adapter = CLIAdapter()
    handler = AsyncMock()
    adapter.set_message_handler(handler)

    await adapter._process_line("")
    await adapter._process_line("   ")

    handler.assert_not_called()


@pytest.mark.asyncio
async def test_cli_adapter_no_handler_no_crash():
    """_process_line should not crash if no handler is set."""
    adapter = CLIAdapter()
    await adapter._process_line("hello")  # Should not raise
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_cli_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'airees.gateway.adapters'`

**Step 3: Write minimal implementation**

Create `airees/gateway/adapters/__init__.py`:
```python
"""Channel adapter implementations."""
```

Create `airees/gateway/adapters/cli_adapter.py`:
```python
"""CLI channel adapter — stdin/stdout interaction."""
from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from airees.gateway.adapter import MessageHandler
from airees.gateway.types import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


@dataclass
class CLIAdapter:
    """Channel adapter for interactive CLI usage (stdin/stdout)."""

    name: str = "cli"
    prompt: str = "you> "
    _handler: MessageHandler | None = field(default=None, init=False, repr=False)
    _running: bool = field(default=False, init=False, repr=False)

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Register the callback for incoming messages."""
        self._handler = handler

    async def start(self) -> None:
        """Start reading from stdin in a background loop."""
        self._running = True
        logger.info("CLI adapter started — type your message and press Enter")

    async def stop(self) -> None:
        """Stop the read loop."""
        self._running = False
        logger.info("CLI adapter stopped")

    async def send(self, message: OutboundMessage) -> None:
        """Print the agent's response to stdout."""
        print(f"\nairees> {message.text}\n")

    async def run_interactive(self) -> None:
        """Blocking interactive loop — reads stdin line by line."""
        await self.start()
        try:
            while self._running:
                try:
                    line = await asyncio.to_thread(input, self.prompt)
                except EOFError:
                    break
                if line.strip().lower() in ("exit", "quit", "/quit"):
                    break
                await self._process_line(line)
        finally:
            await self.stop()

    async def _process_line(self, line: str) -> None:
        """Process a single input line into an InboundMessage."""
        text = line.strip()
        if not text:
            return
        if self._handler is None:
            logger.warning("No message handler set — dropping input")
            return

        msg = InboundMessage(
            channel="cli",
            sender_id="local",
            text=text,
        )
        await self._handler(msg)
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_cli_adapter.py -v`
Expected: 6 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/adapters/__init__.py airees/packages/core/airees/gateway/adapters/cli_adapter.py airees/packages/core/tests/test_cli_adapter.py
git commit -m "feat: add CLI channel adapter with stdin/stdout interaction"
```

---

## Layer 2: Conversation Manager (Tasks 4-7)

### Task 4: Complexity Classifier

**Files:**
- Create: `airees/gateway/complexity.py`
- Test: `tests/test_complexity.py`

**Step 1: Write the failing tests**

```python
"""Tests for complexity classifier."""
import pytest
from unittest.mock import AsyncMock

from airees.gateway.complexity import Complexity, classify_complexity


def test_complexity_enum_values():
    """Complexity should have QUICK, MODERATE, COMPLEX levels."""
    assert Complexity.QUICK.value == "quick"
    assert Complexity.MODERATE.value == "moderate"
    assert Complexity.COMPLEX.value == "complex"


def test_complexity_model_property():
    """Each complexity level should map to a model tier."""
    assert "haiku" in Complexity.QUICK.model_hint
    assert "sonnet" in Complexity.MODERATE.model_hint
    assert "opus" in Complexity.COMPLEX.model_hint


@pytest.mark.asyncio
async def test_classify_simple_greeting():
    """Greetings and simple questions should be QUICK."""
    result = await classify_complexity("hello")
    assert result == Complexity.QUICK


@pytest.mark.asyncio
async def test_classify_simple_question():
    """Short factual questions should be QUICK."""
    result = await classify_complexity("What time is it?")
    assert result == Complexity.QUICK


@pytest.mark.asyncio
async def test_classify_moderate_task():
    """Summarization and analysis should be MODERATE."""
    result = await classify_complexity("Summarize the key points of this 5-page document about climate change")
    assert result == Complexity.MODERATE


@pytest.mark.asyncio
async def test_classify_complex_goal():
    """Multi-step planning should be COMPLEX."""
    result = await classify_complexity("Plan my entire week including meetings, gym, meals, and research deadlines")
    assert result == Complexity.COMPLEX


@pytest.mark.asyncio
async def test_classify_complex_keywords():
    """Messages with planning/research keywords should be COMPLEX."""
    result = await classify_complexity("Research the best approach to migrate our database to PostgreSQL and create a migration plan")
    assert result == Complexity.COMPLEX
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_complexity.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `airees/gateway/complexity.py`:
```python
"""Complexity classifier — routes messages to appropriate model tier.

Uses keyword heuristics for instant classification (no LLM call needed).
This keeps the classifier itself at zero cost. Falls back to MODERATE
for ambiguous input.
"""
from __future__ import annotations

import re
from enum import Enum

# Patterns that indicate simple/quick interactions
_QUICK_PATTERNS = [
    re.compile(r"^(hi|hello|hey|yo|sup|thanks|thank you|ok|okay|yes|no|bye|good morning|good night)\b", re.IGNORECASE),
    re.compile(r"^(what|when|where|who|how)\s+(is|are|was|were|do|does|did|time|day)\b", re.IGNORECASE),
    re.compile(r"^(tell me|remind me|set|cancel|stop|start)\b", re.IGNORECASE),
]

# Patterns that indicate complex multi-step goals
_COMPLEX_PATTERNS = [
    re.compile(r"\b(plan|design|architect|build|create|develop|implement|migrate|refactor)\b.*\b(and|then|also|including|across|entire|full|complete)\b", re.IGNORECASE),
    re.compile(r"\b(research|investigate|analyze|compare|evaluate)\b.*\b(and|then|create|build|plan|report)\b", re.IGNORECASE),
    re.compile(r"\b(step.by.step|multi.step|end.to.end|comprehensive|thorough)\b", re.IGNORECASE),
]

# Short messages are almost always quick
_SHORT_THRESHOLD = 30
# Long messages with detail tend to be complex
_LONG_THRESHOLD = 200


class Complexity(Enum):
    """Message complexity level with associated model hint."""

    QUICK = "quick"
    MODERATE = "moderate"
    COMPLEX = "complex"

    @property
    def model_hint(self) -> str:
        """Suggested model tier for this complexity."""
        return {
            Complexity.QUICK: "haiku",
            Complexity.MODERATE: "sonnet",
            Complexity.COMPLEX: "opus",
        }[self]


async def classify_complexity(text: str) -> Complexity:
    """Classify message complexity using keyword heuristics.

    Zero-cost classification (no LLM call). Rules:
    1. Short messages (<30 chars) or matching quick patterns -> QUICK
    2. Matching complex patterns or long messages (>200 chars) -> COMPLEX
    3. Everything else -> MODERATE
    """
    stripped = text.strip()

    # Short messages are quick
    if len(stripped) < _SHORT_THRESHOLD:
        return Complexity.QUICK

    # Check quick patterns
    for pattern in _QUICK_PATTERNS:
        if pattern.search(stripped):
            return Complexity.QUICK

    # Check complex patterns
    for pattern in _COMPLEX_PATTERNS:
        if pattern.search(stripped):
            return Complexity.COMPLEX

    # Long detailed messages tend to be complex
    if len(stripped) > _LONG_THRESHOLD:
        return Complexity.COMPLEX

    return Complexity.MODERATE
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_complexity.py -v`
Expected: 7 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/complexity.py airees/packages/core/tests/test_complexity.py
git commit -m "feat: add zero-cost complexity classifier with keyword heuristics"
```

---

### Task 5: Session and Turn Manager

**Files:**
- Create: `airees/gateway/session.py`
- Test: `tests/test_session.py`

**Step 1: Write the failing tests**

```python
"""Tests for conversation session management."""
import pytest
import time

from airees.gateway.session import Session, SessionStore


def test_session_creates_with_defaults():
    """Session should initialize with empty history and timestamps."""
    session = Session(channel="cli", sender_id="user1")
    assert session.channel == "cli"
    assert session.sender_id == "user1"
    assert session.messages == []
    assert session.created_at > 0
    assert session.updated_at > 0


def test_session_add_turn():
    """add_turn should append user/assistant pair to history."""
    session = Session(channel="cli", sender_id="user1")
    session.add_turn(user_text="hello", assistant_text="hi there")
    assert len(session.messages) == 2
    assert session.messages[0]["role"] == "user"
    assert session.messages[0]["content"] == "hello"
    assert session.messages[1]["role"] == "assistant"
    assert session.messages[1]["content"] == "hi there"


def test_session_get_context_messages():
    """get_context_messages should return recent turns up to max_turns."""
    session = Session(channel="cli", sender_id="user1")
    for i in range(10):
        session.add_turn(user_text=f"msg {i}", assistant_text=f"reply {i}")
    # 10 turns = 20 messages; max_turns=3 should return last 6 messages
    context = session.get_context_messages(max_turns=3)
    assert len(context) == 6
    assert context[0]["content"] == "msg 7"


def test_session_get_context_returns_all_if_fewer():
    """get_context_messages should return all if fewer than max_turns."""
    session = Session(channel="cli", sender_id="user1")
    session.add_turn(user_text="hi", assistant_text="hello")
    context = session.get_context_messages(max_turns=10)
    assert len(context) == 2


def test_session_store_get_or_create():
    """SessionStore should create new sessions on first access."""
    store = SessionStore()
    session = store.get_or_create("cli", "user1")
    assert session.channel == "cli"
    assert session.sender_id == "user1"


def test_session_store_returns_existing():
    """SessionStore should return existing session on second access."""
    store = SessionStore()
    s1 = store.get_or_create("cli", "user1")
    s1.add_turn(user_text="hi", assistant_text="hello")
    s2 = store.get_or_create("cli", "user1")
    assert len(s2.messages) == 2  # Same session, has history


def test_session_store_separates_channels():
    """SessionStore should keep separate sessions per channel+sender."""
    store = SessionStore()
    s1 = store.get_or_create("cli", "user1")
    s2 = store.get_or_create("telegram", "user1")
    s1.add_turn(user_text="cli msg", assistant_text="reply")
    assert len(s2.messages) == 0  # Different session


def test_session_store_active_sessions():
    """active_sessions should return count of stored sessions."""
    store = SessionStore()
    store.get_or_create("cli", "u1")
    store.get_or_create("telegram", "u2")
    assert store.active_sessions == 2
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_session.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `airees/gateway/session.py`:
```python
"""Conversation session management."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    """Tracks a single conversation's message history."""

    channel: str
    sender_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_turn(self, *, user_text: str, assistant_text: str) -> None:
        """Append a user/assistant exchange to the history."""
        self.messages.append({"role": "user", "content": user_text})
        self.messages.append({"role": "assistant", "content": assistant_text})
        self.updated_at = time.time()

    def get_context_messages(self, max_turns: int = 10) -> list[dict[str, str]]:
        """Return the most recent turns (each turn = 2 messages).

        Args:
            max_turns: Maximum number of user/assistant pairs to return.

        Returns:
            List of message dicts, most recent turns only.
        """
        max_messages = max_turns * 2
        if len(self.messages) <= max_messages:
            return list(self.messages)
        return list(self.messages[-max_messages:])


@dataclass
class SessionStore:
    """In-memory store for active conversation sessions."""

    _sessions: dict[str, Session] = field(default_factory=dict)

    def get_or_create(self, channel: str, sender_id: str) -> Session:
        """Retrieve existing session or create a new one."""
        key = f"{channel}:{sender_id}"
        if key not in self._sessions:
            self._sessions[key] = Session(channel=channel, sender_id=sender_id)
        return self._sessions[key]

    @property
    def active_sessions(self) -> int:
        """Count of active sessions."""
        return len(self._sessions)
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_session.py -v`
Expected: 8 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/session.py airees/packages/core/tests/test_session.py
git commit -m "feat: add conversation session and turn management"
```

---

### Task 6: Personal Context Loader (USER.md)

**Files:**
- Create: `airees/gateway/personal_context.py`
- Test: `tests/test_personal_context.py`

**Step 1: Write the failing tests**

```python
"""Tests for personal context loading."""
import pytest
from pathlib import Path
from unittest.mock import patch

from airees.gateway.personal_context import PersonalContext, load_personal_context

_SAMPLE_USER_MD = """---
name: Nathaniel
timezone: Europe/London
---

# Preferences
- Communication style: direct and concise
- Preferred language: English

# Projects
- Airees: multi-agent orchestration platform
- DTE Site: web application
"""


def test_personal_context_is_frozen():
    """PersonalContext should be immutable."""
    ctx = PersonalContext(name="Test", timezone="UTC", content="hello", raw="hello")
    with pytest.raises(AttributeError):
        ctx.name = "Changed"


def test_load_personal_context_parses_frontmatter(tmp_path):
    """load_personal_context should parse YAML frontmatter from USER.md."""
    user_md = tmp_path / "USER.md"
    user_md.write_text(_SAMPLE_USER_MD, encoding="utf-8")

    ctx = load_personal_context(user_md)
    assert ctx.name == "Nathaniel"
    assert ctx.timezone == "Europe/London"
    assert "Communication style" in ctx.content


def test_load_personal_context_default_when_missing(tmp_path):
    """load_personal_context should return default if file doesn't exist."""
    missing = tmp_path / "USER.md"
    ctx = load_personal_context(missing)
    assert ctx.name == "User"
    assert ctx.timezone == "UTC"
    assert ctx.content == ""


def test_personal_context_to_prompt():
    """to_prompt should format context for LLM injection."""
    ctx = PersonalContext(
        name="Nathaniel",
        timezone="Europe/London",
        content="Likes concise replies.",
        raw="raw",
    )
    prompt = ctx.to_prompt()
    assert "Nathaniel" in prompt
    assert "Europe/London" in prompt
    assert "concise replies" in prompt


def test_load_personal_context_no_frontmatter(tmp_path):
    """load_personal_context should handle files without YAML frontmatter."""
    user_md = tmp_path / "USER.md"
    user_md.write_text("Just plain text about the user.", encoding="utf-8")

    ctx = load_personal_context(user_md)
    assert ctx.name == "User"
    assert "plain text" in ctx.content
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_personal_context.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `airees/gateway/personal_context.py`:
```python
"""Personal context loader — parses USER.md for user profile injection."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class PersonalContext:
    """Immutable user profile loaded from USER.md."""

    name: str
    timezone: str
    content: str
    raw: str

    def to_prompt(self) -> str:
        """Format as a prompt section for LLM context injection."""
        lines = [
            f"The user's name is {self.name}.",
            f"Their timezone is {self.timezone}.",
        ]
        if self.content:
            lines.append(f"\nUser context:\n{self.content}")
        return "\n".join(lines)


def load_personal_context(path: Path) -> PersonalContext:
    """Load USER.md from path, returning defaults if missing."""
    if not path.exists():
        logger.info("USER.md not found at %s — using defaults", path)
        return PersonalContext(name="User", timezone="UTC", content="", raw="")

    raw = path.read_text(encoding="utf-8")
    return _parse_user_md(raw)


def _parse_user_md(raw: str) -> PersonalContext:
    """Parse USER.md with optional YAML frontmatter."""
    match = _FRONTMATTER_RE.match(raw)
    if match:
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        content = raw[match.end():].strip()
    else:
        meta = {}
        content = raw.strip()

    return PersonalContext(
        name=meta.get("name", "User"),
        timezone=meta.get("timezone", "UTC"),
        content=content,
        raw=raw,
    )
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_personal_context.py -v`
Expected: 5 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/personal_context.py airees/packages/core/tests/test_personal_context.py
git commit -m "feat: add personal context loader for USER.md"
```

---

### Task 7: ConversationManager

**Files:**
- Create: `airees/gateway/conversation.py`
- Test: `tests/test_conversation_manager.py`

**Step 1: Write the failing tests**

```python
"""Tests for ConversationManager — context assembly, routing, response."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from airees.gateway.conversation import ConversationManager
from airees.gateway.complexity import Complexity
from airees.gateway.types import InboundMessage, OutboundMessage
from airees.gateway.session import SessionStore
from airees.gateway.personal_context import PersonalContext


def _make_manager(tmp_path: Path) -> ConversationManager:
    """Create a ConversationManager with mocked dependencies."""
    router = MagicMock()
    event_bus = MagicMock()
    soul_path = tmp_path / "SOUL.md"
    user_path = tmp_path / "USER.md"
    return ConversationManager(
        router=router,
        event_bus=event_bus,
        soul_path=soul_path,
        user_path=user_path,
    )


def test_conversation_manager_creates():
    """ConversationManager should initialize with a SessionStore."""
    manager = ConversationManager(
        router=MagicMock(),
        event_bus=MagicMock(),
    )
    assert manager.sessions.active_sessions == 0


@pytest.mark.asyncio
async def test_handle_quick_message(tmp_path):
    """Quick messages should use direct runner (Haiku), not orchestrator."""
    manager = _make_manager(tmp_path)
    manager._run_quick = AsyncMock(return_value="Hello!")

    msg = InboundMessage(channel="cli", sender_id="user1", text="hi")
    response = await manager.handle(msg)

    assert response.text == "Hello!"
    assert response.channel == "cli"
    assert response.recipient_id == "user1"
    manager._run_quick.assert_called_once()


@pytest.mark.asyncio
async def test_handle_complex_message_uses_orchestrator(tmp_path):
    """Complex messages should route through the brain orchestrator."""
    manager = _make_manager(tmp_path)
    manager.orchestrator = MagicMock()
    manager._run_orchestrated = AsyncMock(return_value="Plan created and executed.")

    msg = InboundMessage(
        channel="cli",
        sender_id="user1",
        text="Research the best approach to migrate our database to PostgreSQL and create a comprehensive migration plan",
    )
    response = await manager.handle(msg)

    assert response.text == "Plan created and executed."
    manager._run_orchestrated.assert_called_once()


@pytest.mark.asyncio
async def test_handle_records_turn(tmp_path):
    """handle() should record the turn in the session history."""
    manager = _make_manager(tmp_path)
    manager._run_quick = AsyncMock(return_value="Reply")

    msg = InboundMessage(channel="cli", sender_id="user1", text="hello")
    await manager.handle(msg)

    session = manager.sessions.get_or_create("cli", "user1")
    assert len(session.messages) == 2
    assert session.messages[0]["content"] == "hello"
    assert session.messages[1]["content"] == "Reply"


@pytest.mark.asyncio
async def test_handle_includes_history_in_context(tmp_path):
    """handle() should pass conversation history to the runner."""
    manager = _make_manager(tmp_path)
    calls = []

    async def mock_quick(text, context_messages, personal_context):
        calls.append(context_messages)
        return "Reply"

    manager._run_quick = mock_quick

    msg1 = InboundMessage(channel="cli", sender_id="user1", text="hello")
    await manager.handle(msg1)

    msg2 = InboundMessage(channel="cli", sender_id="user1", text="how are you")
    await manager.handle(msg2)

    # Second call should include history from first turn
    assert len(calls) == 2
    assert len(calls[1]) == 2  # Previous turn (user + assistant)
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_conversation_manager.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `airees/gateway/conversation.py`:
```python
"""ConversationManager — routes messages to the right model tier.

Assembles context (SOUL + USER + history), classifies complexity,
and dispatches to either a direct Haiku/Sonnet call or the full
BrainOrchestrator for complex goals.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from airees.gateway.complexity import Complexity, classify_complexity
from airees.gateway.personal_context import PersonalContext, load_personal_context
from airees.gateway.session import SessionStore
from airees.gateway.types import InboundMessage, OutboundMessage
from airees.soul import Soul, load_soul

logger = logging.getLogger(__name__)


@dataclass
class ConversationManager:
    """Routes inbound messages through the appropriate processing tier.

    QUICK -> direct LLM call via Runner (Haiku)
    MODERATE -> direct LLM call via Runner (Sonnet)
    COMPLEX -> full BrainOrchestrator (Opus, plan-execute-evaluate)
    """

    router: Any  # ModelRouter
    event_bus: Any  # EventBus
    soul_path: Path = Path("data/SOUL.md")
    user_path: Path = Path("data/USER.md")
    orchestrator: Any = None  # BrainOrchestrator (optional, for COMPLEX)
    sessions: SessionStore = field(default_factory=SessionStore)
    max_context_turns: int = 10
    _soul: Soul | None = field(default=None, init=False, repr=False)
    _personal: PersonalContext | None = field(default=None, init=False, repr=False)

    def _get_soul(self) -> Soul:
        """Lazy-load SOUL.md."""
        if self._soul is None:
            self._soul = load_soul(self.soul_path)
        return self._soul

    def _get_personal(self) -> PersonalContext:
        """Lazy-load USER.md."""
        if self._personal is None:
            self._personal = load_personal_context(self.user_path)
        return self._personal

    async def handle(self, message: InboundMessage) -> OutboundMessage:
        """Process an inbound message and return a response.

        1. Get or create session
        2. Load context (SOUL + USER + history)
        3. Classify complexity
        4. Route to appropriate handler
        5. Record turn in session
        6. Return OutboundMessage
        """
        session = self.sessions.get_or_create(message.channel, message.sender_id)
        context_messages = session.get_context_messages(max_turns=self.max_context_turns)
        personal = self._get_personal()
        complexity = await classify_complexity(message.text)

        logger.info(
            "Message from %s/%s — complexity=%s",
            message.channel,
            message.sender_id,
            complexity.value,
        )

        if complexity == Complexity.COMPLEX and self.orchestrator is not None:
            response_text = await self._run_orchestrated(
                message.text, context_messages, personal
            )
        else:
            response_text = await self._run_quick(
                message.text, context_messages, personal
            )

        session.add_turn(user_text=message.text, assistant_text=response_text)

        return OutboundMessage(
            channel=message.channel,
            recipient_id=message.sender_id,
            text=response_text,
        )

    async def _run_quick(
        self,
        text: str,
        context_messages: list[dict[str, str]],
        personal_context: PersonalContext,
    ) -> str:
        """Handle QUICK/MODERATE messages with a direct LLM call."""
        soul = self._get_soul()
        system_prompt = (
            f"{soul.to_prompt()}\n\n"
            f"{personal_context.to_prompt()}\n\n"
            "Respond concisely and helpfully."
        )

        messages = list(context_messages)
        messages.append({"role": "user", "content": text})

        try:
            response = await self.router.create_message(
                model="anthropic/claude-haiku-4-5",
                system=system_prompt,
                messages=messages,
                max_tokens=1024,
            )
            return response.content[0].text
        except Exception as e:
            logger.error("Quick response failed: %s", e)
            return f"I encountered an error: {e}"

    async def _run_orchestrated(
        self,
        text: str,
        context_messages: list[dict[str, str]],
        personal_context: PersonalContext,
    ) -> str:
        """Handle COMPLEX messages through the full BrainOrchestrator."""
        try:
            goal_id = await self.orchestrator.submit_goal(text)
            result = await self.orchestrator.execute_goal(goal_id)
            return result
        except Exception as e:
            logger.error("Orchestrated response failed: %s", e)
            return f"I encountered an error processing your complex request: {e}"
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_conversation_manager.py -v`
Expected: 5 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/conversation.py airees/packages/core/tests/test_conversation_manager.py
git commit -m "feat: add ConversationManager with complexity routing"
```

---

## Layer 3: Gateway Server & Wiring (Tasks 8-11)

### Task 8: Gateway Server

**Files:**
- Create: `airees/gateway/server.py`
- Test: `tests/test_gateway_server.py`

**Step 1: Write the failing tests**

```python
"""Tests for Gateway ASGI server."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from airees.gateway.server import Gateway
from airees.gateway.types import InboundMessage, OutboundMessage


def test_gateway_creates():
    """Gateway should initialize with conversation manager and adapter registry."""
    conversation_manager = MagicMock()
    gateway = Gateway(conversation_manager=conversation_manager)
    assert gateway.conversation_manager is conversation_manager
    assert gateway.adapters is not None


@pytest.mark.asyncio
async def test_gateway_handle_message_routes_to_manager():
    """handle_message should pass InboundMessage to ConversationManager."""
    conversation_manager = MagicMock()
    conversation_manager.handle = AsyncMock(
        return_value=OutboundMessage(channel="cli", recipient_id="user1", text="Reply")
    )
    gateway = Gateway(conversation_manager=conversation_manager)

    msg = InboundMessage(channel="cli", sender_id="user1", text="hello")
    response = await gateway.handle_message(msg)

    conversation_manager.handle.assert_called_once_with(msg)
    assert response.text == "Reply"


@pytest.mark.asyncio
async def test_gateway_handle_message_sends_via_adapter():
    """handle_message should send the response back through the correct adapter."""
    conversation_manager = MagicMock()
    conversation_manager.handle = AsyncMock(
        return_value=OutboundMessage(channel="cli", recipient_id="user1", text="Reply")
    )

    adapter = MagicMock()
    adapter.name = "cli"
    adapter.send = AsyncMock()

    gateway = Gateway(conversation_manager=conversation_manager)
    gateway.adapters.register(adapter)

    msg = InboundMessage(channel="cli", sender_id="user1", text="hello")
    await gateway.handle_message(msg)

    adapter.send.assert_called_once()


@pytest.mark.asyncio
async def test_gateway_handle_message_unknown_adapter():
    """handle_message should still return response even if adapter missing."""
    conversation_manager = MagicMock()
    conversation_manager.handle = AsyncMock(
        return_value=OutboundMessage(channel="unknown", recipient_id="u1", text="Reply")
    )
    gateway = Gateway(conversation_manager=conversation_manager)

    msg = InboundMessage(channel="unknown", sender_id="u1", text="hi")
    response = await gateway.handle_message(msg)
    assert response.text == "Reply"  # Should not crash


@pytest.mark.asyncio
async def test_gateway_start_registers_handler_on_adapters():
    """start() should call set_message_handler on all adapters."""
    conversation_manager = MagicMock()
    adapter = MagicMock()
    adapter.name = "cli"
    adapter.set_message_handler = MagicMock()
    adapter.start = AsyncMock()

    gateway = Gateway(conversation_manager=conversation_manager)
    gateway.adapters.register(adapter)
    await gateway.start()

    adapter.set_message_handler.assert_called_once()
    adapter.start.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_server.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `airees/gateway/server.py`:
```python
"""Gateway server — routes messages between adapters and ConversationManager."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from airees.gateway.adapter import AdapterRegistry
from airees.gateway.conversation import ConversationManager
from airees.gateway.types import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


@dataclass
class Gateway:
    """Central message router connecting channel adapters to the brain.

    Handles the full lifecycle:
    1. Receive InboundMessage from adapter
    2. Route to ConversationManager
    3. Send OutboundMessage back through adapter
    """

    conversation_manager: ConversationManager
    adapters: AdapterRegistry = field(default_factory=AdapterRegistry)

    async def start(self) -> None:
        """Start the gateway — wire handlers and start all adapters."""
        for channel in self.adapters.channels:
            adapter = self.adapters.get(channel)
            if adapter:
                adapter.set_message_handler(self.handle_message)
        await self.adapters.start_all()
        logger.info("Gateway started with channels: %s", self.adapters.channels)

    async def stop(self) -> None:
        """Stop all adapters."""
        await self.adapters.stop_all()
        logger.info("Gateway stopped")

    async def handle_message(self, message: InboundMessage) -> OutboundMessage:
        """Process an inbound message and route response back.

        Args:
            message: Normalized inbound message from any channel.

        Returns:
            OutboundMessage with the agent's response.
        """
        response = await self.conversation_manager.handle(message)

        adapter = self.adapters.get(response.channel)
        if adapter:
            try:
                await adapter.send(response)
            except Exception as e:
                logger.error(
                    "Failed to send response via '%s': %s", response.channel, e
                )
        else:
            logger.warning("No adapter for channel '%s'", response.channel)

        return response
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_server.py -v`
Expected: 5 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/server.py airees/packages/core/tests/test_gateway_server.py
git commit -m "feat: add Gateway server for message routing"
```

---

### Task 9: Wire Gateway into Bootstrap and CLI

**Files:**
- Modify: `airees/cli/bootstrap.py`
- Modify: `airees/cli/main.py`
- Test: `tests/test_gateway_bootstrap.py`

**Step 1: Write the failing tests**

```python
"""Tests for gateway bootstrap and CLI chat command."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from airees.cli.bootstrap import bootstrap_gateway


@pytest.mark.asyncio
async def test_bootstrap_gateway_creates_components(tmp_path):
    """bootstrap_gateway should create Gateway with ConversationManager."""
    config_path = tmp_path / "airees.yaml"
    config_path.write_text(
        "name: test\nbrain_model: anthropic/claude-haiku-4-5\ndata_dir: data\n",
        encoding="utf-8",
    )

    with patch("airees.cli.bootstrap.ModelRouter") as MockRouter:
        MockRouter.return_value = MagicMock()
        with patch("airees.cli.bootstrap.GoalStore") as MockStore:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            MockStore.return_value = mock_store

            gateway = await bootstrap_gateway(config_path)

    assert gateway is not None
    assert gateway.conversation_manager is not None


@pytest.mark.asyncio
async def test_bootstrap_gateway_registers_cli_adapter(tmp_path):
    """bootstrap_gateway should register the CLI adapter by default."""
    config_path = tmp_path / "airees.yaml"
    config_path.write_text(
        "name: test\nbrain_model: anthropic/claude-haiku-4-5\ndata_dir: data\n",
        encoding="utf-8",
    )

    with patch("airees.cli.bootstrap.ModelRouter") as MockRouter:
        MockRouter.return_value = MagicMock()
        with patch("airees.cli.bootstrap.GoalStore") as MockStore:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            MockStore.return_value = mock_store

            gateway = await bootstrap_gateway(config_path)

    assert "cli" in gateway.adapters.channels
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_bootstrap.py -v`
Expected: FAIL with `ImportError: cannot import name 'bootstrap_gateway'`

**Step 3: Write implementation**

Add to `airees/cli/bootstrap.py` (after existing `bootstrap_from_config` function):

```python
async def bootstrap_gateway(
    config_path: Path,
) -> "Gateway":
    """Create Gateway with ConversationManager from airees.yaml.

    Creates:
    1. All core components via bootstrap_from_config
    2. ConversationManager with router, event_bus, soul, user context
    3. Gateway with CLIAdapter registered
    """
    from airees.gateway.adapters.cli_adapter import CLIAdapter
    from airees.gateway.conversation import ConversationManager
    from airees.gateway.server import Gateway

    orch, heartbeat = await bootstrap_from_config(config_path)
    cfg = load_airees_config(config_path)
    data_dir = Path(cfg.get("data_dir", _DEFAULTS["data_dir"]))

    manager = ConversationManager(
        router=orch.router,
        event_bus=orch.event_bus,
        soul_path=data_dir / "SOUL.md",
        user_path=data_dir / "USER.md",
        orchestrator=orch,
    )

    gateway = Gateway(conversation_manager=manager)
    gateway.adapters.register(CLIAdapter())

    return gateway
```

Add to `airees/cli/main.py` — new `chat` command (add after the `logs` command, before `if __name__`):

```python
@app.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    default="airees.yaml",
    help="Path to config file",
)
def chat(config_path: str) -> None:
    """Start an interactive chat session."""
    import asyncio

    from airees.cli.bootstrap import bootstrap_gateway

    async def _chat() -> None:
        click.echo("Bootstrapping Airees...")
        gateway = await bootstrap_gateway(Path(config_path))
        click.echo("Airees is ready. Type your message (exit/quit to stop).\n")

        cli_adapter = gateway.adapters.get("cli")
        if cli_adapter is None:
            click.echo("Error: CLI adapter not found.")
            return

        await gateway.start()
        try:
            await cli_adapter.run_interactive()
        finally:
            await gateway.stop()

    try:
        asyncio.run(_chat())
    except KeyboardInterrupt:
        click.echo("\nChat ended.")
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_bootstrap.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/cli/bootstrap.py airees/packages/core/airees/cli/main.py airees/packages/core/tests/test_gateway_bootstrap.py
git commit -m "feat: wire gateway into bootstrap and add CLI chat command"
```

---

### Task 10: Update Package Exports and Dependencies

**Files:**
- Modify: `airees/__init__.py`
- Modify: `pyproject.toml`
- Test: `tests/test_gateway_exports.py`

**Step 1: Write the failing tests**

```python
"""Tests for gateway exports from airees package."""


def test_gateway_types_exported():
    """Gateway message types should be importable from airees."""
    from airees import InboundMessage, OutboundMessage, Attachment
    assert InboundMessage is not None
    assert OutboundMessage is not None
    assert Attachment is not None


def test_gateway_components_exported():
    """Gateway components should be importable from airees."""
    from airees import Gateway, ConversationManager, AdapterRegistry
    assert Gateway is not None
    assert ConversationManager is not None
    assert AdapterRegistry is not None


def test_complexity_exported():
    """Complexity classifier should be importable from airees."""
    from airees import Complexity, classify_complexity
    assert Complexity is not None
    assert classify_complexity is not None


def test_session_exported():
    """Session components should be importable from airees."""
    from airees import Session, SessionStore
    assert Session is not None
    assert SessionStore is not None


def test_personal_context_exported():
    """PersonalContext should be importable from airees."""
    from airees import PersonalContext, load_personal_context
    assert PersonalContext is not None
    assert load_personal_context is not None
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_exports.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write implementation**

Add to `airees/__init__.py` (add these import lines in the appropriate section):

```python
# Gateway
from airees.gateway.types import Attachment, InboundMessage, OutboundMessage
from airees.gateway.adapter import AdapterRegistry
from airees.gateway.complexity import Complexity, classify_complexity
from airees.gateway.conversation import ConversationManager
from airees.gateway.personal_context import PersonalContext, load_personal_context
from airees.gateway.server import Gateway
from airees.gateway.session import Session, SessionStore
```

Add these to the `__all__` list (or add to existing exports).

Update `pyproject.toml` dependencies — add:

```toml
[project.optional-dependencies]
gateway = ["starlette>=0.40.0", "uvicorn>=0.30.0"]
telegram = ["python-telegram-bot>=21.0"]
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_exports.py -v`
Expected: 5 PASSED

**Step 5: Verify all existing tests still pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest --tb=short -q`
Expected: All 342+ tests PASSED

**Step 6: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/__init__.py airees/packages/core/pyproject.toml airees/packages/core/tests/test_gateway_exports.py
git commit -m "feat: export gateway components and add optional dependencies"
```

---

### Task 11: Telegram Channel Adapter

**Files:**
- Create: `airees/gateway/adapters/telegram_adapter.py`
- Test: `tests/test_telegram_adapter.py`

**Step 1: Write the failing tests**

```python
"""Tests for Telegram channel adapter."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from airees.gateway.adapters.telegram_adapter import TelegramAdapter
from airees.gateway.types import InboundMessage, OutboundMessage


def test_telegram_adapter_name():
    """TelegramAdapter should have name 'telegram'."""
    adapter = TelegramAdapter(bot_token="fake-token")
    assert adapter.name == "telegram"


def test_telegram_adapter_requires_token():
    """TelegramAdapter should store the bot token."""
    adapter = TelegramAdapter(bot_token="123:ABC")
    assert adapter.bot_token == "123:ABC"


@pytest.mark.asyncio
async def test_telegram_adapter_build_inbound():
    """_build_inbound should convert telegram Update to InboundMessage."""
    adapter = TelegramAdapter(bot_token="fake")

    # Simulate a telegram Update.message
    mock_message = MagicMock()
    mock_message.text = "hello from telegram"
    mock_message.chat_id = 12345
    mock_message.from_user.id = 67890
    mock_message.message_id = 1
    mock_message.date.timestamp.return_value = 1000.0

    msg = adapter._build_inbound(mock_message)
    assert isinstance(msg, InboundMessage)
    assert msg.channel == "telegram"
    assert msg.text == "hello from telegram"
    assert msg.sender_id == "67890"


@pytest.mark.asyncio
async def test_telegram_adapter_send():
    """send() should call bot.send_message with correct chat_id and text."""
    adapter = TelegramAdapter(bot_token="fake")
    mock_bot = AsyncMock()
    adapter._bot = mock_bot

    msg = OutboundMessage(
        channel="telegram",
        recipient_id="12345",
        text="Hello from Airees!",
    )
    await adapter.send(msg)

    mock_bot.send_message.assert_called_once_with(
        chat_id=12345,
        text="Hello from Airees!",
    )


def test_telegram_adapter_set_message_handler():
    """set_message_handler should store the callback."""
    adapter = TelegramAdapter(bot_token="fake")
    handler = AsyncMock()
    adapter.set_message_handler(handler)
    assert adapter._handler is handler
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_telegram_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `airees/gateway/adapters/telegram_adapter.py`:
```python
"""Telegram channel adapter using python-telegram-bot."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from airees.gateway.adapter import MessageHandler
from airees.gateway.types import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


@dataclass
class TelegramAdapter:
    """Channel adapter for Telegram using python-telegram-bot library.

    Requires python-telegram-bot >= 21.0 (install with `pip install airees[telegram]`).
    Set bot_token from @BotFather on Telegram.
    """

    bot_token: str
    name: str = "telegram"
    allowed_user_ids: tuple[int, ...] = ()  # Empty = allow all (for personal use)
    _handler: MessageHandler | None = field(default=None, init=False, repr=False)
    _bot: Any = field(default=None, init=False, repr=False)
    _app: Any = field(default=None, init=False, repr=False)

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Register the callback for incoming messages."""
        self._handler = handler

    async def start(self) -> None:
        """Start the Telegram bot with polling."""
        try:
            from telegram import Bot
            from telegram.ext import ApplicationBuilder, MessageHandler as TgHandler, filters
        except ImportError:
            raise ImportError(
                "python-telegram-bot is required for Telegram adapter. "
                "Install with: pip install airees[telegram]"
            )

        self._bot = Bot(token=self.bot_token)
        self._app = (
            ApplicationBuilder()
            .token(self.bot_token)
            .build()
        )

        # Register handler for text messages
        self._app.add_handler(TgHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
        logger.info("Starting Telegram adapter (polling mode)")
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            logger.info("Telegram adapter stopped")

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to a Telegram chat."""
        if self._bot is None:
            raise RuntimeError("Telegram bot not initialized — call start() first")
        await self._bot.send_message(
            chat_id=int(message.recipient_id),
            text=message.text,
        )

    async def _on_message(self, update: Any, context: Any) -> None:
        """Handle incoming Telegram message."""
        if update.message is None or update.message.text is None:
            return

        # Optional: filter by allowed user IDs
        if self.allowed_user_ids:
            user_id = update.message.from_user.id
            if user_id not in self.allowed_user_ids:
                logger.warning("Ignoring message from unauthorized user: %s", user_id)
                return

        inbound = self._build_inbound(update.message)
        if self._handler:
            await self._handler(inbound)

    def _build_inbound(self, message: Any) -> InboundMessage:
        """Convert a telegram Message object to InboundMessage."""
        return InboundMessage(
            channel="telegram",
            sender_id=str(message.from_user.id),
            text=message.text or "",
            timestamp=message.date.timestamp() if message.date else 0.0,
            metadata={
                "chat_id": message.chat_id,
                "message_id": message.message_id,
            },
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_telegram_adapter.py -v`
Expected: 5 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/adapters/telegram_adapter.py airees/packages/core/tests/test_telegram_adapter.py
git commit -m "feat: add Telegram channel adapter with user filtering"
```

---

## Layer 4: Integration & E2E (Tasks 12-14)

### Task 12: Cost Tracker

**Files:**
- Create: `airees/gateway/cost_tracker.py`
- Test: `tests/test_cost_tracker.py`

**Step 1: Write the failing tests**

```python
"""Tests for cost tracking."""
import pytest

from airees.gateway.cost_tracker import CostTracker, ModelCost


def test_model_cost_defaults():
    """ModelCost should have sensible defaults for Claude models."""
    costs = ModelCost.defaults()
    assert "haiku" in costs
    assert "sonnet" in costs
    assert "opus" in costs


def test_cost_tracker_record_and_total():
    """CostTracker should accumulate costs per model."""
    tracker = CostTracker()
    tracker.record(model="haiku", input_tokens=1000, output_tokens=500)
    tracker.record(model="haiku", input_tokens=2000, output_tokens=1000)

    total = tracker.total_cost
    assert total > 0


def test_cost_tracker_per_model_breakdown():
    """CostTracker should report costs per model."""
    tracker = CostTracker()
    tracker.record(model="haiku", input_tokens=1000, output_tokens=500)
    tracker.record(model="sonnet", input_tokens=1000, output_tokens=500)

    breakdown = tracker.breakdown()
    assert "haiku" in breakdown
    assert "sonnet" in breakdown
    assert breakdown["haiku"] < breakdown["sonnet"]


def test_cost_tracker_per_channel():
    """CostTracker should report costs per channel."""
    tracker = CostTracker()
    tracker.record(model="haiku", input_tokens=1000, output_tokens=500, channel="cli")
    tracker.record(model="haiku", input_tokens=1000, output_tokens=500, channel="telegram")

    by_channel = tracker.by_channel()
    assert "cli" in by_channel
    assert "telegram" in by_channel


def test_cost_tracker_reset():
    """reset() should clear all accumulated costs."""
    tracker = CostTracker()
    tracker.record(model="haiku", input_tokens=1000, output_tokens=500)
    tracker.reset()
    assert tracker.total_cost == 0.0


def test_cost_tracker_turn_count():
    """CostTracker should count total turns."""
    tracker = CostTracker()
    tracker.record(model="haiku", input_tokens=100, output_tokens=50)
    tracker.record(model="sonnet", input_tokens=100, output_tokens=50)
    assert tracker.total_turns == 2
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_cost_tracker.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `airees/gateway/cost_tracker.py`:
```python
"""Cost tracker — accumulates token usage and costs per model and channel."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelCost:
    """Cost per million tokens for a model tier."""

    input_per_mtok: float
    output_per_mtok: float

    @staticmethod
    def defaults() -> dict[str, "ModelCost"]:
        """Default costs for Claude model tiers (March 2026 pricing)."""
        return {
            "haiku": ModelCost(input_per_mtok=1.0, output_per_mtok=5.0),
            "sonnet": ModelCost(input_per_mtok=3.0, output_per_mtok=15.0),
            "opus": ModelCost(input_per_mtok=5.0, output_per_mtok=25.0),
        }


@dataclass
class _TurnRecord:
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    channel: str


@dataclass
class CostTracker:
    """Accumulates cost data across turns, models, and channels."""

    _records: list[_TurnRecord] = field(default_factory=list)
    _costs: dict[str, ModelCost] = field(default_factory=ModelCost.defaults)

    def record(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        channel: str = "unknown",
    ) -> float:
        """Record a single LLM call. Returns the cost of this call."""
        model_key = self._resolve_model_key(model)
        pricing = self._costs.get(model_key, self._costs["sonnet"])
        cost = (
            (input_tokens / 1_000_000) * pricing.input_per_mtok
            + (output_tokens / 1_000_000) * pricing.output_per_mtok
        )
        self._records.append(
            _TurnRecord(
                model=model_key,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                channel=channel,
            )
        )
        return cost

    @property
    def total_cost(self) -> float:
        """Total accumulated cost across all turns."""
        return sum(r.cost for r in self._records)

    @property
    def total_turns(self) -> int:
        """Total number of recorded turns."""
        return len(self._records)

    def breakdown(self) -> dict[str, float]:
        """Cost breakdown by model tier."""
        result: dict[str, float] = {}
        for r in self._records:
            result[r.model] = result.get(r.model, 0.0) + r.cost
        return result

    def by_channel(self) -> dict[str, float]:
        """Cost breakdown by channel."""
        result: dict[str, float] = {}
        for r in self._records:
            result[r.channel] = result.get(r.channel, 0.0) + r.cost
        return result

    def reset(self) -> None:
        """Clear all recorded costs."""
        self._records.clear()

    def _resolve_model_key(self, model: str) -> str:
        """Map model ID to pricing tier key."""
        lower = model.lower()
        if "haiku" in lower:
            return "haiku"
        if "opus" in lower:
            return "opus"
        return "sonnet"
```

**Step 4: Run tests to verify they pass**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_cost_tracker.py -v`
Expected: 6 PASSED

**Step 5: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/airees/gateway/cost_tracker.py airees/packages/core/tests/test_cost_tracker.py
git commit -m "feat: add cost tracker with per-model and per-channel breakdown"
```

---

### Task 13: End-to-End Integration Test

**Files:**
- Create: `tests/test_gateway_e2e.py`

**Step 1: Write the e2e test**

```python
"""End-to-end test: CLI message -> Gateway -> ConversationManager -> response."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from airees.gateway.adapters.cli_adapter import CLIAdapter
from airees.gateway.conversation import ConversationManager
from airees.gateway.server import Gateway
from airees.gateway.types import InboundMessage, OutboundMessage


@pytest.mark.asyncio
async def test_e2e_cli_message_flow(tmp_path):
    """Full flow: CLI message -> Gateway -> ConversationManager -> response sent back.

    Verifies:
    1. InboundMessage created from CLI input
    2. Gateway routes to ConversationManager
    3. ConversationManager classifies complexity (QUICK for "hello")
    4. Response sent back via CLIAdapter
    5. Session records the turn
    """
    # Setup: mock router that returns a fake LLM response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello! How can I help you today?")]
    mock_router = MagicMock()
    mock_router.create_message = AsyncMock(return_value=mock_response)

    # Create ConversationManager
    manager = ConversationManager(
        router=mock_router,
        event_bus=MagicMock(),
        soul_path=tmp_path / "SOUL.md",
        user_path=tmp_path / "USER.md",
    )

    # Create Gateway with CLI adapter
    gateway = Gateway(conversation_manager=manager)
    cli = CLIAdapter()
    gateway.adapters.register(cli)

    # Wire handler (normally done by gateway.start())
    cli.set_message_handler(gateway.handle_message)

    # Simulate a user message
    msg = InboundMessage(channel="cli", sender_id="local", text="hello")
    response = await gateway.handle_message(msg)

    # Verify response
    assert isinstance(response, OutboundMessage)
    assert response.channel == "cli"
    assert response.recipient_id == "local"
    assert "Hello" in response.text

    # Verify session recorded the turn
    session = manager.sessions.get_or_create("cli", "local")
    assert len(session.messages) == 2
    assert session.messages[0]["content"] == "hello"

    # Verify router was called with Haiku (QUICK complexity)
    call_args = mock_router.create_message.call_args
    assert "haiku" in call_args.kwargs.get("model", "")


@pytest.mark.asyncio
async def test_e2e_multi_turn_context(tmp_path):
    """Multi-turn conversation maintains context across turns."""
    responses = iter([
        MagicMock(content=[MagicMock(text="Hello! I'm Airees.")]),
        MagicMock(content=[MagicMock(text="You asked me to say hello!")]),
    ])
    mock_router = MagicMock()
    mock_router.create_message = AsyncMock(side_effect=lambda **kw: next(responses))

    manager = ConversationManager(
        router=mock_router,
        event_bus=MagicMock(),
        soul_path=tmp_path / "SOUL.md",
        user_path=tmp_path / "USER.md",
    )

    gateway = Gateway(conversation_manager=manager)

    # Turn 1
    msg1 = InboundMessage(channel="cli", sender_id="local", text="hello")
    r1 = await gateway.handle_message(msg1)
    assert "Airees" in r1.text

    # Turn 2 — should include Turn 1 in context
    msg2 = InboundMessage(channel="cli", sender_id="local", text="what did I just say?")
    r2 = await gateway.handle_message(msg2)

    # Verify the second call included conversation history
    second_call = mock_router.create_message.call_args_list[1]
    messages = second_call.kwargs.get("messages", [])
    # Should have: prev user, prev assistant, current user = 3 messages
    assert len(messages) >= 3


@pytest.mark.asyncio
async def test_e2e_personal_context_loaded(tmp_path):
    """Personal context from USER.md should be included in system prompt."""
    user_md = tmp_path / "USER.md"
    user_md.write_text(
        "---\nname: Nathaniel\ntimezone: Europe/London\n---\nLikes Python.",
        encoding="utf-8",
    )

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hi Nathaniel!")]
    mock_router = MagicMock()
    mock_router.create_message = AsyncMock(return_value=mock_response)

    manager = ConversationManager(
        router=mock_router,
        event_bus=MagicMock(),
        soul_path=tmp_path / "SOUL.md",
        user_path=user_md,
    )

    gateway = Gateway(conversation_manager=manager)
    msg = InboundMessage(channel="cli", sender_id="local", text="hi")
    await gateway.handle_message(msg)

    # Verify system prompt includes personal context
    call_args = mock_router.create_message.call_args
    system = call_args.kwargs.get("system", "")
    assert "Nathaniel" in system
    assert "Europe/London" in system
```

**Step 2: Run e2e test**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest tests/test_gateway_e2e.py -v`
Expected: 3 PASSED

**Step 3: Run full test suite**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest --tb=short -q`
Expected: All tests PASSED (342 existing + ~60 new)

**Step 4: Commit**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add airees/packages/core/tests/test_gateway_e2e.py
git commit -m "test: add end-to-end gateway integration tests"
```

---

### Task 14: Final Verification and Export Cleanup

**Step 1: Run full test suite**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m pytest --tb=short -q`
Expected: All tests PASSED

**Step 2: Verify all imports work**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -c "from airees import Gateway, ConversationManager, InboundMessage, OutboundMessage, Attachment, CLIAdapter, Complexity, Session, SessionStore, PersonalContext, CostTracker; print('All Phase 6 exports OK')"` (Note: CLIAdapter and CostTracker may need explicit export — add if missing)

**Step 3: Verify CLI chat command registered**

Run: `cd C:/Users/Nathaniel/Documents/Airees/training/airees/packages/core && python -m airees.cli.main --help`
Expected: Should show `chat` command in list

**Step 4: Final commit if any fixes needed**

```bash
cd C:/Users/Nathaniel/Documents/Airees/training
git add -A airees/packages/core/
git commit -m "fix: final Phase 6 export and wiring fixes"
```

---

## Summary

| Task | Component | Files | Tests |
|------|-----------|-------|-------|
| 1 | Message Types | gateway/types.py | 7 |
| 2 | Adapter Protocol + Registry | gateway/adapter.py | 6 |
| 3 | CLI Adapter | gateway/adapters/cli_adapter.py | 6 |
| 4 | Complexity Classifier | gateway/complexity.py | 7 |
| 5 | Session Manager | gateway/session.py | 8 |
| 6 | Personal Context | gateway/personal_context.py | 5 |
| 7 | ConversationManager | gateway/conversation.py | 5 |
| 8 | Gateway Server | gateway/server.py | 5 |
| 9 | Bootstrap + CLI Chat | cli/bootstrap.py, cli/main.py | 2 |
| 10 | Exports + Dependencies | __init__.py, pyproject.toml | 5 |
| 11 | Telegram Adapter | gateway/adapters/telegram_adapter.py | 5 |
| 12 | Cost Tracker | gateway/cost_tracker.py | 6 |
| 13 | E2E Integration | test_gateway_e2e.py | 3 |
| 14 | Final Verification | cleanup | - |
| **Total** | **14 tasks** | **~15 files** | **~70 tests** |
