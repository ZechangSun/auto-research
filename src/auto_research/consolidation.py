from __future__ import annotations

from dataclasses import dataclass

from auto_research.memory import LongTermMemory, MemoryRecord, MemoryScope, tokenize


@dataclass(frozen=True)
class ConsolidationReport:
    promoted: list[MemoryRecord]
    skipped: list[MemoryRecord]

    def to_markdown(self) -> str:
        lines = ["# Memory Consolidation", "", "## Promoted"]
        if self.promoted:
            lines.extend(f"- {record.id[:8]} [{record.scope.value}] {record.content}" for record in self.promoted)
        else:
            lines.append("- None")
        lines.extend(["", "## Skipped"])
        if self.skipped:
            lines.extend(f"- {record.id[:8]} [{record.scope.value}] {record.content}" for record in self.skipped)
        else:
            lines.append("- None")
        return "\n".join(lines)


def consolidate_memory(memory: LongTermMemory, recent_limit: int = 50) -> ConsolidationReport:
    """Promote reusable episodic/reflective records into durable memory scopes."""

    promoted: list[MemoryRecord] = []
    skipped: list[MemoryRecord] = []
    for record in memory.recent(recent_limit):
        target_scope = _target_scope(record)
        if target_scope is None:
            skipped.append(record)
            continue
        promoted_record = memory.promote(
            record.id,
            scope=target_scope,
            kind=_target_kind(record),
            importance=max(record.importance, _importance(record)),
            confidence=record.confidence,
            tags=tuple(dict.fromkeys((*record.tags, "consolidated"))),
        )
        if promoted_record:
            promoted.append(promoted_record)
    return ConsolidationReport(promoted=promoted, skipped=skipped)


def _target_scope(record: MemoryRecord) -> MemoryScope | None:
    if record.scope in {MemoryScope.SEMANTIC, MemoryScope.PROCEDURAL}:
        return None
    terms = set(tokenize(record.content))
    if terms.intersection({"use", "prefer", "run", "workflow", "procedure", "method"}):
        return MemoryScope.PROCEDURAL
    if terms.intersection({"risk", "gap", "lesson", "reflection", "avoid"}):
        return MemoryScope.REFLECTIVE
    if terms.intersection({"architecture", "memory", "planning", "retrieval", "provider"}):
        return MemoryScope.SEMANTIC
    return None


def _target_kind(record: MemoryRecord) -> str:
    if record.kind == "reflection":
        return "lesson"
    if _target_scope(record) is MemoryScope.PROCEDURAL:
        return "procedure"
    if _target_scope(record) is MemoryScope.SEMANTIC:
        return "fact"
    return record.kind


def _importance(record: MemoryRecord) -> float:
    terms = set(tokenize(record.content))
    score = 0.65
    if terms.intersection({"risk", "gap", "lesson", "workflow", "procedure"}):
        score += 0.15
    if terms.intersection({"memory", "planning", "retrieval", "provider"}):
        score += 0.1
    return min(score, 0.95)
