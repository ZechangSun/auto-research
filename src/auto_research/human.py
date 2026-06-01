from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class HumanReviewKind(str, Enum):
    APPROVAL = "approval"
    CLARIFICATION = "clarification"
    DECISION = "decision"
    RISK_REVIEW = "risk_review"


class HumanDecision(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"
    COMMENT = "comment"


class HumanReviewStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


@dataclass
class HumanReview:
    prompt: str
    kind: HumanReviewKind = HumanReviewKind.APPROVAL
    step_id: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)
    status: HumanReviewStatus = HumanReviewStatus.OPEN
    decision: HumanDecision | None = None
    content: str | None = None
    created_at: str = field(default_factory=now_utc)
    responded_at: str | None = None

    def respond(self, decision: HumanDecision, content: str) -> None:
        self.status = HumanReviewStatus.RESOLVED
        self.decision = decision
        self.content = content
        self.responded_at = now_utc()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "prompt": self.prompt,
            "step_id": self.step_id,
            "status": self.status.value,
            "decision": self.decision.value if self.decision else None,
            "content": self.content,
            "created_at": self.created_at,
            "responded_at": self.responded_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "HumanReview":
        return cls(
            id=str(data["id"]),
            kind=HumanReviewKind(str(data.get("kind", HumanReviewKind.APPROVAL.value))),
            prompt=str(data["prompt"]),
            step_id=data.get("step_id") if data.get("step_id") else None,
            status=HumanReviewStatus(str(data.get("status", HumanReviewStatus.OPEN.value))),
            decision=HumanDecision(str(data["decision"])) if data.get("decision") else None,
            content=str(data["content"]) if data.get("content") else None,
            created_at=str(data.get("created_at", now_utc())),
            responded_at=str(data["responded_at"]) if data.get("responded_at") else None,
        )
