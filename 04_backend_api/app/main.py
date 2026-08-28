"""
main.py
FastAPI application: REST endpoints for triggering/querying batch runs and
metrics, plus a WebSocket endpoint that streams live telemetry from
DrivingPipeline.step() for the frontend dashboard to render in real time.

Run locally:
    uvicorn app.main:app --reload --port 8000

Then:
    http://localhost:8000/docs         <- interactive API docs (auto-generated)
    ws://localhost:8000/ws/live/village_road   <- live telemetry stream
"""
from __future__ import annotations
import statistics as stats

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import crud, schemas
from .driving_stack.scenarios import ALL_SCENARIOS
from .driving_stack.pipeline import DrivingPipeline

Base.metadata.create_all(bind=engine)  # creates tables on first run if they don't exist

app = FastAPI(title="ADAS SIH Backend", version="1.0")

# Allow the React dashboard (running on a different port/origin) to call this API.
# Tighten allow_origins to your deployed frontend URL before submission.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_STEPS = 300  # 30s of sim time at dt=0.1, mirrors run_all.py's cap


@app.get("/api/scenarios")
def list_scenarios():
    return {"scenarios": ALL_SCENARIOS}


@app.post("/api/runs", response_model=schemas.RunOut)
def create_run(req: schemas.RunCreateRequest, db: Session = Depends(get_db)):
    """Run one scenario headlessly to completion (or timeout) and persist
    the summary metrics. Use this for batch validation runs -- the
    dashboard's 'run all scenarios' button hits this in a loop."""
    if req.scenario not in ALL_SCENARIOS:
        raise HTTPException(404, f"Unknown scenario '{req.scenario}'")

    pipe = DrivingPipeline(req.scenario, seed=req.seed)
    latencies = []
    telem = None
    for _ in range(MAX_STEPS):
        telem = pipe.step()
        if telem.replan_latency_ms > 0:
            latencies.append(telem.replan_latency_ms)
        if telem.done:
            break

    result = {
        "completed": telem.done and not telem.collision,
        "collision": telem.collision,
        "sim_time_s": telem.t,
        "min_clearance_m": telem.min_clearance_m,
        "mean_replan_latency_ms": round(stats.mean(latencies), 3) if latencies else None,
        "p95_replan_latency_ms": round(sorted(latencies)[int(0.95 * len(latencies))], 3) if latencies else None,
        "path_smoothness": telem.path_smoothness,
    }
    return crud.create_run(db, req.scenario, req.seed, result)


@app.get("/api/runs", response_model=list[schemas.RunOut])
def get_runs(scenario: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    return crud.list_runs(db, scenario, limit)


@app.get("/api/runs/{run_id}", response_model=schemas.RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = crud.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@app.get("/api/metrics/summary", response_model=schemas.MetricsSummaryOut)
def metrics_summary(db: Session = Depends(get_db)):
    """Aggregate completion/collision rate per scenario, across all stored
    runs. This is what your results dashboard / technical report table
    pulls from."""
    return crud.get_metrics_summary(db)


@app.websocket("/ws/live/{scenario_name}")
async def live_stream(ws: WebSocket, scenario_name: str, seed: int | None = None):
    """Streams one tick of telemetry per message as the scenario runs live.
    On completion, persists a Run row (with per-tick snapshots) to the DB
    automatically, so a live-demo run also becomes queryable history."""
    if scenario_name not in ALL_SCENARIOS:
        await ws.close(code=4004, reason=f"Unknown scenario '{scenario_name}'")
        return

    await ws.accept()
    pipe = DrivingPipeline(scenario_name, seed=seed)
    latencies = []
    db = next(get_db())

    try:
        run_row = None
        for _ in range(MAX_STEPS):
            telem = pipe.step()
            if telem.replan_latency_ms > 0:
                latencies.append(telem.replan_latency_ms)

            await ws.send_json(telem.to_json())

            if run_row is None:
                # create the Run row on first tick so snapshots have a run_id to attach to
                run_row = crud.create_run(db, scenario_name, seed, {
                    "completed": False, "collision": False, "sim_time_s": 0,
                    "min_clearance_m": None, "mean_replan_latency_ms": None,
                    "p95_replan_latency_ms": None, "path_smoothness": None,
                })
            crud.add_snapshot(db, run_row.id, telem.t, telem.mode, telem.to_json())

            if telem.done:
                break

        # finalize the run row with summary metrics now that the sim has ended
        if run_row is not None:
            run_row.completed = telem.done and not telem.collision
            run_row.collision = telem.collision
            run_row.sim_time_s = telem.t
            run_row.min_clearance_m = telem.min_clearance_m
            run_row.mean_replan_latency_ms = round(stats.mean(latencies), 3) if latencies else None
            run_row.p95_replan_latency_ms = (
                round(sorted(latencies)[int(0.95 * len(latencies))], 3) if latencies else None
            )
            run_row.path_smoothness = telem.path_smoothness
            db.commit()

    except WebSocketDisconnect:
        pass
    finally:
        db.close()
