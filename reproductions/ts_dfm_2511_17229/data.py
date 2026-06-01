from __future__ import annotations

import json
import random
import urllib.request
from pathlib import Path
from typing import Any, Iterable

FIGSHARE_DOWNLOADS = {
    "transition1x": [
        "https://figshare.com/ndownloader/files/36035789",
        "https://doi.org/10.6084/m9.figshare.19614657.v4",
    ],
    "rgd1": [
        "https://doi.org/10.6084/m9.figshare.21066901.v6",
    ],
}


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


def download_dataset(name: str, output: str | Path) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for url in FIGSHARE_DOWNLOADS[name]:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "auto-research-reproducer/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                with target.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
            return target
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Unable to download dataset. Attempts:\n" + "\n".join(errors))


def convert_transition1x(input_path: str | Path, output_path: str | Path, split: str = "train", limit: int = 128) -> int:
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError("Install h5py with `pip install -e '.[ts-dfm]'`.") from exc

    rows: list[dict[str, Any]] = []
    with h5py.File(input_path, "r") as handle:
        root = handle[split]
        for formula in root:
            formula_group = root[formula]
            for reaction in formula_group:
                reaction_group = formula_group[reaction]
                row = _reaction_to_row(reaction_group)
                if row is None:
                    continue
                rows.append(row)
                if len(rows) >= limit:
                    write_jsonl(output_path, rows)
                    return len(rows)
    write_jsonl(output_path, rows)
    return len(rows)


def _reaction_to_row(group: Any) -> dict[str, Any] | None:
    try:
        atomic_numbers = group["reactant"]["atomic_numbers"][()].tolist()
        reactant = group["reactant"]["positions"][()][0].tolist()
        product = group["product"]["positions"][()][0].tolist()
        ts = group["transition_state"]["positions"][()][0].tolist()
    except Exception:
        return None
    return {"z": atomic_numbers, "reactant": reactant, "product": product, "ts": ts}
