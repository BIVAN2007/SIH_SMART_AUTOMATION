"""
models.py
ORM tables.

Run              -- one row per scenario execution: outcome + summary metrics.
                    This is what your metrics dashboard/report queries.
TelemetrySnapshot -- optional per-tick log (position, mode, risk) for a run,
                    used to replay a run afterward without re-simulating it.
                    Written only when a run is started via the WebSocket
                    live-stream endpoint (see main.py); REST-triggered batch
                    runs skip it to keep the table lean.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    scenario = Column(String, index=True, nullable=False)
    seed = Column(Integer, nullable=True)

    completed = Column(Boolean, default=False)
    collision = Column(Boolean, default=False)
    sim_time_s = Column(Float, default=0.0)
    min_clearance_m = Column(Float, nullable=True)
    mean_replan_latency_ms = Column(Float, nullable=True)
    p95_replan_latency_ms = Column(Float, nullable=True)
    path_smoothness = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    snapshots = relationship("TelemetrySnapshot", back_populates="run", cascade="all, delete-orphan")


class TelemetrySnapshot(Base):
    __tablename__ = "telemetry_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    t = Column(Float, nullable=False)
    mode = Column(String, nullable=True)
    payload = Column(JSON, nullable=False)   # full Telemetry.to_json() blob for this tick

    run = relationship("Run", back_populates="snapshots")


class RoadCondition(Base):
    """A single reported condition on a named road segment: a jam, a
    pothole/bumpy patch, an accident, etc. Any car (simulated or later,
    real) can create one; any car planning a route reads active ones to
    avoid that segment. condition_type + severity together drive the
    routing cost penalty in road_network.py -- a JAM and a POTHOLE use
    the exact same table/flow, just different severity."""
    __tablename__ = "road_conditions"

    id = Column(Integer, primary_key=True, index=True)
    road_id = Column(String, index=True, nullable=False)
    condition_type = Column(String, nullable=False)  # JAM | POTHOLE | BUMPY_ROAD | ACCIDENT | CONSTRUCTION
    severity = Column(Float, default=0.6)             # 0..1, scales the route-cost penalty
    reported_by = Column(String, nullable=True)        # vehicle/scenario id that reported it
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
