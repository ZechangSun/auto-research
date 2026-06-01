from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


def parse_time(value: str | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


@dataclass
class ScheduleExecution:
    run_id: str
    status: str
    executed_at: str

    def to_dict(self) -> dict[str, object]:
        return {"run_id": self.run_id, "status": self.status, "executed_at": self.executed_at}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ScheduleExecution":
        return cls(
            run_id=str(data["run_id"]),
            status=str(data["status"]),
            executed_at=str(data["executed_at"]),
        )


@dataclass
class ScheduledTask:
    task: str
    every_minutes: int
    steps: int = 1
    max_steps: int = 5
    id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "active"
    next_run_at: str = field(default_factory=lambda: format_time(datetime.now(timezone.utc)))
    last_run_at: str | None = None
    last_run_id: str | None = None
    executions: list[ScheduleExecution] = field(default_factory=list)

    def is_due(self, now: datetime) -> bool:
        return self.status == "active" and parse_time(self.next_run_at) <= now

    def mark_executed(self, run_id: str, run_status: str, now: datetime) -> None:
        self.last_run_at = format_time(now)
        self.last_run_id = run_id
        self.next_run_at = format_time(now + timedelta(minutes=self.every_minutes))
        self.executions.append(ScheduleExecution(run_id, run_status, format_time(now)))

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "task": self.task,
            "every_minutes": self.every_minutes,
            "steps": self.steps,
            "max_steps": self.max_steps,
            "status": self.status,
            "next_run_at": self.next_run_at,
            "last_run_at": self.last_run_at,
            "last_run_id": self.last_run_id,
            "executions": [execution.to_dict() for execution in self.executions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ScheduledTask":
        return cls(
            id=str(data["id"]),
            task=str(data["task"]),
            every_minutes=int(data["every_minutes"]),
            steps=int(data.get("steps", 1)),
            max_steps=int(data.get("max_steps", 5)),
            status=str(data.get("status", "active")),
            next_run_at=str(data["next_run_at"]),
            last_run_at=str(data["last_run_at"]) if data.get("last_run_at") else None,
            last_run_id=str(data["last_run_id"]) if data.get("last_run_id") else None,
            executions=[ScheduleExecution.from_dict(item) for item in data.get("executions", [])],
        )


class ScheduleStore:
    def __init__(self, path: str | Path = ".auto_research/schedules.json") -> None:
        self.path = Path(path)

    def load(self) -> list[ScheduledTask]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [ScheduledTask.from_dict(item) for item in data.get("tasks", [])]

    def save(self, tasks: list[ScheduledTask]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"tasks": [task.to_dict() for task in tasks]}, indent=2),
            encoding="utf-8",
        )

    def add(self, task: ScheduledTask) -> ScheduledTask:
        tasks = self.load()
        tasks.append(task)
        self.save(tasks)
        return task

    def due(self, now: datetime) -> list[ScheduledTask]:
        return [task for task in self.load() if task.is_due(now)]
