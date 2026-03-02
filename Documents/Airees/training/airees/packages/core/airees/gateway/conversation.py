"""ConversationManager — central gateway orchestrator.

Receives :class:`InboundMessage` instances from channel adapters, classifies
complexity, routes to either the quick (router) or orchestrated path, and
returns an :class:`OutboundMessage`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from airees.gateway.complexity import Complexity, classify_complexity
from airees.gateway.cost_tracker import CostTracker
from airees.gateway.personal_context import PersonalContext, load_personal_context
from airees.gateway.session import SessionStore
from airees.gateway.types import InboundMessage, OutboundMessage
from airees.skill_store import SkillStore
from airees.soul import Soul, load_soul

log = logging.getLogger(__name__)

_MODEL_MAP: dict[str, str] = {
    "haiku": "anthropic/claude-haiku-4-5",
    "sonnet": "anthropic/claude-sonnet-4-5",
    "opus": "anthropic/claude-opus-4-5",
}

_SKILL_CONFIDENCE_THRESHOLD = 0.001


@dataclass
class ConversationManager:
    """Orchestrates the full request lifecycle for a single message.

    Attributes:
        router: Model router with a ``create_message`` async method.
        event_bus: Optional event bus for emitting gateway events.
        soul_path: Path to SOUL.md identity file.
        user_path: Path to USER.md personal context file.
        orchestrator: Optional orchestrator for complex multi-step goals.
        sessions: In-memory session store.
        max_context_turns: Maximum conversation turns to include as context.
    """

    router: Any
    event_bus: Any
    soul_path: Path
    user_path: Path
    orchestrator: Any = None
    sessions: SessionStore = field(default_factory=SessionStore)
    max_context_turns: int = 10
    cost_tracker: CostTracker | None = None
    skill_store: SkillStore | None = None

    # Lazy-loaded caches (not part of __init__)
    _soul: Soul | None = field(default=None, init=False, repr=False)
    _personal: PersonalContext | None = field(default=None, init=False, repr=False)

    def _get_soul(self) -> Soul:
        """Lazy-load the Soul identity."""
        if self._soul is None:
            self._soul = load_soul(self.soul_path)
            log.info("Soul loaded: %s", self._soul.name)
        return self._soul

    def _get_personal(self) -> PersonalContext:
        """Lazy-load the personal context."""
        if self._personal is None:
            self._personal = load_personal_context(self.user_path)
            log.info("Personal context loaded: %s", self._personal.name)
        return self._personal

    async def handle(self, message: InboundMessage) -> OutboundMessage:
        """Process an inbound message and produce an outbound reply.

        Steps:
        1. Get or create session
        2. Retrieve conversation context
        3. Load personal context
        4. Check skill store for a cached pattern
        5. If no skill match, classify complexity
        6. Route to skill, quick, or orchestrated path
        7. Record the turn
        8. Return the outbound message
        """
        session = self.sessions.get_or_create(message.channel, message.sender_id)
        context_messages = session.get_context_messages(self.max_context_turns)
        personal = self._get_personal()

        # Check skill store for a cached pattern
        skill_result = None
        if self.skill_store is not None:
            results = self.skill_store.search(message.text, top_k=1)
            if results and results[0].score >= _SKILL_CONFIDENCE_THRESHOLD:
                skill_result = results[0]
                log.info("Skill match: %s (score=%.2f)", skill_result.name, skill_result.score)

        if skill_result is not None:
            reply_text = await self._run_skill(
                message.text, context_messages, personal, skill_result,
                channel=message.channel,
            )
        else:
            complexity = await classify_complexity(message.text)
            log.info(
                "Handling message from %s:%s — complexity=%s",
                message.channel,
                message.sender_id,
                complexity.value,
            )

            if complexity is Complexity.COMPLEX and self.orchestrator is not None:
                reply_text = await self._run_orchestrated(
                    message.text, context_messages, personal
                )
            else:
                reply_text = await self._run_quick(
                    message.text, context_messages, personal,
                    complexity=complexity, channel=message.channel,
                )

        session.add_turn(user_text=message.text, assistant_text=reply_text)

        return OutboundMessage(
            channel=message.channel,
            recipient_id=message.sender_id,
            text=reply_text,
        )

    async def _run_quick(
        self,
        text: str,
        context_messages: list[dict[str, str]],
        personal: PersonalContext,
        *,
        complexity: Complexity = Complexity.QUICK,
        channel: str = "unknown",
    ) -> str:
        """Handle a quick/moderate message via the model router."""
        soul = self._get_soul()
        system_prompt = soul.to_prompt() + "\n\n" + personal.to_prompt()
        messages = [*context_messages, {"role": "user", "content": text}]
        model = _MODEL_MAP.get(complexity.model_hint, _MODEL_MAP["haiku"])

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
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    channel=channel,
                )

            return reply_text
        except Exception as exc:
            log.error("_run_quick failed: %s", exc, exc_info=True)
            return "I'm sorry, something went wrong. Please try again."

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

    async def _run_orchestrated(
        self,
        text: str,
        context_messages: list[dict[str, str]],
        personal: PersonalContext,
    ) -> str:
        """Handle a complex message via the full orchestrator pipeline."""
        try:
            goal_id = await self.orchestrator.submit_goal(text)
            result = await self.orchestrator.execute_goal(goal_id)
            return result
        except Exception as exc:
            log.error("_run_orchestrated failed: %s", exc, exc_info=True)
            return "I'm sorry, something went wrong processing your request. Please try again."
