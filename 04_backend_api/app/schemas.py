"""
schemas.py
Pydantic request/response models -- the API's public contract.
Keep these in sync with models.py, but note they're deliberately separate:
API shape and DB shape are allowed to diverge (e.g. hiding internal
columns, renaming fields for the frontend) without that leaking into
the ORM layer.
"""
from datetime import datetime
from pydantic import BaseModel


class RunCreateRequest(BaseModel):
    scenario: str
    seed: int | None = None


class RunOut(BaseModel):
    id: int
    scenario: str
    seed: int | None
    completed: bool
    collision: bool
    sim_time_s: float
    min_clearance_m: float | None
    mean_replan_latency_ms: float | None
    p95_replan_latency_ms: float | None
    path_smoothness: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class ScenarioSummary(BaseModel):
    scenario: str
    total_runs: int
    completion_rate_pct: float
    collision_rate_pct: float
    mean_replan_latency_ms: float | None
    mean_path_smoothness: float | None


class MetricsSummaryOut(BaseModel):
    scenarios: list[ScenarioSummary]
    overall_completion_rate_pct: float
    overall_collision_rate_pct: float


# ---- V2V road conditions + global routing ----

class RoadConditionCreate(BaseModel):
    road_id: str
    condition_type: str = "JAM"   # JAM | POTHOLE | BUMPY_ROAD | ACCIDENT | CONSTRUCTION
    severity: float = 0.6          # 0..1
    reported_by: str | None = None


class RoadConditionOut(BaseModel):
    id: int
    road_id: str
    condition_type: str
    severity: float
    reported_by: str | None
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RouteRequest(BaseModel):
    start: str
    destination: str


class RouteOut(BaseModel):
    start: str
    destination: str
    path: list[str]          # location ids visited, in order
    path_names: list[str]    # same, as real place names
    road_ids: list[str]      # roads actually used
    total_cost: float
    avoided: list[str]       # road_ids that were penalized/avoided due to active conditions


class LocationOut(BaseModel):
    id: str
    name: str
    lat: float
    lng: float


class RoadOut(BaseModel):
    id: str
    from_id: str
    to_id: str
    from_name: str
    to_name: str
    length_km: float


# ---- manual agent spawning (buttons) ----

class SpawnAgentRequest(BaseModel):
    agent_type: str    # pedestrian | cattle | auto_rickshaw | pushcart | two_wheeler | car
    behavior: str | None = None   # defaults chosen per agent_type if omitted
