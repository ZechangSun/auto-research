from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Reflection:
    summary: str
    gaps: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def needs_more_work(self) -> bool:
        return bool(self.gaps or self.next_actions) and self.confidence < 0.85

