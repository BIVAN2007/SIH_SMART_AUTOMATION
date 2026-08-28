"""
predictor.py
Short-horizon motion prediction per tracked agent. Port of
motionPredictor.m: regular agents (cars) get a tight constant-velocity
projection; irregular agents (pedestrians, rickshaws, carts, cattle,
two-wheelers) get a widening uncertainty cone reflecting non-lane-based,
erratic movement.

Real deployment path: replace `predict()`'s kinematic projection with a
trained LSTM/Seq2Seq model (see sketch at bottom) that outputs a proper
multi-modal distribution over future positions, trained on trajectories
logged from CARLA scenario replays or the IDD dataset's tracked sequences.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from .tracker import Track
from .scenarios import IRREGULAR_TYPES

BASE_SIGMA_M = 0.25   # base positional uncertainty at t=0 (measurement noise)


@dataclass
class Prediction:
    track_id: int
    type: str
    steps: np.ndarray     # (n_steps, 2) predicted [x, y] per future timestep
    radius: np.ndarray    # (n_steps,) 1-sigma uncertainty radius per step


def predict(tracks: list[Track], horizon_s: float, dt: float,
            rng: np.random.Generator) -> list[Prediction]:
    n_steps = round(horizon_s / dt)
    predictions: list[Prediction] = []

    for tr in tracks:
        irregular = tr.type in IRREGULAR_TYPES
        growth_rate = 0.55 if irregular else 0.12   # cone widens ~4.5x faster for irregular agents

        p = tr.pos.copy()
        steps = np.zeros((n_steps, 2))
        radius = np.zeros(n_steps)

        for s in range(n_steps):
            p = p + tr.vel * dt
            if irregular:
                # kinematic mean itself perturbed -- irregular agents don't
                # track a straight line even in expectation
                p = p + 0.05 * rng.standard_normal(2)
            steps[s] = p
            radius[s] = BASE_SIGMA_M + growth_rate * ((s + 1) * dt)

        predictions.append(Prediction(track_id=tr.id, type=tr.type, steps=steps, radius=radius))

    return predictions


# ---------------------------------------------------------------------------
# LSTM predictor integration sketch (drop-in replacement for predict() above
# once you have a trained model + enough logged trajectories to train it):
#
# import torch
#
# class LSTMTrajectoryPredictor:
#     def __init__(self, weights_path: str, obs_len=8, pred_len=30):
#         self.model = torch.jit.load(weights_path).eval()
#         self.obs_len, self.pred_len = obs_len, pred_len
#         self.history: dict[int, list[np.ndarray]] = {}   # per-track position buffer
#
#     def predict(self, tracks: list[Track]) -> list[Prediction]:
#         preds = []
#         for tr in tracks:
#             self.history.setdefault(tr.id, []).append(tr.pos.copy())
#             hist = self.history[tr.id][-self.obs_len:]
#             if len(hist) < self.obs_len:
#                 continue   # not enough history yet -- fall back to kinematic predict()
#             x = torch.tensor(np.stack(hist), dtype=torch.float32).unsqueeze(0)
#             with torch.no_grad():
#                 out = self.model(x)                 # (1, pred_len, 2) or multi-modal (K, pred_len, 2)
#             steps = out.squeeze(0).numpy()
#             radius = np.linspace(0.3, 2.5, len(steps))  # or model-predicted variance
#             preds.append(Prediction(tr.id, tr.type, steps, radius))
#         return preds
# ---------------------------------------------------------------------------
