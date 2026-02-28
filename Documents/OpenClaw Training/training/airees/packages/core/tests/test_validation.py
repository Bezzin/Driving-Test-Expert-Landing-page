"""Tests for pipeline validation rules."""
import pytest

from airees.agent import Agent
from airees.orchestration.pipeline import Pipeline, PipelineStep
from airees.router.types import ModelConfig
from airees.validation import validate_pipeline, ValidationWarning


def test_no_warnings_different_models():
    builder = Agent(
        name="builder",
        instructions="Build",
        model=ModelConfig(model_id="claude-opus-4-6"),
        description="builds code",
    )
    reviewer = Agent(
        name="reviewer",
        instructions="Review",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        description="reviews code",
    )
    pipeline = Pipeline(name="test", steps=[
        PipelineStep(agent=builder, task_template="Build"),
        PipelineStep(agent=reviewer, task_template="Review"),
    ])
    warnings = validate_pipeline(pipeline)
    assert len(warnings) == 0


def test_warns_same_model_build_review():
    builder = Agent(
        name="builder",
        instructions="Build",
        model=ModelConfig(model_id="claude-opus-4-6"),
        description="builds code",
    )
    reviewer = Agent(
        name="reviewer",
        instructions="Review",
        model=ModelConfig(model_id="claude-opus-4-6"),
        description="reviews code",
    )
    pipeline = Pipeline(name="test", steps=[
        PipelineStep(agent=builder, task_template="Build"),
        PipelineStep(agent=reviewer, task_template="Review"),
    ])
    warnings = validate_pipeline(pipeline)
    assert len(warnings) == 1
    assert warnings[0].code == "SAME_MODEL_BUILD_REVIEW"


def test_no_warning_when_no_review_step():
    agent_a = Agent(
        name="fetcher",
        instructions="Fetch",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    agent_b = Agent(
        name="writer",
        instructions="Write",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
    )
    pipeline = Pipeline(name="test", steps=[
        PipelineStep(agent=agent_a, task_template="Fetch"),
        PipelineStep(agent=agent_b, task_template="Write"),
    ])
    warnings = validate_pipeline(pipeline)
    assert len(warnings) == 0
