from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reproductions.ts_dfm_2511_17229.data import load_jsonl
from reproductions.ts_dfm_2511_17229.geometry import pairwise_distances, reconstruct_from_distances, require_numpy
from reproductions.ts_dfm_2511_17229.metrics import dmae, rmsd
from reproductions.ts_dfm_2511_17229.model import build_tsdvnet, require_torch


def distance_triplet(row: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        pairwise_distances(row["reactant"]),
        pairwise_distances(row["product"]),
        pairwise_distances(row["ts"]),
    )


def train(config: dict[str, Any]) -> None:
    np = require_numpy()
    torch = require_torch()
    seed = int(config.get("seed", 7))
    np.random.seed(seed)
    torch.manual_seed(seed)
    rows = load_jsonl(config["data"]["train_path"])
    model = build_tsdvnet(**config["model"])
    optimizer = torch.optim.Adam(model.parameters(), lr=float(config["training"]["lr"]))
    sigma = float(config["training"].get("sigma", 0.1))
    epochs = int(config["training"]["epochs"])
    checkpoint = Path(config["training"]["checkpoint"])
    checkpoint.parent.mkdir(parents=True, exist_ok=True)

    history: list[dict[str, float]] = []
    for epoch in range(epochs):
        losses = []
        for row in rows:
            d_r, d_p, d_ts = distance_triplet(row)
            d0 = (d_r + d_p) / 2.0
            target_velocity = d_ts - d0
            t = torch.rand(1)
            noise = np.random.normal(scale=sigma, size=d0.shape)
            d_t = t.item() * d_ts + (1 - t.item()) * d0 + noise
            pred = model(
                torch.tensor([row["z"]]),
                torch.tensor(d_r[None, ...], dtype=torch.float32),
                torch.tensor(d_p[None, ...], dtype=torch.float32),
                torch.tensor(d_t[None, ...], dtype=torch.float32),
                t,
            )
            loss = torch.mean((pred - torch.tensor(target_velocity[None, ...], dtype=torch.float32)) ** 2)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu().item()))
        history.append({"epoch": float(epoch + 1), "loss": float(np.mean(losses))})
    torch.save({"model": model.state_dict(), "config": config}, checkpoint)
    history_path = config.get("outputs", {}).get("history_path")
    if history_path:
        Path(history_path).parent.mkdir(parents=True, exist_ok=True)
        Path(history_path).write_text(json.dumps(history, indent=2), encoding="utf-8")


def predict_distances(model: Any, row: dict[str, Any], steps: int = 100) -> Any:
    torch = require_torch()
    d_r, d_p, _ = distance_triplet(row)
    current = (d_r + d_p) / 2.0
    dt = 1.0 / steps
    with torch.no_grad():
        for index in range(steps):
            t = torch.tensor([index * dt], dtype=torch.float32)
            velocity = model(
                torch.tensor([row["z"]]),
                torch.tensor(d_r[None, ...], dtype=torch.float32),
                torch.tensor(d_p[None, ...], dtype=torch.float32),
                torch.tensor(current[None, ...], dtype=torch.float32),
                t,
            )[0].detach().cpu().numpy()
            current = current + velocity * dt
    return current


def evaluate(config: dict[str, Any]) -> dict[str, float]:
    np = require_numpy()
    torch = require_torch()
    seed = int(config.get("seed", 7))
    np.random.seed(seed)
    torch.manual_seed(seed)
    rows = load_jsonl(config["data"]["eval_path"])
    checkpoint = torch.load(config["training"]["checkpoint"], map_location="cpu")
    model = build_tsdvnet(**config["model"])
    model.load_state_dict(checkpoint["model"])
    model.eval()
    values = []
    for row in rows:
        pred_dist = predict_distances(model, row, steps=int(config["inference"]["steps"]))
        pred_coords = reconstruct_from_distances(pred_dist, steps=100)
        values.append({"rmsd": rmsd(pred_coords, np.asarray(row["ts"])), "dmae": dmae(pred_coords, row["ts"])})
    metrics = {
        "mean_rmsd": float(np.mean([item["rmsd"] for item in values])),
        "mean_dmae": float(np.mean([item["dmae"] for item in values])),
    }
    output_path = Path(config["outputs"]["metrics_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
