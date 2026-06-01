from __future__ import annotations

from typing import Any

from reproductions.ts_dfm_2511_17229.geometry import pairwise_distances, require_numpy


def kabsch_align(predicted: Any, target: Any) -> Any:
    np = require_numpy()
    predicted = np.asarray(predicted, dtype=float)
    target = np.asarray(target, dtype=float)
    pred_centered = predicted - predicted.mean(axis=0, keepdims=True)
    target_centered = target - target.mean(axis=0, keepdims=True)
    covariance = pred_centered.T @ target_centered
    u, _, vt = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[-1, -1] = np.linalg.det(vt.T @ u.T)
    rotation = vt.T @ correction @ u.T
    return pred_centered @ rotation


def rmsd(predicted: Any, target: Any) -> float:
    np = require_numpy()
    aligned = kabsch_align(predicted, target)
    target_centered = target - np.asarray(target).mean(axis=0, keepdims=True)
    return float(np.sqrt(np.mean(np.sum((aligned - target_centered) ** 2, axis=-1))))


def dmae(predicted: Any, target: Any) -> float:
    np = require_numpy()
    pred_dist = pairwise_distances(predicted)
    true_dist = pairwise_distances(target)
    n = pred_dist.shape[0]
    mask = ~np.eye(n, dtype=bool)
    return float(np.mean(np.abs(pred_dist[mask] - true_dist[mask])))
