"""
pipeline.py
Orchestrates one full closed-loop cycle: perception -> tracking ->
prediction -> decision -> planning -> control -> vehicle dynamics.

This is the exact interface Layer 2 (FastAPI backend) calls: instantiate
`DrivingPipeline(scenario_name)`, then call `.step()` once per tick and
stream its returned telemetry dict straight over the WebSocket to the
dashboard. Nothing in Layer 2 needs to know about numpy/dataclasses --
`.step()`'s return value is already JSON-serializable-friendly (call
`.to_json()` on it).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np

from .scenarios import generate_scenario, step_agents, Agent, EgoState
from .perception import SimulatedPerception, SensorRanges
from .tracker import MultiObjectTracker
from .predictor import predict
from .decision_logic import DecisionState, decide
from .planner import plan, Trajectory
from .vehicle import VehicleLimits, pure_pursuit, step as vehicle_step

DT = 0.1
PLAN_HORIZON_S = 3.0
REPLAN_EVERY_S = 0.3
REPLAN_RISK_TRIGGER = 0.75
GOAL_TOLERANCE_M = 3.0


@dataclass
class Telemetry:
    t: float
    ego_pos: list
    ego_theta: float
    ego_speed_kmh: float
    agents: list          # [{type, pos}, ...] ground truth (for viz)
    tracks: list           # [{id, type, pos, vel}, ...] fused tracker output
    planned_path: list      # [[x,y], ...]
    mode: str
    mode_note: str
    min_ttc: float
    nearest_dist: float
    min_clearance_m: float
    replan_latency_ms: float
    path_risk: float
    path_smoothness: float
    done: bool
    collision: bool

    def to_json(self) -> dict:
        return asdict(self)


class DrivingPipeline:
    def __init__(self, scenario_name: str, seed: int | None = None):
        self.scn = generate_scenario(scenario_name)
        self.rng = np.random.default_rng(seed)
        self.t = 0.0

        self.ego = EgoState(pos=self.scn.ego0.pos.copy(), theta=self.scn.ego0.theta, v=self.scn.ego0.v)
        self.agents: list[Agent] = [
            Agent(a.type, a.pos.copy(), a.vel.copy(), a.behavior, a.trigger_t) for a in self.scn.agents
        ]

        self.perception = SimulatedPerception(SensorRanges(), seed=seed)
        self.tracker = MultiObjectTracker()
        self.decision_state = DecisionState()
        self.limits = VehicleLimits()

        self.current_traj: Trajectory | None = None
        self.time_since_replan = float("inf")
        self.min_clearance = float("inf")
        self.done = False
        self.collision = False
        self.driven_path: list[list[float]] = []

    def step(self) -> Telemetry:
        if self.done:
            return self._telemetry(replan_latency_ms=0.0)

        step_agents(self.agents, self.t, DT, self.scn.bounds, self.rng)

        dets = self.perception.sense(self.agents, self.ego.pos)
        tracks = self.tracker.update(dets, DT)
        predictions = predict(tracks, PLAN_HORIZON_S, DT, self.rng)

        ego_vel = np.array([self.ego.v * np.cos(self.ego.theta), self.ego.v * np.sin(self.ego.theta)])
        decision = decide(self.decision_state, self.ego.pos, ego_vel, tracks, self.scn.lane_marked, DT)

        replan_latency_ms = 0.0
        need_replan = (
            self.current_traj is None
            or self.time_since_replan >= REPLAN_EVERY_S
            or self.current_traj.max_risk > REPLAN_RISK_TRIGGER
        )
        if need_replan:
            import time
            t0 = time.perf_counter()
            self.current_traj = plan(self.ego, self.scn.goal, self.scn.static_obs, predictions,
                                      self.scn.bounds, decision.planner_mode, DT, PLAN_HORIZON_S)
            replan_latency_ms = (time.perf_counter() - t0) * 1000
            self.time_since_replan = 0.0
        else:
            self.time_since_replan += DT

        accel, steer = pure_pursuit(self.ego, self.current_traj, self.limits.wheelbase)
        vehicle_step(self.ego, accel, steer, DT, self.limits)

        min_c = min((float(np.linalg.norm(a.pos - self.ego.pos)) for a in self.agents), default=float("inf"))
        self.min_clearance = min(self.min_clearance, min_c)
        if min_c < 0.6:
            self.collision = True

        self.driven_path.append(self.ego.pos.tolist())
        self.t += DT
        if float(np.linalg.norm(self.ego.pos - self.scn.goal)) < GOAL_TOLERANCE_M:
            self.done = True

        self._last_decision = decision
        return self._telemetry(replan_latency_ms, tracks, decision)

    def _telemetry(self, replan_latency_ms=0.0, tracks=None, decision=None) -> Telemetry:
        tracks = tracks or []
        decision = decision or getattr(self, "_last_decision", None)
        traj = self.current_traj

        return Telemetry(
            t=round(self.t, 2),
            ego_pos=self.ego.pos.round(3).tolist(),
            ego_theta=round(self.ego.theta, 4),
            ego_speed_kmh=round(self.ego.v * 3.6, 2),
            agents=[{"type": a.type, "pos": a.pos.round(2).tolist()} for a in self.agents],
            tracks=[{"id": t.id, "type": t.type, "pos": t.pos.round(2).tolist(),
                      "vel": t.vel.round(2).tolist()} for t in tracks],
            planned_path=traj.xy.round(2).tolist() if traj is not None else [],
            mode=decision.mode.value if decision else "LaneFollow",
            mode_note=decision.note if decision else "",
            min_ttc=round(decision.min_ttc, 2) if decision and decision.min_ttc != float("inf") else -1,
            nearest_dist=round(decision.nearest_dist, 2) if decision and decision.nearest_dist != float("inf") else -1,
            min_clearance_m=round(self.min_clearance, 2) if self.min_clearance != float("inf") else -1,
            replan_latency_ms=round(replan_latency_ms, 2),
            path_risk=round(traj.max_risk, 3) if traj else 0.0,
            path_smoothness=round(traj.smooth_cost, 3) if traj else 0.0,
            done=self.done,
            collision=self.collision,
        )
