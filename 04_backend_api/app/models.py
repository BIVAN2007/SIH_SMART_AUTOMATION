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
