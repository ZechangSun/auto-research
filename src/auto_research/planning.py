from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    id: str
    goal: str
    method: str
    success_criteria: str
    status: StepStatus = StepStatus.PENDING
    observation: str | None = None


@dataclass
class Plan:
    task: str
    steps: list[PlanStep] = field(default_factory=list)

    def pending_steps(self) -> list[PlanStep]:
        return [step for step in self.steps if step.status is StepStatus.PENDING]

    def is_complete(self) -> bool:
        return all(step.status in {StepStatus.COMPLETE, StepStatus.SKIPPED} for step in self.steps)

