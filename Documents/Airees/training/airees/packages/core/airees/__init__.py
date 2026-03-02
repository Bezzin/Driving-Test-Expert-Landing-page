"""Airees Core SDK - Multi-agent orchestration platform."""

__version__ = "0.1.0"

from airees.agent import Agent
from airees.brain.orchestrator import BrainOrchestrator
from airees.gateway.types import Attachment, InboundMessage, OutboundMessage
from airees.gateway.adapter import AdapterRegistry
from airees.gateway.complexity import Complexity, classify_complexity
from airees.gateway.conversation import ConversationManager
from airees.gateway.cost_tracker import CostTracker, ModelCost
from airees.gateway.learning import AutoSkillCapture
from airees.gateway.model_preference import ModelPreference
from airees.gateway.personal_context import PersonalContext, load_personal_context
from airees.gateway.server import Gateway
from airees.gateway.session import Session, SessionStore
from airees.brain.intent import GoalIntent, classify_intent, intent_to_prompt_hint
from airees.brain.prompt import build_brain_prompt
from airees.brain.state_machine import BrainState, BrainStateMachine
from airees.brain.tools import get_brain_tools
from airees.concurrency import ConcurrencyManager
from airees.context_budget import ContextBudget
from airees.context_compressor import ContextCompressor
from airees.coordinator.executor import Coordinator
from airees.coordinator.worker_builder import build_worker_prompt, get_tools_for_role, select_model
from airees.corpus_search import CorpusDocument, CorpusResult, CorpusSearchEngine
from airees.db.schema import GoalStatus, GoalStore, TaskStatus
from airees.decision_doc import DecisionDocument, DecisionEntry
from airees.events import Event, EventBus, EventType
from airees.feedback import FeedbackConfig, FeedbackEntry, FeedbackLoop
from airees.goal_daemon import GoalDaemon
from airees.heartbeat import HeartbeatDaemon
from airees.mcp_client import MCPServerConfig, MCPToolProvider
from airees.quality_gate import GateAction, GateResult, QualityGate
from airees.router.fallback import FallbackRouter
from airees.runner import Runner, RunResult, TokenUsage
from airees.scheduler import Scheduler, SchedulerConfig
from airees.skill_store import SkillDocument, SkillResult, SkillStore
from airees.soul import Soul, load_soul
from airees.state import PhaseStatus, ProjectState, load_state, save_state
from airees.tools.registry import TrustLevel
from airees.validation import ValidationWarning, validate_pipeline
from airees.worker_pool import WorkerPool

__all__ = [
    "AdapterRegistry",
    "Agent",
    "Attachment",
    "AutoSkillCapture",
    "BrainOrchestrator",
    "BrainState",
    "BrainStateMachine",
    "Complexity",
    "ConcurrencyManager",
    "ContextBudget",
    "ContextCompressor",
    "ConversationManager",
    "CostTracker",
    "Coordinator",
    "CorpusDocument",
    "CorpusResult",
    "CorpusSearchEngine",
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
    "Gateway",
    "GoalDaemon",
    "GoalIntent",
    "GoalStatus",
    "GoalStore",
    "HeartbeatDaemon",
    "InboundMessage",
    "MCPServerConfig",
    "MCPToolProvider",
    "ModelCost",
    "ModelPreference",
    "OutboundMessage",
    "PersonalContext",
    "PhaseStatus",
    "ProjectState",
    "QualityGate",
    "Runner",
    "RunResult",
    "Scheduler",
    "SchedulerConfig",
    "Session",
    "SessionStore",
    "SkillDocument",
    "SkillResult",
    "SkillStore",
    "Soul",
    "TaskStatus",
    "TokenUsage",
    "TrustLevel",
    "ValidationWarning",
    "WorkerPool",
    "build_brain_prompt",
    "build_worker_prompt",
    "classify_complexity",
    "classify_intent",
    "get_brain_tools",
    "get_tools_for_role",
    "intent_to_prompt_hint",
    "load_personal_context",
    "load_soul",
    "load_state",
    "save_state",
    "select_model",
    "validate_pipeline",
]
