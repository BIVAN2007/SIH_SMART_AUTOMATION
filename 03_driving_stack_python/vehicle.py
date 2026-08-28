"""
vehicle.py
Kinematic bicycle model + pure-pursuit trajectory-tracking controller.
Port of vehicleModel.m / purePursuitController.m.

Real deployment path (Layer 1 -> hardware): if you add the Raspberry-Pi
rover, `VehicleLimits` becomes your actual rover's physical constraints,
and `step()`'s output (accel, steer) maps directly to PWM motor/servo
commands instead of updating a simulated pose.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from scenarios import EgoState
from planner import Trajectory


@dataclass
class VehicleLimits:
    wheelbase: float = 2.7
    max_v: float = 25.0
    max_accel: float = 2.5
    max_decel: float = 6.0
    max_steer: float = np.deg2rad(35)


def pure_pursuit(ego: EgoState, traj: Trajectory, wheelbase: float) -> tuple[float, float]:
    lookahead = max(1.5, 0.6 * ego.v)
    dists = np.linalg.norm(traj.xy - ego.pos, axis=1)
    idx_candidates = np.where(dists >= lookahead)[0]
    idx = int(idx_candidates[0]) if len(idx_candidates) else len(traj.xy) - 1

    target = traj.xy[idx]
    dx, dy = target[0] - ego.pos[0], target[1] - ego.pos[1]
    alpha = np.arctan2(dy, dx) - ego.theta
    ld = max(float(np.hypot(dx, dy)), 0.5)
    steer = np.arctan2(2 * wheelbase * np.sin(alpha), ld)

    kp = 0.8
    accel = kp * (traj.v - ego.v)
    return accel, steer


def step(ego: EgoState, accel: float, steer: float, dt: float, limits: VehicleLimits) -> None:
    """Kinematic bicycle model propagation (in-place update of `ego`)."""
    accel = float(np.clip(accel, -limits.max_decel, limits.max_accel))
    ego.v = float(np.clip(ego.v + accel * dt, 0, limits.max_v))

    steer = float(np.clip(steer, -limits.max_steer, limits.max_steer))
    ego.theta += (ego.v / limits.wheelbase) * np.tan(steer) * dt

    ego.pos[0] += ego.v * np.cos(ego.theta) * dt
    ego.pos[1] += ego.v * np.sin(ego.theta) * dt
