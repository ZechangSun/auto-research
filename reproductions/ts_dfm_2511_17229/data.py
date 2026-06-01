from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterable


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def make_synthetic_rows(count: int = 16, atoms: int = 5, seed: int = 7) -> list[dict[str, Any]]:
    random.seed(seed)
    rows = []
    for _ in range(count):
        z = [6] * atoms
        reactant = [[random.random() + i * 0.8, random.random(), random.random()] for i in range(atoms)]
        product = [[x + 0.2 * random.random(), y - 0.2 * random.random(), zc + 0.1] for x, y, zc in reactant]
        ts = [[(r[0] + p[0]) / 2 + 0.05, (r[1] + p[1]) / 2, (r[2] + p[2]) / 2] for r, p in zip(reactant, product)]
        rows.append({"z": z, "reactant": reactant, "product": product, "ts": ts})
    return rows
