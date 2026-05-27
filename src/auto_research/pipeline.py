from __future__ import annotations

from dataclasses import dataclass

from auto_research.memory import LongTermMemory, MemoryRecord, MemoryQuery, MemoryScope, ShortTermMemory
from auto_research.planning import Plan, StepStatus, lint_plan
from auto_research.providers import (
    HeuristicPlanningProvider,
    HeuristicReflectionProvider,
    HeuristicResearchProvider,
    PlanningProvider,
    ReflectionProvider,
    ResearchProvider,
)
from auto_research.reflection import Reflection


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


class ResearchPipeline:
    def __init__(
        self,
        long_term_memory: LongTermMemory,
        short_term_memory: ShortTermMemory | None = None,
        planner: PlanningProvider | None = None,
        researcher: ResearchProvider | None = None,
        reflector: ReflectionProvider | None = None,
    ) -> None:
        self.long_term_memory = long_term_memory
        self.short_term_memory = short_term_memory or ShortTermMemory()
        self.planner = planner or HeuristicPlanningProvider()
        self.researcher = researcher or HeuristicResearchProvider()
        self.reflector = reflector or HeuristicReflectionProvider()

    def run(self, task: str, max_steps: int = 5, session_id: str | None = None) -> ResearchReport:
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
        steps_executed = 0
        while steps_executed < max_steps and not plan.is_complete():
            ready_steps = plan.ready_steps() or plan.pending_steps()
            if not ready_steps:
                break
            step = ready_steps[0]
            if steps_executed >= max_steps:
                break
            step.status = StepStatus.RUNNING
            observation = self.researcher.research(task, step, self.short_term_memory.recent(12))
            step.observation = observation
            step.status = StepStatus.COMPLETE
            record = MemoryRecord(
                kind="observation",
                content=observation,
                scope=MemoryScope.EPISODIC,
                importance=0.65 if step.id in {"strategy", "synthesis"} else 0.55,
                tags=("research", step.id),
                metadata={"task": task, "step_id": step.id, "session_id": session_id},
            )
            self.short_term_memory.add(record)
            self.long_term_memory.add(record)
            steps_executed += 1

            reflection = self.reflector.reflect(task, plan, self.short_term_memory.recent(20))
            reflection_record = MemoryRecord(
                kind="reflection",
                content=reflection.summary,
                scope=MemoryScope.REFLECTIVE,
                importance=0.7,
                confidence=reflection.confidence,
                tags=("reflection",),
                metadata={
                    "task": task,
                    "confidence": reflection.confidence,
                    "gaps": reflection.gaps,
                    "session_id": session_id,
                },
            )
            self.short_term_memory.add(reflection_record)
            self.long_term_memory.add(reflection_record)

            if not reflection.needs_more_work and plan.is_complete():
                break

        final_reflection = self.reflector.reflect(task, plan, self.short_term_memory.recent(20))
        observations = [
            record
            for record in self.short_term_memory.all()
            if record.kind == "observation" and record.metadata.get("task") == task
        ]
        return ResearchReport(
            task=task,
            plan=plan,
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
