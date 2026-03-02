"""Auto-skill capture — learn from successful goal executions."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from airees.skill_store import SkillStore

log = logging.getLogger(__name__)

# BM25 with small corpora (single document) produces negative IDF, so
# SkillStore clamps scores to 0.001.  Any result returned from search()
# already passed a token-overlap filter, meaning it is a genuine match.
# A threshold of 0.0 therefore treats every returned result as a duplicate.
_DUPLICATE_THRESHOLD = 0.0


@dataclass
class AutoSkillCapture:
    """Captures successful goal patterns as reusable skills."""

    skill_store: SkillStore

    def maybe_create_skill(
        self,
        *,
        goal_text: str,
        result_text: str,
        success: bool,
    ) -> bool:
        """Create a skill if the goal was novel and successful.

        Returns True if a skill was created or updated, False otherwise.
        """
        if not success:
            log.debug("Skipping skill capture for failed goal")
            return False

        # Check if a skill already matches
        existing = self.skill_store.search(goal_text, top_k=1)
        if existing and existing[0].score >= _DUPLICATE_THRESHOLD:
            # Update existing skill's success rate
            try:
                self.skill_store.update_skill(
                    name=existing[0].name,
                    success=True,
                )
                log.info("Updated existing skill: %s", existing[0].name)
            except FileNotFoundError:
                pass
            return True

        # Create a new skill
        name = _slugify(goal_text)
        triggers = [goal_text.lower().strip()]
        self.skill_store.create_skill(
            name=name,
            description=goal_text[:200],
            triggers=triggers,
            task_graph=f"Goal: {goal_text}\nResult: {result_text[:500]}",
        )
        log.info("Created new skill: %s", name)
        return True


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower().strip())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:60]
