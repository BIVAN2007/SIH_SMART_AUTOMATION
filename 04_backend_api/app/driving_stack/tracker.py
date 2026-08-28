"""
tracker.py
Multi-object tracker: associates raw detections across frames into
persistent tracks with smoothed position/velocity. Port of
sensorFusionTracker.m.

Real deployment path: swap Track/MultiObjectTracker internals for
FilterPy's KalmanFilter/IMM per track, or a proper JPDA/GNN implementation
(e.g. via `motpy` or a custom Hungarian-algorithm association using
scipy.optimize.linear_sum_assignment) -- the Track dataclass shape and
public update() method stay the same so planner/predictor are unaffected.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import itertools
import numpy as np

from .perception import Detection

GATE_RADIUS_M = 3.0       # max distance to associate a detection to a track
FILTER_GAIN = 0.6         # smoothing gain (stand-in for a Kalman update)
MAX_MISSED_FRAMES = 5


@dataclass
class Track:
    id: int
    type: str
    pos: np.ndarray
    vel: np.ndarray
    age: int = 0
    missed: int = 0


class MultiObjectTracker:
    def __init__(self):
        self._id_counter = itertools.count(1)
        self.tracks: list[Track] = []

    def update(self, detections: list[Detection], dt: float) -> list[Track]:
        # 1. predict all existing tracks forward
        for tr in self.tracks:
            tr.pos = tr.pos + tr.vel * dt
            tr.age += 1
            tr.missed += 1

        assigned = [False] * len(detections)

        # 2. nearest-neighbor association (same type, within gate radius)
        #    -- replace with scipy.optimize.linear_sum_assignment (Hungarian)
        #    for globally-optimal association at scale.
        for tr in self.tracks:
            best_j, best_d = -1, GATE_RADIUS_M
            for j, det in enumerate(detections):
                if assigned[j] or det.type != tr.type:
                    continue
                d = float(np.linalg.norm(det.pos - tr.pos))
                if d < best_d:
                    best_d, best_j = d, j
            if best_j >= 0:
                det = detections[best_j]
                tr.pos = (1 - FILTER_GAIN) * tr.pos + FILTER_GAIN * det.pos
                tr.vel = (1 - FILTER_GAIN) * tr.vel + FILTER_GAIN * det.vel
                tr.missed = 0
                assigned[best_j] = True

        # 3. spawn new tracks for unassociated detections
        for j, det in enumerate(detections):
            if assigned[j]:
                continue
            self.tracks.append(Track(
                id=next(self._id_counter), type=det.type,
                pos=det.pos.copy(), vel=det.vel.copy(),
            ))

        # 4. prune stale tracks
        self.tracks = [t for t in self.tracks if t.missed < MAX_MISSED_FRAMES]
        return self.tracks
