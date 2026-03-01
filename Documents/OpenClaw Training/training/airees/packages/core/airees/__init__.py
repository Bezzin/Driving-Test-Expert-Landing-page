"""Airees Core SDK - Multi-agent orchestration platform."""

__version__ = "0.1.0"

from airees.agent import Agent
from airees.context_budget import ContextBudget
from airees.decision_doc import DecisionDocument, DecisionEntry
from airees.events import Event, EventBus, EventType
from airees.feedback import FeedbackConfig, FeedbackEntry, FeedbackLoop
from airees.quality_gate import GateAction, GateResult, QualityGate
from airees.runner import Runner, RunResult, TokenUsage
from airees.scheduler import Scheduler, SchedulerConfig
from airees.state import PhaseStatus, ProjectState, load_state, save_state
from airees.validation import ValidationWarning, validate_pipeline

__all__ = [
    "Agent",
    "ContextBudget",
    "DecisionDocument",
    "DecisionEntry",
    "Event",
    "EventBus",
    "EventType",
    "FeedbackConfig",
    "FeedbackEntry",
    "FeedbackLoop",
    "GateAction",
    "GateResult",
    "load_state",
    "PhaseStatus",
    "ProjectState",
    "QualityGate",
    "Runner",
    "RunResult",
    "save_state",
    "Scheduler",
    "SchedulerConfig",
    "TokenUsage",
    "validate_pipeline",
    "ValidationWarning",
]
