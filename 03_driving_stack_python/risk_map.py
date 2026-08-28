"""
risk_map.py
Time-indexed probabilistic risk field: static obstacles + predicted agent
positions -> a queryable risk function. Port of occupancyRiskMap.m, but
exposed as a point-query function (`risk_at`) rather than a dense grid,
since the planner only needs risk at specific candidate-trajectory points
-- this avoids building a full grid every planning cycle (the perf fix
already applied in the MATLAB version's pathPlanner.m).
"""
from __future__ import annotations
import numpy as np

from predictor import Prediction


def risk_at(xy: np.ndarray, static_obs: np.ndarray,
            predictions: list[Prediction], step_idx: int) -> np.ndarray:
    """
    xy: (N, 2) array of query points
    Returns: (N,) risk values in [0, 1], vectorized over all query points.
    """
    risk = np.zeros(len(xy))

    # static obstacles: hard 1.0 inside radius, soft Gaussian falloff outside
    for ox, oy, r in static_obs:
        d = np.linalg.norm(xy - np.array([ox, oy]), axis=1)
        soft = np.exp(-np.clip(d - r, 0, None) ** 2 / (2 * 0.6 ** 2)) * (d < r + 2.5)
        risk = np.maximum(risk, soft)
        risk[d <= r] = 1.0

    # dynamic agents at this future timestep: Gaussian risk around predicted pos
    for pr in predictions:
        if step_idx >= len(pr.steps):
            continue
        center = pr.steps[step_idx]
        sigma = max(float(pr.radius[step_idx]), 0.3)
        d2 = np.sum((xy - center) ** 2, axis=1)
        risk = np.maximum(risk, np.exp(-d2 / (2 * sigma ** 2)))

    return risk
