"""
scenarios.py
Defines the 5 required Indian-road test scenarios: static layout, ego
start state, goal, and scripted dynamic agents. This is the Python port
of generateScenario.m / stepAgents.m from the MATLAB reference pipeline.

In the deployed system, this module is what gets replaced by a live feed
from CARLA (simulation) or real sensor input (hardware demo) -- but the
Agent/Scenario data shapes stay the same, so downstream modules (tracker,
predictor, planner) don't change.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

IRREGULAR_TYPES = {"pedestrian", "auto_rickshaw", "pushcart", "cattle", "two_wheeler"}


@dataclass
class Agent:
    type: str
    pos: np.ndarray          # [x, y]
    vel: np.ndarray          # [vx, vy]
    behavior: str            # 'straight' | 'weave' | 'randomWalk' | 'suddenCross' | 'mergeSlow'
    trigger_t: float = 0.0

    def is_irregular(self) -> bool:
        return self.type in IRREGULAR_TYPES


@dataclass
class EgoState:
    pos: np.ndarray
    theta: float
    v: float


@dataclass
class Scenario:
    name: str
    title: str
    bounds: tuple            # (xmin, xmax, ymin, ymax)
    lane_marked: bool
    ego0: EgoState
    goal: np.ndarray
    static_obs: np.ndarray   # Nx3 [x, y, radius]
    agents: list[Agent] = field(default_factory=list)


def _agent(type_, pos, vel, behavior, trigger_t=0.0):
    return Agent(type_, np.array(pos, dtype=float), np.array(vel, dtype=float), behavior, trigger_t)


def generate_scenario(name: str) -> Scenario:
    if name == "village_road":
        return Scenario(
            name, "Village Road (Unmarked)", (0, 120, -10, 10), False,
            EgoState(np.array([5.0, 0.0]), 0.0, 6.0), np.array([110.0, 2.0]),
            np.array([[45, -3, 1.2], [70, 4, 1.0]]),
            [
                _agent("pedestrian", [40, 5], [-0.3, -1.0], "weave"),
                _agent("two_wheeler", [20, -6], [3.5, 0.6], "weave"),
                _agent("pushcart", [60, 3], [0.4, -0.2], "randomWalk"),
            ],
        )
    if name == "urban_intersection":
        return Scenario(
            name, "Unsignaled Urban Intersection", (-10, 60, -30, 30), True,
            EgoState(np.array([-5.0, 0.0]), 0.0, 8.0), np.array([55.0, 0.0]),
            np.zeros((0, 3)),
            [
                _agent("auto_rickshaw", [25, -20], [0.5, 4.2], "weave"),
                _agent("car", [25, 22], [0.2, -4.0], "straight"),
                _agent("two_wheeler", [10, -15], [2.5, 3.0], "weave"),
                _agent("pedestrian", [25, -3], [0.0, 1.2], "randomWalk"),
            ],
        )
    if name == "highway_merge":
        return Scenario(
            name, "Highway Merge (Slow Mergers)", (0, 200, -8, 8), True,
            EgoState(np.array([5.0, -3.0]), 0.0, 22.0), np.array([190.0, -3.0]),
            np.zeros((0, 3)),
            [
                _agent("car", [60, -3], [18, 0], "straight"),
                _agent("auto_rickshaw", [80, 6], [6, -1.2], "mergeSlow", 2.0),
                _agent("car", [130, -3], [14, 0], "straight"),
            ],
        )
    if name == "market_area":
        return Scenario(
            name, "Dense Market Area (Mixed Traffic)", (0, 80, -8, 8), False,
            EgoState(np.array([3.0, 0.0]), 0.0, 3.0), np.array([75.0, 1.0]),
            np.array([[30, -2, 1.0], [50, 3, 0.8], [55, -1, 0.9]]),
            [
                _agent("pedestrian", [15, 2], [0.2, -0.9], "randomWalk"),
                _agent("pedestrian", [35, -3], [0.1, 0.8], "randomWalk"),
                _agent("pushcart", [45, 1], [-0.3, 0.1], "weave"),
                _agent("two_wheeler", [10, -4], [2.0, 0.9], "weave"),
                _agent("auto_rickshaw", [60, 4], [-1.0, -0.5], "weave"),
            ],
        )
    if name == "cattle_crossing":
        return Scenario(
            name, "Sudden Cattle Crossing", (0, 100, -10, 10), False,
            EgoState(np.array([5.0, 0.0]), 0.0, 12.0), np.array([95.0, 0.0]),
            np.zeros((0, 3)),
            [
                _agent("cattle", [50, -9], [0, 3.2], "suddenCross", 2.5),
                _agent("cattle", [53, -9], [0, 3.0], "suddenCross", 2.7),
            ],
        )
    raise ValueError(f"Unknown scenario '{name}'. Options: village_road, urban_intersection, "
                      f"highway_merge, market_area, cattle_crossing")


ALL_SCENARIOS = ["village_road", "urban_intersection", "highway_merge", "market_area", "cattle_crossing"]


def step_agents(agents: list[Agent], t: float, dt: float, bounds: tuple, rng: np.random.Generator) -> None:
    """Advance ground-truth agent motion one timestep (in-place). Stand-in
    for CARLA actor behavior trees / RoadRunner Scenario actor logic."""
    xmin, xmax, ymin, ymax = bounds
    for a in agents:
        if a.behavior == "straight":
            pass
        elif a.behavior == "weave":
            a.vel[1] += 0.6 * rng.standard_normal() * dt * 5
            a.vel[1] = np.clip(a.vel[1], -3, 3)
        elif a.behavior == "randomWalk":
            a.vel += 0.4 * rng.standard_normal(2) * dt * 5
            spd = np.linalg.norm(a.vel)
            if spd > 1.6:
                a.vel = a.vel / spd * 1.6
        elif a.behavior == "suddenCross":
            if t < a.trigger_t:
                a.vel[:] = 0.0
            else:
                sign = np.sign(a.vel[1]) if a.vel[1] != 0 else 1.0
                a.vel[:] = [0.0, sign * 3.2]
        elif a.behavior == "mergeSlow":
            if t < a.trigger_t:
                a.vel[1] = 0.0
            else:
                a.vel[1] = -1.0

        a.pos += a.vel * dt
        if a.pos[0] < xmin or a.pos[0] > xmax:
            a.vel[0] *= -1
        if a.pos[1] < ymin or a.pos[1] > ymax:
            a.vel[1] *= -1
