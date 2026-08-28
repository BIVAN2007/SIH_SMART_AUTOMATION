"""
crud.py
Database operations, kept separate from route handlers (main.py) so the
API layer and the persistence layer can be tested/changed independently.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models


def create_run(db: Session, scenario: str, seed: int | None, result: dict) -> models.Run:
    run = models.Run(
        scenario=scenario,
        seed=seed,
        completed=result["completed"],
        collision=result["collision"],
        sim_time_s=result["sim_time_s"],
        min_clearance_m=result["min_clearance_m"],
        mean_replan_latency_ms=result["mean_replan_latency_ms"],
        p95_replan_latency_ms=result["p95_replan_latency_ms"],
        path_smoothness=result["path_smoothness"],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def add_snapshot(db: Session, run_id: int, t: float, mode: str, payload: dict) -> None:
    db.add(models.TelemetrySnapshot(run_id=run_id, t=t, mode=mode, payload=payload))
    db.commit()


def get_run(db: Session, run_id: int) -> models.Run | None:
    return db.query(models.Run).filter(models.Run.id == run_id).first()


def list_runs(db: Session, scenario: str | None = None, limit: int = 100) -> list[models.Run]:
    q = db.query(models.Run)
    if scenario:
        q = q.filter(models.Run.scenario == scenario)
    return q.order_by(models.Run.created_at.desc()).limit(limit).all()


def get_metrics_summary(db: Session) -> dict:
    scenarios = []
    all_runs = db.query(models.Run).all()

    scenario_names = sorted({r.scenario for r in all_runs})
    for name in scenario_names:
        runs = [r for r in all_runs if r.scenario == name]
        total = len(runs)
        completed = sum(1 for r in runs if r.completed)
        collided = sum(1 for r in runs if r.collision)
        latencies = [r.mean_replan_latency_ms for r in runs if r.mean_replan_latency_ms is not None]
        smoothness = [r.path_smoothness for r in runs if r.path_smoothness is not None]

        scenarios.append({
            "scenario": name,
            "total_runs": total,
            "completion_rate_pct": round(100 * completed / total, 1) if total else 0.0,
            "collision_rate_pct": round(100 * collided / total, 1) if total else 0.0,
            "mean_replan_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "mean_path_smoothness": round(sum(smoothness) / len(smoothness), 3) if smoothness else None,
        })

    total_all = len(all_runs)
    overall_completed = sum(1 for r in all_runs if r.completed)
    overall_collided = sum(1 for r in all_runs if r.collision)

    return {
        "scenarios": scenarios,
        "overall_completion_rate_pct": round(100 * overall_completed / total_all, 1) if total_all else 0.0,
        "overall_collision_rate_pct": round(100 * overall_collided / total_all, 1) if total_all else 0.0,
    }
