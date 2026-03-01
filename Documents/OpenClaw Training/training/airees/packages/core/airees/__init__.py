"""Airees Core SDK - Multi-agent orchestration platform."""

__version__ = "0.1.0"

from airees.agent import Agent
from airees.brain.orchestrator import BrainOrchestrator
from airees.brain.intent import GoalIntent, classify_intent, intent_to_prompt_hint
from airees.brain.prompt import build_brain_prompt
from airees.brain.state_machine import BrainState, BrainStateMachine
from airees.brain.tools import get_brain_tools
from airees.concurrency import ConcurrencyManager
from airees.context_budget import ContextBudget
from airees.coordinator.executor import Coordinator
from airees.coordinator.worker_builder import build_worker_prompt, get_tools_for_role, select_model
from airees.db.schema import GoalStatus, GoalStore, TaskStatus
from airees.decision_doc import DecisionDocument, DecisionEntry
from airees.events import Event, EventBus, EventType
from airees.feedback import FeedbackConfig, FeedbackEntry, FeedbackLoop
from airees.quality_gate import GateAction, GateResult, QualityGate
from airees.router.fallback import FallbackRouter
from airees.runner import Runner, RunResult, TokenUsage
from airees.scheduler import Scheduler, SchedulerConfig
from airees.soul import Soul, load_soul
from airees.state import PhaseStatus, ProjectState, load_state, save_state
from airees.validation import ValidationWarning, validate_pipeline
from airees.worker_pool import WorkerPool

__all__ = [
    "Agent",
    "BrainOrchestrator",
    "BrainState",
    "BrainStateMachine",
    "ConcurrencyManager",
    "ContextBudget",
    "Coordinator",
    "DecisionDocument",
    "DecisionEntry",
    "Event",
    "EventBus",
    "EventType",
    "FallbackRouter",
    "FeedbackConfig",
    "FeedbackEntry",
    "FeedbackLoop",
    "GateAction",
    "GateResult",
    "GoalIntent",
    "GoalStatus",
    "GoalStore",
    "PhaseStatus",
    "ProjectState",
    "QualityGate",
    "Runner",
    "RunResult",
    "Scheduler",
    "SchedulerConfig",
    "Soul",
    "TaskStatus",
    "TokenUsage",
    "ValidationWarning",
    "WorkerPool",
    "build_brain_prompt",
    "build_worker_prompt",
    "classify_intent",
    "get_brain_tools",
    "get_tools_for_role",
    "intent_to_prompt_hint",
    "load_soul",
    "load_state",
    "save_state",
    "select_model",
    "validate_pipeline",
]
