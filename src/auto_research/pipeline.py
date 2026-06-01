from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auto_research.context import PromptAssembler
from auto_research.memory import LongTermMemory, MemoryRecord, MemoryQuery, MemoryScope, ShortTermMemory
from auto_research.planning import Plan, PlanStep, StepStatus, lint_plan
from auto_research.providers import (
    HeuristicPlanningProvider,
    HeuristicReflectionProvider,
    HeuristicResearchProvider,
    PlanningProvider,
    ReflectionProvider,
    ResearchProvider,
)
from auto_research.reflection import Reflection
from auto_research.run_state import ResearchRunState, RunStatus
from auto_research.verifier import DeterministicVerifier


@dataclass(frozen=True)
class ResearchReport:
    task: str
    plan: Plan
    reflection: Reflection
    observations: list[MemoryRecord]

    def to_markdown(self) -> str:
        lines = [
            f"# Research Report",
            "",
            f"## Task",
            self.task,
            "",
            f"## Plan ({self.plan.shape.value})",
        ]
        for step in self.plan.steps:
            dependencies = self.plan.dependencies_for(step.id)
            suffix = f" depends_on={','.join(dependencies)}" if dependencies else ""
            lines.append(f"- [{step.status.value}] {step.id}: {step.goal}{suffix}")
        lines.extend(["", "## Observations"])
        for record in self.observations:
            lines.append(f"- {record.content}")
        lines.extend(
            [
                "",
                "## Reflection",
                self.reflection.summary,
                f"Confidence: {self.reflection.confidence:.2f}",
            ]
        )
        if self.reflection.gaps:
            lines.extend(["", "## Gaps", *[f"- {gap}" for gap in self.reflection.gaps]])
        if self.reflection.next_actions:
            lines.extend(
                ["", "## Next Actions", *[f"- {action}" for action in self.reflection.next_actions]]
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class AgentStepPrompt:
    run_id: str
    step_id: str
    prompt_path: Path | None
    content: str


class ResearchPipeline:
    def __init__(
        self,
        long_term_memory: LongTermMemory,
        short_term_memory: ShortTermMemory | None = None,
        planner: PlanningProvider | None = None,
        researcher: ResearchProvider | None = None,
        reflector: ReflectionProvider | None = None,
        prompt_assembler: PromptAssembler | None = None,
        verifier: DeterministicVerifier | None = None,
        prompt_dir: str | Path | None = None,
    ) -> None:
        self.long_term_memory = long_term_memory
        self.short_term_memory = short_term_memory or ShortTermMemory()
        self.planner = planner or HeuristicPlanningProvider()
        self.researcher = researcher or HeuristicResearchProvider()
        self.reflector = reflector or HeuristicReflectionProvider()
        self.prompt_assembler = prompt_assembler or PromptAssembler()
        self.verifier = verifier or DeterministicVerifier()
        self.prompt_dir = Path(prompt_dir) if prompt_dir else None

    def run(self, task: str, max_steps: int = 5, session_id: str | None = None) -> ResearchReport:
        state = self.start(task, max_steps=max_steps, session_id=session_id)
        while state.status is RunStatus.ACTIVE:
            state = self.step(state)
        return self.report_from_state(state)

    def start(
        self,
        task: str,
        max_steps: int = 5,
        session_id: str | None = None,
    ) -> ResearchRunState:
        memories = self._retrieve_starting_memories(task)
        for memory in memories:
            self.short_term_memory.focus(memory)

        plan = self.planner.create_plan(task, memories)
        for issue in lint_plan(plan):
            issue_record = MemoryRecord(
                kind="plan_issue",
                content=f"{issue.severity}: {issue.message}",
                scope=MemoryScope.REFLECTIVE,
                importance=0.8 if issue.severity == "error" else 0.6,
                tags=("planning", "lint"),
                metadata={"task": task, "step_id": issue.step_id, "session_id": session_id},
            )
            self.short_term_memory.add(issue_record)
            self.long_term_memory.add(issue_record)
        state = ResearchRunState(
            task=task,
            plan=plan,
            session_id=session_id,
            max_steps=max_steps,
            status=RunStatus.COMPLETE if plan.is_complete() else RunStatus.ACTIVE,
        )
        state.add_event("started", "Created initial research plan.")
        return state

    def step(self, state: ResearchRunState) -> ResearchRunState:
        agent_prompt = self.prepare_agent_step(state)
        if agent_prompt is None:
            return state
        step = self._step_by_id(state, agent_prompt.step_id)
        if step is None:
            state.status = RunStatus.FAILED
            state.last_error = f"Prepared unknown step {agent_prompt.step_id}"
            return state
        try:
            observation = self.researcher.research(
                state.task,
                step,
                self.short_term_memory.recent(12),
            )
        except Exception as exc:
            step.status = StepStatus.PENDING
            state.retry_count += 1
            state.status = RunStatus.FAILED
            state.last_error = str(exc)
            state.add_event(
                "failed",
                f"Step {step.id} failed: {exc}",
                step_id=step.id,
                metadata={"retry_count": state.retry_count, "max_retries": state.max_retries},
            )
            return state
        return self.complete_agent_step(state, step.id, observation)

    def prepare_agent_step(self, state: ResearchRunState) -> AgentStepPrompt | None:
        if state.status is not RunStatus.ACTIVE:
            return None
        if state.steps_executed >= state.max_steps:
            state.status = RunStatus.WAITING
            state.add_event("budget", "Step budget reached; waiting for review or a larger budget.")
            return None
        if state.plan.is_complete():
            state.status = RunStatus.COMPLETE
            state.add_event("complete", "Plan is complete.")
            return None

        ready_steps = state.plan.ready_steps() or state.plan.pending_steps()
        if not ready_steps:
            state.status = RunStatus.WAITING
            state.add_event("waiting", "No dependency-ready step is available.")
            return None

        step = ready_steps[0]
        recalled = self.short_term_memory.focused() + self.short_term_memory.recent(8)
        assembled_context = self.prompt_assembler.assemble(state, step, recalled)
        prompt_path = self._write_prompt_artifact(state, step.id, assembled_context.content)
        state.add_event(
            "prompt_assembled",
            "Assembled deterministic model-view context.",
            step_id=step.id,
            metadata={
                "cache_key": assembled_context.cache_key,
                "fixed_layers": list(assembled_context.fixed_layers),
                "variable_layers": list(assembled_context.variable_layers),
                "prompt_path": str(prompt_path) if prompt_path else None,
            },
        )
        state.add_event("step_started", f"Started step {step.id}.", step_id=step.id)
        step.status = StepStatus.RUNNING
        return AgentStepPrompt(
            run_id=state.run_id,
            step_id=step.id,
            prompt_path=prompt_path,
            content=assembled_context.content,
        )

    def complete_agent_step(self, state: ResearchRunState, step_id: str, observation: str) -> ResearchRunState:
        step = self._step_by_id(state, step_id)
        if step is None:
            state.status = RunStatus.FAILED
            state.last_error = f"Unknown step: {step_id}"
            state.add_event("failed", state.last_error)
            return state
        step.observation = observation
        step.status = StepStatus.COMPLETE
        verification = self.verifier.verify_step(state, step, observation)
        verification_record = MemoryRecord(
            kind="verification",
            content=verification.summary(),
            scope=MemoryScope.REFLECTIVE,
            importance=0.7 if verification.passed else 0.9,
            confidence=1.0,
            tags=("verification", step.id),
            metadata={
                "task": state.task,
                "step_id": step.id,
                "session_id": state.session_id,
                "passed": verification.passed,
                "checks": [check.__dict__ for check in verification.checks],
            },
        )
        self.short_term_memory.add(verification_record)
        self.long_term_memory.add(verification_record)
        state.add_event(
            "verification_passed" if verification.passed else "verification_failed",
            verification.summary(),
            step_id=step.id,
        )
        if not verification.passed:
            state.status = RunStatus.WAITING
            state.add_event("waiting", "Verifier failed; waiting for plan or executor correction.", step_id=step.id)
            return state
        record = MemoryRecord(
            kind="observation",
            content=observation,
            scope=MemoryScope.EPISODIC,
            importance=0.65 if step.id in {"strategy", "synthesis"} else 0.55,
            tags=("research", step.id),
            metadata={"task": state.task, "step_id": step.id, "session_id": state.session_id},
        )
        self.short_term_memory.add(record)
        self.long_term_memory.add(record)
        state.steps_executed += 1
        state.retry_count = 0
        state.add_event("step_completed", f"Completed step {step.id}.", step_id=step.id)

        reflection = self.reflector.reflect(state.task, state.plan, self.short_term_memory.recent(20))
        reflection_record = MemoryRecord(
            kind="reflection",
            content=reflection.summary,
            scope=MemoryScope.REFLECTIVE,
            importance=0.7,
            confidence=reflection.confidence,
            tags=("reflection",),
            metadata={
                "task": state.task,
                "confidence": reflection.confidence,
                "gaps": reflection.gaps,
                "session_id": state.session_id,
            },
        )
        self.short_term_memory.add(reflection_record)
        self.long_term_memory.add(reflection_record)
        state.add_event(
            "reflection",
            reflection.summary,
            metadata={"confidence": reflection.confidence, "gaps": reflection.gaps},
        )

        if state.plan.is_complete() and not reflection.needs_more_work:
            state.status = RunStatus.COMPLETE
            state.add_event("complete", "Plan completed with sufficient reflection confidence.")
        elif state.steps_executed >= state.max_steps:
            state.status = RunStatus.WAITING
            state.add_event("budget", "Step budget reached after this step.")
        return state

    def _step_by_id(self, state: ResearchRunState, step_id: str) -> PlanStep | None:
        for step in state.plan.steps:
            if step.id == step_id:
                return step
        return None

    def _write_prompt_artifact(
        self,
        state: ResearchRunState,
        step_id: str,
        content: str,
    ) -> Path | None:
        if self.prompt_dir is None:
            return None
        target = self.prompt_dir / state.run_id / f"{state.steps_executed + 1:03d}-{step_id}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def report_from_state(self, state: ResearchRunState) -> ResearchReport:
        final_reflection = self.reflector.reflect(state.task, state.plan, self.short_term_memory.recent(20))
        observations = [
            record
            for record in self.short_term_memory.all()
            if record.kind == "observation" and record.metadata.get("task") == state.task
        ]
        if not observations:
            observations = [
                MemoryRecord(
                    kind="observation",
                    content=step.observation,
                    scope=MemoryScope.EPISODIC,
                    tags=("research", step.id),
                    metadata={"task": state.task, "step_id": step.id, "session_id": state.session_id},
                )
                for step in state.plan.steps
                if step.observation
            ]
        return ResearchReport(
            task=state.task,
            plan=state.plan,
            reflection=final_reflection,
            observations=observations,
        )

    def _retrieve_starting_memories(self, task: str) -> list[MemoryRecord]:
        query = MemoryQuery(
            text=task,
            scopes=(MemoryScope.SEMANTIC, MemoryScope.PROCEDURAL, MemoryScope.REFLECTIVE),
            limit=10,
            importance_weight=0.35,
            diversity_weight=0.25,
        )
        scoped = [result.record for result in self.long_term_memory.retrieve(query)]
        if scoped:
            return scoped
        return self.long_term_memory.search(task)
