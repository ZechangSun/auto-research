from __future__ import annotations

import math
from typing import Any


def require_numpy() -> Any:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Install reproduction dependencies with `pip install -e '.[ts-dfm]'`.") from exc
    return np


def pairwise_distances(coords: Any) -> Any:
    np = require_numpy()
    coords = np.asarray(coords, dtype=float)
    diff = coords[:, None, :] - coords[None, :, :]
    return np.linalg.norm(diff, axis=-1)


def classical_mds(distances: Any, dim: int = 3) -> Any:
    np = require_numpy()
    distances = np.asarray(distances, dtype=float)
    n = distances.shape[0]
    squared = distances**2
    centering = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centering @ squared @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1][:dim]
    values = np.maximum(eigenvalues[order], 0.0)
    return eigenvectors[:, order] * np.sqrt(values)


def reconstruct_from_distances(distances: Any, steps: int = 200, lr: float = 1.0) -> Any:
    np = require_numpy()
    try:
        from scipy.optimize import minimize
    except ImportError as exc:
        raise RuntimeError("Install scipy with `pip install -e '.[ts-dfm]'`.") from exc

    target = np.asarray(distances, dtype=float)
    init = classical_mds(target, dim=3)
    eps = 1e-8
    weights = 1.0 / np.maximum(target, eps) ** 2
    np.fill_diagonal(weights, 0.0)

    def objective(flat: Any) -> tuple[float, Any]:
        coords = flat.reshape((-1, 3))
        pred = pairwise_distances(coords)
        residual = pred - target
        loss = float(np.sum(weights * residual**2))
        grad = np.zeros_like(coords)
        for i in range(coords.shape[0]):
            for j in range(coords.shape[0]):
                if i == j:
                    continue
                delta = coords[i] - coords[j]
                distance = max(float(np.linalg.norm(delta)), eps)
                grad[i] += 2.0 * weights[i, j] * residual[i, j] * delta / distance
        return loss, grad.reshape(-1)

    result = minimize(
        fun=lambda x: objective(x)[0],
        x0=init.reshape(-1),
        jac=lambda x: objective(x)[1],
        method="L-BFGS-B",
        options={"maxiter": steps, "maxls": 20, "ftol": math.sqrt(np.finfo(float).eps)},
    )
    return result.x.reshape((-1, 3))
