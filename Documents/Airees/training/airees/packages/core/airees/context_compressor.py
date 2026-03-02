"""Progressive context compression for long-running goals.

4-stage cascade:
- Stage 0 (<60%): No compression
- Stage 1 (60-74%): Summarize completed assistant outputs via Haiku
- Stage 2 (75-84%): Collapse completed message pairs into one-liners
- Stage 3 (85-94%): Checkpoint — keep only recent messages
- Stage 4 (95%+): Emergency — keep only the last exchange
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from airees.context_budget import ContextBudget
from airees.router.types import ModelConfig


@dataclass
class ContextCompressor:
    router: Any
    budget: ContextBudget

    _THRESHOLDS = (60.0, 75.0, 85.0, 95.0)

    def detect_stage(self) -> int:
        pct = self.budget.usage_percent
        for i, threshold in enumerate(self._THRESHOLDS):
            if pct < threshold:
                return i
        return 4

    def update_budget(self, budget: ContextBudget) -> None:
        self.budget = budget

    async def compress(
        self, messages: list[dict[str, Any]], stage: int
    ) -> list[dict[str, Any]]:
        if stage == 0 or not messages:
            return list(messages)
        if stage >= 4:
            return self._emergency_trim(messages)
        if stage >= 3:
            return self._checkpoint_trim(messages)
        if stage >= 2:
            return self._collapse_pairs(messages)
        return await self._summarize_outputs(messages)

    async def _summarize_outputs(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            if msg.get("role") == "assistant" and isinstance(
                msg.get("content"), str
            ):
                content = msg["content"]
                if len(content) > 200:
                    summary = await self._haiku_summarize(content)
                    result.append(
                        {
                            "role": "assistant",
                            "content": f"[Summarized] {summary}",
                        }
                    )
                else:
                    result.append(msg)
            else:
                result.append(msg)
        return result

    def _collapse_pairs(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if len(messages) <= 4:
            return list(messages)
        collapsed: list[dict[str, Any]] = []
        earlier = messages[:-4]
        recent = messages[-4:]
        summaries = []
        for msg in earlier:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, str):
                preview = content[:80].replace("\n", " ")
            else:
                preview = str(content)[:80]
            summaries.append(f"[{role}] {preview}")
        if summaries:
            collapsed.append(
                {
                    "role": "user",
                    "content": "[Compressed earlier context]\n"
                    + "\n".join(summaries),
                }
            )
        collapsed.extend(recent)
        return collapsed

    def _checkpoint_trim(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if len(messages) <= 2:
            return list(messages)
        return list(messages[-2:])

    def _emergency_trim(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        last_user: tuple[int, dict] | None = None
        last_assistant: tuple[int, dict] | None = None
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if msg.get("role") == "user" and last_user is None:
                last_user = (i, msg)
            elif msg.get("role") == "assistant" and last_assistant is None:
                last_assistant = (i, msg)
            if last_user and last_assistant:
                break
        # Sort by original index to preserve chronological order
        found = [x for x in (last_user, last_assistant) if x is not None]
        found.sort(key=lambda x: x[0])
        result = [msg for _, msg in found]
        return result if result else list(messages[-1:])

    async def _haiku_summarize(self, text: str) -> str:
        model = ModelConfig(model_id="claude-haiku-4-5-20251001")
        response = await self.router.create_message(
            model=model,
            system="Summarize this text in exactly 2 lines. Preserve key facts and results.",
            messages=[{"role": "user", "content": text}],
        )
        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return text[:200]
