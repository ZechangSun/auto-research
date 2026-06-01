from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from auto_research.memory import MemoryRecord
from auto_research.planning import PlanStep
from auto_research.run_state import ResearchRunState


@dataclass(frozen=True)
class RoleProfile:
    identity: str = "Auto-research coding-agent equipment"
    skills: tuple[str, ...] = (
        "classical memory retrieval",
        "dependency-aware planning",
        "stepwise execution",
        "reflection",
        "deterministic verification",
    )
    boundaries: tuple[str, ...] = (
        "Prefer repo evidence over speculation.",
        "Keep outputs concise and machine-readable enough to archive.",
        "Do not claim completion before verification.",
    )


@dataclass(frozen=True)
class TaskSpecification:
    goal: str
    allowed_tools: tuple[str, ...] = ("memory", "planner", "research_provider", "verifier")
    output_constraints: tuple[str, ...] = (
        "Return a focused observation for the current step.",
        "Name risks or uncertainty when evidence is weak.",
    )


@dataclass(frozen=True)
class OutputFormat:
    schema: str = "observation: str; risks: list[str]; next_hint: str"
    stop_conditions: tuple[str, ...] = (
        "Current step has a useful observation.",
        "Verifier can assess correctness, completeness, and integrity.",
    )


@dataclass(frozen=True)
class AssembledContext:
    content: str
    cache_key: str
    fixed_layers: tuple[str, ...]
    variable_layers: tuple[str, ...]

    def write_to(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.content, encoding="utf-8")
        return target


@dataclass(frozen=True)
class PromptAssembler:
    role_profile: RoleProfile = field(default_factory=RoleProfile)
    output_format: OutputFormat = field(default_factory=OutputFormat)

    def assemble(
        self,
        state: ResearchRunState,
        step: PlanStep,
        recalled_memories: list[MemoryRecord],
    ) -> AssembledContext:
        task_spec = TaskSpecification(goal=state.task)
        fixed_layers = (
            self._render_role_profile(),
            self._render_task_spec(task_spec),
            self._render_output_format(),
        )
        variable_layers = (
            self._render_reference_injection(step, recalled_memories),
            self._render_plan(state, step),
            self._render_memory_recall(recalled_memories),
            self._render_state_context(state),
        )
        content = "\n\n".join((*fixed_layers, "---", *variable_layers))
        cache_key = hashlib.sha256("\n\n".join(fixed_layers).encode("utf-8")).hexdigest()[:16]
        return AssembledContext(
            content=content,
            cache_key=cache_key,
            fixed_layers=("role_profile", "task_specification", "output_format"),
            variable_layers=("reference_injection", "plan", "memory_recall", "state_context"),
        )

    def _render_role_profile(self) -> str:
        return "\n".join(
            [
                "# Role Profile",
                f"Identity: {self.role_profile.identity}",
                "Skills:",
                *[f"- {skill}" for skill in self.role_profile.skills],
                "Boundaries:",
                *[f"- {boundary}" for boundary in self.role_profile.boundaries],
            ]
        )

    @staticmethod
    def _render_task_spec(task: TaskSpecification) -> str:
        return "\n".join(
            [
                "# Task Specification",
                f"Goal: {task.goal}",
                "Allowed tools:",
                *[f"- {tool}" for tool in task.allowed_tools],
                "Output constraints:",
                *[f"- {constraint}" for constraint in task.output_constraints],
            ]
        )

    def _render_output_format(self) -> str:
        return "\n".join(
            [
                "# Output Format",
                f"Schema: {self.output_format.schema}",
                "Stop conditions:",
                *[f"- {condition}" for condition in self.output_format.stop_conditions],
            ]
        )

    @staticmethod
    def _render_reference_injection(step: PlanStep, memories: list[MemoryRecord]) -> str:
        references = [
            record
            for record in memories
            if set(step.id.lower().split()).intersection(" ".join(record.tags).lower().split())
        ]
        if not references:
            references = memories[:3]
        return "\n".join(
            [
                "# Reference Injection",
                *[
                    f"- [{record.scope.value}/{record.kind}] {record.content}"
                    for record in references
                ],
            ]
        )

    @staticmethod
    def _render_plan(state: ResearchRunState, step: PlanStep) -> str:
        lines = ["# Plan", f"Shape: {state.plan.shape.value}", f"Current step: {step.id}"]
        for plan_step in state.plan.steps:
            dependencies = state.plan.dependencies_for(plan_step.id)
            suffix = f" depends_on={','.join(dependencies)}" if dependencies else ""
            marker = " ->" if plan_step.id == step.id else "  "
            lines.append(f"{marker} [{plan_step.status.value}] {plan_step.id}: {plan_step.goal}{suffix}")
        return "\n".join(lines)

    @staticmethod
    def _render_memory_recall(memories: list[MemoryRecord]) -> str:
        if not memories:
            return "# Memory Recall\n- None"
        return "\n".join(
            [
                "# Memory Recall",
                *[
                    f"- {record.id[:8]} [{record.scope.value}/{record.kind}] "
                    f"importance={record.importance:.2f}: {record.content}"
                    for record in memories
                ],
            ]
        )

    @staticmethod
    def _render_state_context(state: ResearchRunState) -> str:
        recent_events = state.events[-5:]
        return "\n".join(
            [
                "# State Context",
                f"Run: {state.run_id}",
                f"Status: {state.status.value}",
                f"Progress: {state.steps_executed}/{state.max_steps}",
                "Recent events:",
                *[
                    f"- {event.created_at} [{event.type}] {event.message}"
                    for event in recent_events
                ],
            ]
        )
