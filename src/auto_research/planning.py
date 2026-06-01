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

    def to_dict(self) -> dict[str, object]:
        return {
            "task": self.task,
            "shape": self.shape.value,
            "steps": [
                {
                    "id": step.id,
                    "goal": step.goal,
                    "method": step.method,
                    "success_criteria": step.success_criteria,
                    "parent_id": step.parent_id,
                    "status": step.status.value,
                    "observation": step.observation,
                }
                for step in self.steps
            ],
            "edges": [
                {"source": edge.source, "target": edge.target, "relation": edge.relation}
                for edge in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Plan":
        steps = [
            PlanStep(
                id=str(step["id"]),
                goal=str(step["goal"]),
                method=str(step["method"]),
                success_criteria=str(step["success_criteria"]),
                parent_id=step["parent_id"] if step.get("parent_id") else None,
                status=StepStatus(str(step.get("status", StepStatus.PENDING.value))),
                observation=step["observation"] if step.get("observation") else None,
            )
            for step in data.get("steps", [])
        ]
        edges = [
            PlanEdge(
                source=str(edge["source"]),
                target=str(edge["target"]),
                relation=str(edge.get("relation", "depends_on")),
            )
            for edge in data.get("edges", [])
        ]
        return cls(
            task=str(data["task"]),
            steps=steps,
            shape=PlanShape(str(data.get("shape", PlanShape.GRAPH.value))),
            edges=edges,
        )


@dataclass(frozen=True)
class PlanIssue:
    severity: str
    message: str
    step_id: str | None = None


def lint_plan(plan: Plan) -> list[PlanIssue]:
    issues: list[PlanIssue] = []
    step_ids = {step.id for step in plan.steps}
    if not plan.steps:
        return [PlanIssue("error", "Plan has no steps.")]
    if len(step_ids) != len(plan.steps):
        issues.append(PlanIssue("error", "Plan contains duplicate step ids."))
    for step in plan.steps:
        if not step.goal.strip():
            issues.append(PlanIssue("error", "Step has no goal.", step.id))
        if not step.success_criteria.strip():
            issues.append(PlanIssue("warning", "Step has no success criteria.", step.id))
    for edge in plan.edges:
        if edge.source not in step_ids:
            issues.append(PlanIssue("error", f"Dependency source does not exist: {edge.source}", edge.target))
        if edge.target not in step_ids:
            issues.append(PlanIssue("error", f"Dependency target does not exist: {edge.target}", edge.source))
    issues.extend(_cycle_issues(plan))
    if plan.shape is PlanShape.GRAPH and not plan.edges:
        issues.append(PlanIssue("warning", "Graph plan has no edges."))
    return issues


def _cycle_issues(plan: Plan) -> list[PlanIssue]:
    dependencies: dict[str, list[str]] = {step.id: [] for step in plan.steps}
    for edge in plan.edges:
        if edge.relation == "depends_on":
            dependencies.setdefault(edge.target, []).append(edge.source)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> bool:
        if step_id in visiting:
            return True
        if step_id in visited:
            return False
        visiting.add(step_id)
        for dependency in dependencies.get(step_id, []):
            if visit(dependency):
                return True
        visiting.remove(step_id)
        visited.add(step_id)
        return False

    for step_id in dependencies:
        if visit(step_id):
            return [PlanIssue("error", "Plan dependency graph contains a cycle.", step_id)]
    return []


def choose_plan_shape(task: str) -> PlanShape:
    lowered = task.lower()
    if any(
        marker in lowered
        for marker in ["compare", "explore", "research", "investigate", "graph", "memory", "planning"]
        + [
            "reflect",
            "reflection",
            "long-running",
            "long running",
            "checkpoint",
            "resume",
            "optimize",
            "pipeline",
            "model-view",
            "model view",
        ]
    ):
        return PlanShape.GRAPH
    if any(marker in lowered for marker in ["break down", "decompose", "build", "implement"]):
        return PlanShape.TREE
    return PlanShape.LINEAR
