from __future__ import annotations

from typing import Protocol

from auto_research.memory import MemoryRecord
from auto_research.planning import Plan, PlanStep
from auto_research.reflection import Reflection


class PlanningProvider(Protocol):
    def create_plan(self, task: str, memories: list[MemoryRecord]) -> Plan:
        """Create a research plan."""


class ResearchProvider(Protocol):
    def research(self, task: str, step: PlanStep, context: list[MemoryRecord]) -> str:
        """Return an observation for a plan step."""


class ReflectionProvider(Protocol):
    def reflect(self, task: str, plan: Plan, context: list[MemoryRecord]) -> Reflection:
        """Reflect on evidence and remaining work."""


class HeuristicPlanningProvider:
    def create_plan(self, task: str, memories: list[MemoryRecord]) -> Plan:
        memory_hint = "Use prior memory where relevant." if memories else "Establish baseline context."
        return Plan(
            task=task,
            steps=[
                PlanStep(
                    id="scope",
                    goal="Clarify the task, constraints, and expected output.",
                    method=f"Parse the prompt and identify assumptions. {memory_hint}",
                    success_criteria="The problem boundaries and deliverable are explicit.",
                ),
                PlanStep(
                    id="evidence",
                    goal="Gather supporting evidence and implementation options.",
                    method="Review available context, existing memories, and local/repository signals.",
                    success_criteria="Key options, tradeoffs, and risks are documented.",
                ),
                PlanStep(
                    id="synthesis",
                    goal="Synthesize a recommended path.",
                    method="Convert observations into a concrete implementation or research brief.",
                    success_criteria="The final answer is actionable and cites the evidence used.",
                ),
            ],
        )


class HeuristicResearchProvider:
    def research(self, task: str, step: PlanStep, context: list[MemoryRecord]) -> str:
        prior = "; ".join(record.content for record in context[-3:])
        if step.id == "scope":
            return (
                f"Task: {task}. Deliverable should include a plan, memory handling, "
                "reflection, and a practical coding-agent integration path."
            )
        if step.id == "evidence":
            return (
                "A robust pipeline needs durable memory, bounded working memory, "
                "explicit plan steps, iterative reflection, provider interfaces, "
                "observability, and risk tracking for stale evidence, weak sources, "
                f"or incomplete execution. Recent context: {prior or 'none'}"
            )
        return (
            "Recommended path: keep orchestration separate from providers so search, "
            "LLM calls, browser automation, and coding-agent execution can be swapped independently."
        )


class HeuristicReflectionProvider:
    def reflect(self, task: str, plan: Plan, context: list[MemoryRecord]) -> Reflection:
        completed = [step for step in plan.steps if step.observation]
        gaps: list[str] = []
        if len(completed) < len(plan.steps):
            gaps.append("Some planned research steps have not produced observations yet.")
        if not any("risk" in record.content.lower() for record in context):
            gaps.append("Risks have not been explicitly assessed.")

        confidence = min(0.95, 0.35 + 0.2 * len(completed))
        next_actions = [] if not gaps else ["Run remaining plan steps and add risk analysis."]
        return Reflection(
            summary=f"Completed {len(completed)} of {len(plan.steps)} steps for: {task}",
            gaps=gaps,
            next_actions=next_actions,
            confidence=confidence,
        )
