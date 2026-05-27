from __future__ import annotations

from dataclasses import dataclass

from auto_research.memory import LongTermMemory, MemoryRecord, ShortTermMemory
from auto_research.planning import Plan, StepStatus
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
            "## Plan",
        ]
        for step in self.plan.steps:
            lines.append(f"- [{step.status.value}] {step.id}: {step.goal}")
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
        memories = self.long_term_memory.search(task)
        for memory in memories:
            self.short_term_memory.add(memory)

        plan = self.planner.create_plan(task, memories)
        steps_executed = 0
        for step in plan.steps:
            if steps_executed >= max_steps:
                break
            step.status = StepStatus.RUNNING
            observation = self.researcher.research(task, step, self.short_term_memory.recent(12))
            step.observation = observation
            step.status = StepStatus.COMPLETE
            record = MemoryRecord(
                kind="observation",
                content=observation,
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
