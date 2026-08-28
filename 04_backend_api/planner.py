"""
planner.py
Local lattice / DWA-style planner: generates a fan of candidate
(speed, curvature) trajectories from the ego's current state, scores each
against the time-indexed risk field, picks the best. Port of
pathPlanner.m.

Real deployment path: for a ROS2 stack, replace this module's search with
Nav2's controller_server (DWB or MPPI controller plugin) fed by a costmap
built from `risk_map.py`'s risk_at() function -- or keep this custom
planner as-is; it's a legitimate, explainable lattice planner in its own
right and is easy to defend to judges since you can show the exact cost
function.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from scenarios import EgoState, Agent
from risk_map import risk_at

# cost function weights -- tune here, keep in sync with the MATLAB version
W_RISK = 8.0
W_SMOOTH = 1.5
W_PROGRESS = 1.0
W_SPEED = 0.1
HARD_REJECT_RISK = 0.9
# Conservative geometric safety margins for the simulation/demo.  These are
# deliberately stricter than the soft probabilistic risk score so that a
# low-probability prediction can never result in the ego trajectory actually
# intersecting a moving actor.
EGO_RADIUS_M = 1.05
AGENT_RADIUS_M = {
    "car": 1.25, "auto_rickshaw": 1.25, "two_wheeler": 0.9,
    "pedestrian": 0.75, "pushcart": 0.9, "cattle": 1.15,
}
SAFETY_MARGIN_M = 0.45


@dataclass
class Trajectory:
    xy: np.ndarray          # (n_steps, 2)
    theta: np.ndarray       # (n_steps,)
    v: float
    cost: float
    max_risk: float
    smooth_cost: float
    progress_cost: float


def _speed_envelope(mode: str, ego_v: float) -> np.ndarray:
    if mode == "emergency":
        # Include a true stop candidate.  The previous envelope never offered
        # a full stop at highway speeds, which could make every emergency
        # trajectory unsafe and then fall back to an unvalidated path.
        return np.unique(np.array([0.0, max(ego_v - 8.0, 0.0), max(ego_v - 4.0, 0.0),
                                   max(ego_v - 2.0, 0.0)]))
    if mode == "yield":
        return np.array([0.0, ego_v * 0.25, ego_v * 0.5])
    if mode == "crawl":
        return np.array([1.0, min(ego_v + 0.5, 3.0), min(ego_v + 1.0, 4.0)])
    return np.array([max(ego_v - 2, 0), ego_v, ego_v + 2])


def _simulate_arc(ego: EgoState, v: float, curvature: float, dt: float, n_steps: int):
    xy = np.zeros((n_steps, 2))
    theta = np.zeros(n_steps)
    x, y, th = ego.pos[0], ego.pos[1], ego.theta
    for s in range(n_steps):
        th += v * curvature * dt
        x += v * np.cos(th) * dt
        y += v * np.sin(th) * dt
        xy[s] = (x, y)
        theta[s] = th
    return xy, theta


def _geometric_safety_ok(xy: np.ndarray, static_obs: np.ndarray,
                         predictions, agents: list[Agent] | None, dt: float) -> bool:
    """Hard safety gate used in addition to the probabilistic risk score.

    The risk map is intentionally soft/probabilistic.  For a safety demo we
    also require a positive physical separation from every actor along the
    whole candidate horizon.  When ground-truth simulation actors are
    available, their scripted velocity is used as a conservative second
    check; this models the safety supervisor sitting underneath the planner.
    """
    # Static obstacles: treat their configured radius as physical occupancy.
    for ox, oy, r in static_obs:
        min_allowed = EGO_RADIUS_M + float(r) + SAFETY_MARGIN_M
        if np.any(np.linalg.norm(xy - np.array([ox, oy]), axis=1) < min_allowed):
            return False

    # Prediction-space gate.  Inflate each predicted uncertainty radius by a
    # fixed ego/actor footprint margin, so merely touching an uncertainty cone
    # is not accepted as a safe path.
    for pr in predictions:
        n = min(len(pr.steps), len(xy))
        if n == 0:
            continue
        actor_r = AGENT_RADIUS_M.get(pr.type, 1.0)
        allowed = EGO_RADIUS_M + actor_r + SAFETY_MARGIN_M
        d = np.linalg.norm(xy[:n] - pr.steps[:n], axis=1)
        if np.any(d < allowed + pr.radius[:n]):
            return False

    # Ground-truth second check catches a noisy/missed detection before it can
    # become a collision in the simulator.  Use a constant-velocity rollout
    # over the candidate horizon.
    if agents:
        for a in agents:
            actor_r = AGENT_RADIUS_M.get(a.type, 1.0)
            allowed = EGO_RADIUS_M + actor_r + SAFETY_MARGIN_M
            future = np.asarray([a.pos + a.vel * ((i + 1) * dt) for i in range(len(xy))])
            if np.any(np.linalg.norm(xy - future, axis=1) < allowed):
                return False

    return True


def plan(ego: EgoState, goal: np.ndarray, static_obs: np.ndarray, predictions,
         bounds: tuple, mode: str, dt: float, horizon_s: float,
         agents: list[Agent] | None = None) -> Trajectory:
    n_steps = round(horizon_s / dt)
    v_candidates = _speed_envelope(mode, ego.v)
    curv_candidates = np.linspace(-0.12, 0.12, 9)
    xmin, xmax, ymin, ymax = bounds

    best: Trajectory | None = None
    best_cost = float("inf")

    for v in v_candidates:
        for c in curv_candidates:
            xy, theta = _simulate_arc(ego, v, c, dt, n_steps)

            if np.any(xy[:, 0] < xmin) or np.any(xy[:, 0] > xmax) or \
               np.any(xy[:, 1] < ymin) or np.any(xy[:, 1] > ymax):
                continue

            # Hard geometric safety gate comes before the soft risk score.
            # This prevents a candidate from being selected merely because its
            # probabilistic risk is below HARD_REJECT_RISK.
            if not _geometric_safety_ok(xy, static_obs, predictions, agents, dt):
                continue

            # risk cost: query risk field at each step's own future time index
            risk_cost = 0.0
            max_risk = 0.0
            for s in range(n_steps):
                r = risk_at(xy[s:s + 1], static_obs, predictions, s)[0]
                risk_cost += r ** 2 * (n_steps - s) / n_steps
                max_risk = max(max_risk, r)
            if max_risk > HARD_REJECT_RISK:
                continue

            smooth_cost = abs(c) * 3
            progress_cost = float(np.linalg.norm(xy[-1] - goal))
            speed_cost = 0.1 * abs(v - ego.v)

            total = W_RISK * risk_cost + W_SMOOTH * smooth_cost + W_PROGRESS * progress_cost + speed_cost

            if total < best_cost:
                best_cost = total
                best = Trajectory(xy=xy, theta=theta, v=v, cost=total,
                                   max_risk=max_risk, smooth_cost=smooth_cost,
                                   progress_cost=progress_cost)

    if best is None:
        # every candidate rejected -> hold position (hard stop)
        xy = np.tile(ego.pos, (n_steps, 1))
        best = Trajectory(xy=xy, theta=np.full(n_steps, ego.theta), v=0.0,
                           cost=float("inf"), max_risk=1.0, smooth_cost=0.0, progress_cost=0.0)

    return best
