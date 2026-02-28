"""Validation rules for pipelines and workflows."""
from __future__ import annotations

from dataclasses import dataclass

from airees.orchestration.pipeline import Pipeline

_BUILD_KEYWORDS = {"build", "coder", "builder", "implement", "develop"}
_REVIEW_KEYWORDS = {"review", "reviewer", "audit", "check", "verify", "score"}


@dataclass(frozen=True)
class ValidationWarning:
    code: str
    message: str
    severity: str = "warning"


def _is_role(agent_name: str, agent_desc: str, keywords: set[str]) -> bool:
    text = f"{agent_name} {agent_desc}".lower()
    return any(kw in text for kw in keywords)


def validate_pipeline(pipeline: Pipeline) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []
    builders = []
    reviewers = []
    for step in pipeline.steps:
        agent = step.agent
        if _is_role(agent.name, agent.description, _BUILD_KEYWORDS):
            builders.append(agent)
        elif _is_role(agent.name, agent.description, _REVIEW_KEYWORDS):
            reviewers.append(agent)
    for b in builders:
        for r in reviewers:
            if b.model.model_id == r.model.model_id:
                warnings.append(ValidationWarning(
                    code="SAME_MODEL_BUILD_REVIEW",
                    message=(
                        f"Builder '{b.name}' and reviewer '{r.name}' use the same model "
                        f"'{b.model.model_id}'. Cross-model review produces higher quality output."
                    ),
                ))
    return warnings
