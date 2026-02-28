"""Integration test: full pipeline with quality gate, state, and decision doc."""
import pytest

from airees.agent import Agent
from airees.context_budget import ContextBudget
from airees.decision_doc import DecisionDocument, DecisionEntry
from airees.feedback import FeedbackEntry, FeedbackLoop
from airees.quality_gate import GateAction, QualityGate
from airees.router.types import ModelConfig
from airees.state import PhaseStatus, ProjectState
from airees.validation import validate_pipeline
from airees.orchestration.pipeline import Pipeline, PipelineStep


def test_full_workflow_types():
    """Verify all new types compose together correctly."""
    # 1. Create a project state
    state = ProjectState(
        project_id="app-001",
        name="Fitness Tracker",
        phases=["research", "build", "review", "deploy"],
    )
    assert state.current_phase == "research"

    # 2. Advance through research
    state = state.advance()
    assert state.current_phase == "build"

    # 3. Create agents with context budgets
    orchestrator = Agent(
        name="orchestrator",
        instructions="Route tasks",
        model=ModelConfig(model_id="claude-haiku-4-5"),
        context_budget=ContextBudget(max_tokens=200000, max_usage_percent=5.0),
    )
    assert orchestrator.context_budget.effective_max == 10000

    builder = Agent(
        name="builder",
        instructions="Build the app",
        model=ModelConfig(model_id="claude-opus-4-6"),
        description="builds code",
    )
    reviewer = Agent(
        name="reviewer",
        instructions="Review the code",
        model=ModelConfig(model_id="claude-sonnet-4-6"),
        description="reviews code",
    )

    # 4. Create pipeline with quality gate
    gate = QualityGate(
        name="code-review",
        min_score=8,
        max_retries=3,
        on_failure=GateAction.FLAG_HUMAN,
    )
    pipeline = Pipeline(name="build-pipeline", steps=[
        PipelineStep(agent=builder, task_template="Build {{feature}}"),
        PipelineStep(
            agent=reviewer,
            task_template="Score: {{previous_output}}",
            quality_gate=gate,
        ),
    ])

    # 5. Validate pipeline (should have no warnings — different models)
    warnings = validate_pipeline(pipeline)
    assert len(warnings) == 0

    # 6. Record a decision
    doc = DecisionDocument(project_id="app-001", title="Fitness Tracker")
    doc = doc.add_entry(DecisionEntry(
        phase="research",
        agent="researcher",
        decision="Target iOS fitness niche",
        reasoning="High demand, low competition",
        confidence=0.9,
    ))
    assert len(doc.entries) == 1
    assert "fitness" in doc.to_markdown().lower()

    # 7. Record feedback
    loop = FeedbackLoop()
    loop = loop.record(FeedbackEntry(
        run_id="run-001",
        agent_name="builder",
        outcome="success",
        score=9.0,
        lesson="Template approach worked well",
    ))
    memory = loop.to_memory_content("builder")
    assert "Template approach" in memory

    # 8. Fail a phase and check escalation
    state = state.fail_phase("Build error")
    state = state.fail_phase("Build error 2")
    state = state.fail_phase("Build error 3")
    assert state.needs_human("build") is True


def test_same_model_warning():
    """Cross-model validation catches same-model build+review."""
    same_model = ModelConfig(model_id="claude-opus-4-6")
    builder = Agent(
        name="builder", instructions="Build",
        model=same_model, description="builds code",
    )
    reviewer = Agent(
        name="reviewer", instructions="Review",
        model=same_model, description="reviews code",
    )
    pipeline = Pipeline(name="test", steps=[
        PipelineStep(agent=builder, task_template="Build"),
        PipelineStep(agent=reviewer, task_template="Review"),
    ])
    warnings = validate_pipeline(pipeline)
    assert len(warnings) == 1
    assert warnings[0].code == "SAME_MODEL_BUILD_REVIEW"
