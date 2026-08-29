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
from dataclasses import dataclass, asdict, field
from collections import deque
import numpy as np

from .scenarios import generate_scenario, step_agents, Agent, EgoState

# Default behavior + spawn offset (ahead of / beside the ego car) used when
# a manual "spawn" button doesn't specify one. Mirrors how scenarios.py
# scripts these same agent types, so a manually-spawned pedestrian behaves
# identically to a scripted one -- the planner/tracker/risk code can't
# tell the difference.
MANUAL_SPAWN_DEFAULTS = {
    "pedestrian":    {"behavior": "randomWalk", "ahead": 18, "lateral": 4.0, "vel": [0.1, -0.9]},
    "cattle":        {"behavior": "suddenCross", "ahead": 22, "lateral": 6.0, "vel": [0.0, 3.0]},
    "auto_rickshaw": {"behavior": "weave", "ahead": 20, "lateral": 3.0, "vel": [1.0, 0.4]},
    "pushcart":      {"behavior": "weave", "ahead": 15, "lateral": 2.5, "vel": [-0.3, 0.1]},
    "two_wheeler":   {"behavior": "weave", "ahead": 20, "lateral": -3.0, "vel": [2.5, 0.6]},
    "car":           {"behavior": "straight", "ahead": 25, "lateral": 3.0, "vel": [10.0, 0.0]},
}
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

# Congestion is "repeated hard braking + staying slow", not just "speed is
# low right now" -- a single hard brake (someone jaywalking) shouldn't
# trigger a jam report; a car braking-crawling-braking repeatedly should.
HARD_BRAKE_DECEL = -2.5      # m/s^2 -- deceleration this sharp counts as a "hard brake" event
BRAKE_WINDOW_S = 5.0          # look at hard-brake events in the last N seconds
BRAKE_EVENTS_FOR_JAM = 3      # this many hard brakes in the window -> report a jam
JAM_COOLDOWN_S = 8.0          # don't re-report the same run's jam more than once this often


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
    hard_brake_count_5s: int    # how many hard-brake events in the trailing window right now
    congestion_alert: bool      # True for exactly the tick a jam gets auto-reported

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

        self._prev_v = self.ego.v
        self._brake_event_times: deque[float] = deque()
        self._last_jam_report_t = -JAM_COOLDOWN_S

    def spawn_agent(self, agent_type: str, behavior: str | None = None) -> bool:
        """Manual injection: drop a new agent into the *running* simulation,
        near the ego car, same shape/behavior system scripted agents use.
        Called from a WebSocket 'spawn_agent' control message (button press
        on the dashboard). Returns False if agent_type is unrecognized."""
        defaults = MANUAL_SPAWN_DEFAULTS.get(agent_type)
        if defaults is None:
            return False

        heading = np.array([np.cos(self.ego.theta), np.sin(self.ego.theta)])
        lateral = np.array([-heading[1], heading[0]])
        spawn_pos = self.ego.pos + heading * defaults["ahead"] + lateral * defaults["lateral"]

        self.agents.append(Agent(
            type=agent_type,
            pos=spawn_pos,
            vel=np.array(defaults["vel"], dtype=float),
            behavior=behavior or defaults["behavior"],
            trigger_t=self.t,   # suddenCross-style agents "wait" then trigger immediately
        ))
        return True

    def step(self) -> Telemetry:
        if self.done:
            return self._telemetry(replan_latency_ms=0.0)

        step_agents(self.agents, self.t, DT, self.scn.bounds, self.rng, ego_pos=self.ego.pos)

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

        # Congestion detection: this tick's actual deceleration (IMU-equivalent
        # signal on real hardware), not the commanded accel -- reflects what the
        # car really did. A hard brake beyond HARD_BRAKE_DECEL gets timestamped;
        # events older than BRAKE_WINDOW_S fall out of the rolling window.
        measured_decel = (self.ego.v - self._prev_v) / DT
        self._prev_v = self.ego.v
        if measured_decel <= HARD_BRAKE_DECEL:
            self._brake_event_times.append(self.t)
        while self._brake_event_times and self.t - self._brake_event_times[0] > BRAKE_WINDOW_S:
            self._brake_event_times.popleft()

        congestion_alert = False
        if (len(self._brake_event_times) >= BRAKE_EVENTS_FOR_JAM
                and self.ego.v * 3.6 < 15.0
                and self.t - self._last_jam_report_t >= JAM_COOLDOWN_S):
            congestion_alert = True
            self._last_jam_report_t = self.t

        min_c = min((float(np.linalg.norm(a.pos - self.ego.pos)) for a in self.agents), default=float("inf"))
        self.min_clearance = min(self.min_clearance, min_c)
        if min_c < 0.6:
            self.collision = True

        self.driven_path.append(self.ego.pos.tolist())
        self.t += DT
        if float(np.linalg.norm(self.ego.pos - self.scn.goal)) < GOAL_TOLERANCE_M:
            self.done = True

        self._last_decision = decision
        return self._telemetry(replan_latency_ms, tracks, decision, congestion_alert)

    def _telemetry(self, replan_latency_ms=0.0, tracks=None, decision=None, congestion_alert=False) -> Telemetry:
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
            hard_brake_count_5s=len(self._brake_event_times),
            congestion_alert=congestion_alert,
        )
