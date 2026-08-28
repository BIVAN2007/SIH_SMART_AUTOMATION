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
