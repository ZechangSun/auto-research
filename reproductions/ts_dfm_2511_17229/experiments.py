from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from reproductions.ts_dfm_2511_17229.data import make_synthetic_rows, write_jsonl
from reproductions.ts_dfm_2511_17229.flow import evaluate, train


def run_early_experiments(output_dir: str | Path, seeds: list[int] | None = None) -> dict[str, Any]:
    seeds = seeds or [3, 7, 11]
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    base = _base_config(output)
    results = []
    for seed in seeds:
        config = copy.deepcopy(base)
        config["seed"] = seed
        config["data"]["train_path"] = str(output / f"synthetic_seed_{seed}.jsonl")
        config["data"]["eval_path"] = config["data"]["train_path"]
        config["training"]["checkpoint"] = str(output / f"checkpoint_seed_{seed}.pt")
        config["outputs"]["metrics_path"] = str(output / f"metrics_seed_{seed}.json")
        config["outputs"]["history_path"] = str(output / f"history_seed_{seed}.json")
        write_jsonl(config["data"]["train_path"], make_synthetic_rows(count=8, atoms=4, seed=seed))
        train(config)
        metrics = evaluate(config)
        history = json.loads(Path(config["outputs"]["history_path"]).read_text(encoding="utf-8"))
        results.append({"seed": seed, **metrics, "history": history})
    summary = {
        "results": results,
        "mean_rmsd": sum(item["mean_rmsd"] for item in results) / len(results),
        "mean_dmae": sum(item["mean_dmae"] for item in results) / len(results),
    }
    (output / "early_experiments_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    render_svg(summary, output / "early_experiments.svg")
    return summary


def render_svg(summary: dict[str, Any], path: str | Path) -> Path:
    results = summary["results"]
    width = 860
    height = 520
    margin = 60
    chart_w = width - 2 * margin
    chart_h = 160
    max_metric = max(max(item["mean_rmsd"], item["mean_dmae"]) for item in results) * 1.15
    max_loss = max(point["loss"] for item in results for point in item["history"]) * 1.15
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfbf8"/>',
        '<text x="60" y="38" font-family="Arial" font-size="22" font-weight="700">TS-DFM Early Synthetic Experiments</text>',
        '<text x="60" y="62" font-family="Arial" font-size="13" fill="#555">Compact scaffold, synthetic reaction triplets, lower is better</text>',
        _axis(60, 95, chart_w, chart_h, "RMSD / DMAE by seed"),
    ]
    group_w = chart_w / len(results)
    bar_w = min(42, group_w / 4)
    for index, item in enumerate(results):
        x0 = margin + index * group_w + group_w * 0.35
        rmsd_h = chart_h * item["mean_rmsd"] / max_metric
        dmae_h = chart_h * item["mean_dmae"] / max_metric
        parts.append(f'<rect x="{x0:.1f}" y="{95 + chart_h - rmsd_h:.1f}" width="{bar_w}" height="{rmsd_h:.1f}" fill="#2f6fbb"/>')
        parts.append(f'<rect x="{x0 + bar_w + 6:.1f}" y="{95 + chart_h - dmae_h:.1f}" width="{bar_w}" height="{dmae_h:.1f}" fill="#d17c1f"/>')
        parts.append(f'<text x="{x0:.1f}" y="{95 + chart_h + 22}" font-family="Arial" font-size="12">seed {item["seed"]}</text>')
        parts.append(f'<text x="{x0:.1f}" y="{95 + chart_h - rmsd_h - 6:.1f}" font-family="Arial" font-size="11">{item["mean_rmsd"]:.3f}</text>')
        parts.append(f'<text x="{x0 + bar_w + 6:.1f}" y="{95 + chart_h - dmae_h - 6:.1f}" font-family="Arial" font-size="11">{item["mean_dmae"]:.3f}</text>')
    parts.extend([
        '<rect x="620" y="88" width="14" height="14" fill="#2f6fbb"/><text x="640" y="100" font-family="Arial" font-size="12">mean RMSD</text>',
        '<rect x="720" y="88" width="14" height="14" fill="#d17c1f"/><text x="740" y="100" font-family="Arial" font-size="12">mean DMAE</text>',
        _axis(60, 330, chart_w, 120, "Training loss curves"),
    ])
    colors = ["#2f6fbb", "#2a9d55", "#c74343", "#7b55c7"]
    for index, item in enumerate(results):
        points = []
        history = item["history"]
        for point_index, point in enumerate(history):
            x = margin + chart_w * point_index / max(1, len(history) - 1)
            y = 330 + 120 - 120 * point["loss"] / max_loss
            points.append(f"{x:.1f},{y:.1f}")
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[index % len(colors)]}" stroke-width="3"/>')
        parts.append(f'<text x="{margin + index * 110}" y="486" font-family="Arial" font-size="12" fill="{colors[index % len(colors)]}">seed {item["seed"]}</text>')
    parts.append("</svg>")
    target = Path(path)
    target.write_text("\n".join(parts), encoding="utf-8")
    return target


def _axis(x: int, y: int, width: int, height: int, title: str) -> str:
    return "\n".join(
        [
            f'<text x="{x}" y="{y - 14}" font-family="Arial" font-size="15" font-weight="700">{title}</text>',
            f'<line x1="{x}" y1="{y + height}" x2="{x + width}" y2="{y + height}" stroke="#333"/>',
            f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + height}" stroke="#333"/>',
        ]
    )


def _base_config(output: Path) -> dict[str, Any]:
    return {
        "seed": 7,
        "data": {"train_path": "", "eval_path": ""},
        "model": {"atom_dim": 48, "pair_dim": 48, "layers": 2, "rbf_dim": 24, "cutoff": 20.0},
        "training": {"epochs": 4, "batch_size": 4, "lr": 0.0005, "sigma": 0.1, "checkpoint": ""},
        "inference": {"steps": 20},
        "outputs": {"metrics_path": "", "history_path": str(output / "history.json")},
    }
