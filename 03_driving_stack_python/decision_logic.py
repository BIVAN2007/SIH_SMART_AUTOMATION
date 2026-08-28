"""
decision_logic.py
Behavioral decision layer: a state machine choosing driving mode from
perception/prediction signals. Port of decisionLogic.m (the MATLAB
Stateflow-equivalent).

Real deployment path: if using ROS2, port this 1:1 into a `py_trees`
behavior tree or a ROS2 lifecycle node with the same 5 states -- the
transition CONDITIONS below are the part that took real design effort and
should carry over unchanged; only the state-machine *framework* changes.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import numpy as np

from tracker import Track


class Mode(str, Enum):
    LANE_FOLLOW = "LaneFollow"
    UNMARKED_ROAD_FOLLOW = "UnmarkedRoadFollow"
    CRAWL = "Crawl"
    YIELD = "Yield"
    EMERGENCY_STOP = "EmergencyStop"


# maps each behavioral state -> the planner's speed-envelope/cost-weighting keyword
PLANNER_MODE = {
    Mode.LANE_FOLLOW: "normal",
    Mode.UNMARKED_ROAD_FOLLOW: "normal",
    Mode.CRAWL: "crawl",
    Mode.YIELD: "yield",
    Mode.EMERGENCY_STOP: "emergency",
}

NOTES = {
    Mode.LANE_FOLLOW: "Nominal driving corridor, no active risk agents within threshold.",
    Mode.UNMARKED_ROAD_FOLLOW: "No lane markings detected — planning free-space corridor.",
    Mode.CRAWL: "High agent density or unmarked road with close traffic — speed reduced.",
    Mode.YIELD: "Time-to-collision below caution threshold — ceding right-of-way.",
    Mode.EMERGENCY_STOP: "Critical clearance or TTC breach — hard braking fan engaged.",
}


@dataclass
class DecisionState:
    mode: Mode = Mode.LANE_FOLLOW
    time_in_state: float = 0.0


@dataclass
class DecisionResult:
    mode: Mode
    planner_mode: str
    min_ttc: float
    nearest_dist: float
    note: str


def decide(state: DecisionState, ego_pos: np.ndarray, ego_vel: np.ndarray,
           tracks: list[Track], lane_marked: bool, dt: float) -> DecisionResult:
    min_ttc = float("inf")
    nearest_dist = float("inf")

    for tr in tracks:
        rel = tr.pos - ego_pos
        d = float(np.linalg.norm(rel))
        nearest_dist = min(nearest_dist, d)
        rel_vel = tr.vel - ego_vel
        closing_speed = -float(np.dot(rel_vel, rel)) / max(d, 1e-6)
        if closing_speed > 0.3:
            min_ttc = min(min_ttc, d / closing_speed)

    density = len(tracks)

    # --- transition logic (ported verbatim from decisionLogic.m) ---
    if min_ttc < 1.2 or nearest_dist < 2.0:
        new_mode = Mode.EMERGENCY_STOP
    elif min_ttc < 3.0 or nearest_dist < 4.5:
        new_mode = Mode.YIELD
    elif density >= 4 or (not lane_marked and nearest_dist < 8):
        new_mode = Mode.CRAWL
    elif not lane_marked:
        new_mode = Mode.UNMARKED_ROAD_FOLLOW
    else:
        new_mode = Mode.LANE_FOLLOW

    state.time_in_state = state.time_in_state + dt if new_mode == state.mode else 0.0
    state.mode = new_mode

    return DecisionResult(
        mode=new_mode,
        planner_mode=PLANNER_MODE[new_mode],
        min_ttc=min_ttc,
        nearest_dist=nearest_dist,
        note=NOTES[new_mode],
    )
