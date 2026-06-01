"""Auto-research pipeline primitives for coding agents."""

from auto_research.change_eval import (
    ChangeComparison,
    CommandComparison,
    CommandResult,
    append_comparison_ledger,
    compare_command_results,
)
from auto_research.context import AssembledContext, OutputFormat, PromptAssembler, RoleProfile, TaskSpecification
from auto_research.human import HumanDecision, HumanReview, HumanReviewKind, HumanReviewStatus
from auto_research.memory import LongTermMemory, MemoryQuery, MemoryRecord, MemoryScope, ShortTermMemory
from auto_research.pipeline import AgentStepPrompt, ResearchPipeline, ResearchReport
from auto_research.planning import Plan, PlanIssue, PlanShape, PlanStep, lint_plan
from auto_research.reflection import Reflection
from auto_research.run_state import ResearchRunState, RunEvent, RunStatus, RunStore
from auto_research.scheduler import ScheduleExecution, ScheduleStore, ScheduledTask
from auto_research.verifier import DeterministicVerifier, VerificationCheck, VerificationReport
from auto_research.workbench import render_run_brief

__all__ = [
    "LongTermMemory",
    "ChangeComparison",
    "CommandComparison",
    "CommandResult",
    "HumanDecision",
    "HumanReview",
    "HumanReviewKind",
    "HumanReviewStatus",
    "MemoryQuery",
    "MemoryRecord",
    "MemoryScope",
    "Plan",
    "PlanIssue",
    "PlanShape",
    "PlanStep",
    "Reflection",
    "ResearchPipeline",
    "ResearchReport",
    "ResearchRunState",
    "RunEvent",
    "RunStatus",
    "RunStore",
    "ScheduleExecution",
    "ScheduleStore",
    "ScheduledTask",
    "ShortTermMemory",
    "AssembledContext",
    "AgentStepPrompt",
    "DeterministicVerifier",
    "OutputFormat",
    "PromptAssembler",
    "RoleProfile",
    "TaskSpecification",
    "VerificationCheck",
    "VerificationReport",
    "lint_plan",
    "render_run_brief",
    "append_comparison_ledger",
    "compare_command_results",
]
