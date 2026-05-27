from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryScope(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    REFLECTIVE = "reflective"


@dataclass(frozen=True)
class MemoryRecord:
    content: str
    kind: str = "observation"
    scope: MemoryScope = MemoryScope.EPISODIC
    importance: float = 0.5
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now)

    def to_row(self) -> tuple[str, str, str, str, float, float, str, str, str, str | None, int]:
        return (
            self.id,
            self.kind,
            self.content,
            self.scope.value,
            self.importance,
            self.confidence,
            json.dumps(list(self.tags)),
            json.dumps(self.metadata),
            self.created_at,
            None,
            0,
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MemoryRecord":
        keys = row.keys()
        return cls(
            id=row["id"],
            kind=row["kind"],
            content=row["content"],
            scope=MemoryScope(row["scope"]) if "scope" in keys else MemoryScope.EPISODIC,
            importance=row["importance"] if "importance" in keys else 0.5,
            confidence=row["confidence"] if "confidence" in keys else 1.0,
            tags=tuple(json.loads(row["tags"])),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
        )


@dataclass(frozen=True)
class MemoryQuery:
    text: str
    scopes: tuple[MemoryScope, ...] = ()
    kinds: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    limit: int = 8
    recency_weight: float = 0.15
    importance_weight: float = 0.25
    diversity_weight: float = 0.2


@dataclass(frozen=True)
class MemorySearchResult:
    record: MemoryRecord
    score: float
    reasons: tuple[str, ...] = ()


class ShortTermMemory:
    """Bounded working memory for one research session, organized by scope."""

    def __init__(self, max_records: int = 100) -> None:
        self._records: deque[MemoryRecord] = deque(maxlen=max_records)
        self._focus_ids: set[str] = set()

    def add(self, record: MemoryRecord) -> None:
        self._records.append(record)

    def focus(self, record: MemoryRecord) -> None:
        self.add(record)
        self._focus_ids.add(record.id)

    def by_scope(self, scope: MemoryScope, limit: int = 10) -> list[MemoryRecord]:
        records = [record for record in self._records if record.scope is scope]
        return records[-limit:]

    def focused(self) -> list[MemoryRecord]:
        return [record for record in self._records if record.id in self._focus_ids]

    def recent(self, limit: int = 10) -> list[MemoryRecord]:
        return list(self._records)[-limit:]

    def all(self) -> list[MemoryRecord]:
        return list(self._records)


class LongTermMemory:
    """SQLite-backed memory store with classical lexical retrieval."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        self._connection.close()

    def add(self, record: MemoryRecord) -> None:
        self._connection.execute(
            """
            insert or replace into memories
            (id, kind, content, scope, importance, confidence, tags, metadata, created_at, last_accessed_at, access_count)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            record.to_row(),
        )
        self._connection.commit()

    def search(self, query: str, limit: int = 8) -> list[MemoryRecord]:
        return [result.record for result in self.retrieve(MemoryQuery(text=query, limit=limit))]

    def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        rows = self._candidate_rows(query)
        records = [MemoryRecord.from_row(row) for row in rows]
        results = score_memories(query, records)
        self._mark_accessed([result.record.id for result in results])
        return results

    def _candidate_rows(self, query: MemoryQuery) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[str] = []
        if query.scopes:
            clauses.append(f"scope in ({','.join('?' for _ in query.scopes)})")
            params.extend(scope.value for scope in query.scopes)
        if query.kinds:
            clauses.append(f"kind in ({','.join('?' for _ in query.kinds)})")
            params.extend(query.kinds)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        return self._connection.execute(
            f"select * from memories {where} order by created_at desc limit 500",
            params,
        ).fetchall()

    def _mark_accessed(self, record_ids: list[str]) -> None:
        if not record_ids:
            return
        now = utc_now()
        self._connection.executemany(
            """
            update memories
            set last_accessed_at = ?, access_count = access_count + 1
            where id = ?
            """,
            [(now, record_id) for record_id in record_ids],
        )
        self._connection.commit()

    def _migrate(self) -> None:
        self._connection.execute(
            """
            create table if not exists memories (
                id text primary key,
                kind text not null,
                content text not null,
                tags text not null,
                metadata text not null,
                created_at text not null
            )
            """
        )
        existing = {
            row["name"]
            for row in self._connection.execute("pragma table_info(memories)").fetchall()
        }
        for name, ddl in {
            "scope": "alter table memories add column scope text not null default 'episodic'",
            "importance": "alter table memories add column importance real not null default 0.5",
            "confidence": "alter table memories add column confidence real not null default 1.0",
            "last_accessed_at": "alter table memories add column last_accessed_at text",
            "access_count": "alter table memories add column access_count integer not null default 0",
        }.items():
            if name not in existing:
                self._connection.execute(ddl)
        self._connection.commit()


def score_memories(query: MemoryQuery, records: list[MemoryRecord]) -> list[MemorySearchResult]:
    query_terms = tokenize(query.text)
    if query.tags:
        required = set(query.tags)
        records = [record for record in records if required.intersection(record.tags)]
    if not records:
        return []

    document_terms = [_record_terms(record) for record in records]
    document_frequency = Counter(term for terms in document_terms for term in set(terms))
    average_length = sum(len(terms) for terms in document_terms) / max(1, len(document_terms))
    scored: list[MemorySearchResult] = []
    for index, record in enumerate(records):
        terms = document_terms[index]
        score = _bm25(query_terms, terms, document_frequency, len(records), average_length)
        score += query.importance_weight * record.importance
        score += query.recency_weight * _recency_score(index, len(records))
        reasons = _score_reasons(query_terms, record)
        if score > 0 or not query_terms:
            scored.append(MemorySearchResult(record=record, score=score, reasons=tuple(reasons)))

    scored.sort(key=lambda result: result.score, reverse=True)
    return _diversify(scored, query.limit, query.diversity_weight)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _record_terms(record: MemoryRecord) -> list[str]:
    return tokenize(" ".join([record.content, record.kind, record.scope.value, " ".join(record.tags)]))


def _bm25(
    query_terms: list[str],
    document_terms: list[str],
    document_frequency: Counter[str],
    document_count: int,
    average_length: float,
) -> float:
    if not query_terms or not document_terms:
        return 0.0
    term_frequency = Counter(document_terms)
    k1 = 1.5
    b = 0.75
    score = 0.0
    for term in query_terms:
        frequency = term_frequency[term]
        if frequency == 0:
            continue
        idf = math.log(
            1
            + (document_count - document_frequency[term] + 0.5)
            / (document_frequency[term] + 0.5)
        )
        denominator = frequency + k1 * (1 - b + b * (len(document_terms) / max(average_length, 1)))
        score += idf * ((frequency * (k1 + 1)) / denominator)
    return score


def _recency_score(index: int, total: int) -> float:
    if total <= 1:
        return 1.0
    return 1 - (index / (total - 1))


def _score_reasons(query_terms: list[str], record: MemoryRecord) -> list[str]:
    record_terms = set(_record_terms(record))
    reasons = [f"matched:{term}" for term in query_terms if term in record_terms]
    if record.importance >= 0.75:
        reasons.append("high-importance")
    if record.scope is MemoryScope.PROCEDURAL:
        reasons.append("procedural")
    return reasons


def _diversify(
    results: list[MemorySearchResult],
    limit: int,
    diversity_weight: float,
) -> list[MemorySearchResult]:
    selected: list[MemorySearchResult] = []
    remaining = list(results)
    while remaining and len(selected) < limit:
        best = max(
            remaining,
            key=lambda result: result.score
            - diversity_weight
            * max((_jaccard(result.record, item.record) for item in selected), default=0),
        )
        selected.append(best)
        remaining.remove(best)
    return selected


def _jaccard(left: MemoryRecord, right: MemoryRecord) -> float:
    left_terms = set(_record_terms(left))
    right_terms = set(_record_terms(right))
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms.intersection(right_terms)) / len(left_terms.union(right_terms))
