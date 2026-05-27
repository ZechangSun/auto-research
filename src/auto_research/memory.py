from __future__ import annotations

import json
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MemoryRecord:
    content: str
    kind: str = "observation"
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now)

    def to_row(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.id,
            self.kind,
            self.content,
            json.dumps(list(self.tags)),
            json.dumps(self.metadata),
            self.created_at,
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MemoryRecord":
        return cls(
            id=row["id"],
            kind=row["kind"],
            content=row["content"],
            tags=tuple(json.loads(row["tags"])),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
        )


class ShortTermMemory:
    """Bounded working memory for one research session."""

    def __init__(self, max_records: int = 100) -> None:
        self._records: deque[MemoryRecord] = deque(maxlen=max_records)

    def add(self, record: MemoryRecord) -> None:
        self._records.append(record)

    def recent(self, limit: int = 10) -> list[MemoryRecord]:
        return list(self._records)[-limit:]

    def all(self) -> list[MemoryRecord]:
        return list(self._records)


class LongTermMemory:
    """SQLite-backed memory store with lightweight lexical retrieval."""

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
            (id, kind, content, tags, metadata, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            record.to_row(),
        )
        self._connection.commit()

    def search(self, query: str, limit: int = 8) -> list[MemoryRecord]:
        terms = [term.lower() for term in query.split() if len(term) > 2]
        rows = self._connection.execute(
            "select * from memories order by created_at desc limit 200"
        ).fetchall()
        scored: list[tuple[int, MemoryRecord]] = []
        for row in rows:
            record = MemoryRecord.from_row(row)
            haystack = " ".join([record.content, record.kind, " ".join(record.tags)]).lower()
            score = sum(1 for term in terms if term in haystack)
            if score > 0 or not terms:
                scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return [record for _, record in scored[:limit]]

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
        self._connection.commit()

