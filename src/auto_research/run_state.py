from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from auto_research.planning import Plan


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStatus(str, Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class RunEvent:
    type: str
    message: str
    step_id: str | None = None
    created_at: str = field(default_factory=now_utc)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "message": self.message,
            "step_id": self.step_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RunEvent":
        return cls(
            type=str(data["type"]),
            message=str(data["message"]),
            step_id=data.get("step_id") if data.get("step_id") else None,
            created_at=str(data.get("created_at", now_utc())),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ResearchRunState:
    task: str
    plan: Plan
    run_id: str = field(default_factory=lambda: uuid4().hex)
    status: RunStatus = RunStatus.ACTIVE
    session_id: str | None = None
    steps_executed: int = 0
    max_steps: int = 5
    retry_count: int = 0
    max_retries: int = 2
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    last_error: str | None = None
    events: list[RunEvent] = field(default_factory=list)

    def add_event(
        self,
        event_type: str,
        message: str,
        step_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.events.append(
            RunEvent(
                type=event_type,
                message=message,
                step_id=step_id,
                metadata=metadata or {},
            )
        )

    def next_action(self) -> str:
        if self.status is RunStatus.COMPLETE:
            return "Summarize the result and run `auto-research memory consolidate`."
        if self.status is RunStatus.FAILED:
            return "Inspect last_error, fix the provider/tool issue, then run `auto-research runs step <run-id> --retry`."
        if self.status is RunStatus.WAITING:
            if self.steps_executed >= self.max_steps:
                return "Increase the step budget or review the partial report before continuing."
            return "Resolve the wait condition, then run another checkpointed step."
        ready = self.plan.ready_steps() or self.plan.pending_steps()
        if ready:
            return f"Run the next step: {ready[0].id}."
        return "Review the plan; no dependency-ready step is available."

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "plan": self.plan.to_dict(),
            "status": self.status.value,
            "session_id": self.session_id,
            "steps_executed": self.steps_executed,
            "max_steps": self.max_steps,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_error": self.last_error,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ResearchRunState":
        return cls(
            run_id=str(data["run_id"]),
            task=str(data["task"]),
            plan=Plan.from_dict(data["plan"]),
            status=RunStatus(str(data.get("status", RunStatus.ACTIVE.value))),
            session_id=data.get("session_id") if data.get("session_id") else None,
            steps_executed=int(data.get("steps_executed", 0)),
            max_steps=int(data.get("max_steps", 5)),
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 2)),
            created_at=str(data.get("created_at", now_utc())),
            updated_at=str(data.get("updated_at", now_utc())),
            last_error=data.get("last_error") if data.get("last_error") else None,
            events=[RunEvent.from_dict(event) for event in data.get("events", [])],
        )


class RunStore:
    """Filesystem checkpoint store for resumable long-running research."""

    def __init__(self, root: str | Path = ".auto_research/runs") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, state: ResearchRunState) -> None:
        state.updated_at = now_utc()
        self.path_for(state.run_id).write_text(
            json.dumps(state.to_dict(), indent=2),
            encoding="utf-8",
        )

    def load(self, run_id: str) -> ResearchRunState:
        return ResearchRunState.from_dict(
            json.loads(self.path_for(run_id).read_text(encoding="utf-8"))
        )

    def list(self) -> list[ResearchRunState]:
        states = [
            ResearchRunState.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in self.root.glob("*.json")
        ]
        states.sort(key=lambda state: state.updated_at, reverse=True)
        return states

    def path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"
