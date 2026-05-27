from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class PlanShape(str, Enum):
    LINEAR = "linear"
    TREE = "tree"
    GRAPH = "graph"


@dataclass
class PlanStep:
    id: str
    goal: str
    method: str
    success_criteria: str
    parent_id: str | None = None
    status: StepStatus = StepStatus.PENDING
    observation: str | None = None


@dataclass(frozen=True)
class PlanEdge:
    source: str
    target: str
    relation: str = "depends_on"


@dataclass
class Plan:
    task: str
    steps: list[PlanStep] = field(default_factory=list)
    shape: PlanShape = PlanShape.GRAPH
    edges: list[PlanEdge] = field(default_factory=list)

    def pending_steps(self) -> list[PlanStep]:
        return [step for step in self.steps if step.status is StepStatus.PENDING]

    def ready_steps(self) -> list[PlanStep]:
        complete = {step.id for step in self.steps if step.status is StepStatus.COMPLETE}
        ready: list[PlanStep] = []
        for step in self.pending_steps():
            dependencies = [
                edge.source
                for edge in self.edges
                if edge.target == step.id and edge.relation == "depends_on"
            ]
            if all(dependency in complete for dependency in dependencies):
                ready.append(step)
        return ready

    def add_dependency(self, source: str, target: str) -> None:
        self.edges.append(PlanEdge(source=source, target=target, relation="depends_on"))

    def children_of(self, step_id: str) -> list[PlanStep]:
        return [step for step in self.steps if step.parent_id == step_id]

    def dependencies_for(self, step_id: str) -> list[str]:
        return [
            edge.source
            for edge in self.edges
            if edge.target == step_id and edge.relation == "depends_on"
        ]

    def is_complete(self) -> bool:
        return all(step.status in {StepStatus.COMPLETE, StepStatus.SKIPPED} for step in self.steps)


def choose_plan_shape(task: str) -> PlanShape:
    lowered = task.lower()
    if any(
        marker in lowered
        for marker in ["compare", "explore", "research", "investigate", "graph", "memory", "planning"]
    ):
        return PlanShape.GRAPH
    if any(marker in lowered for marker in ["break down", "decompose", "build", "implement"]):
        return PlanShape.TREE
    return PlanShape.LINEAR
