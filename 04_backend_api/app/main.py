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
import os
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import crud, schemas
from .driving_stack.scenarios import ALL_SCENARIOS
from .driving_stack.pipeline import DrivingPipeline
from .driving_stack import road_network

Base.metadata.create_all(bind=engine)  # creates tables on first run if they don't exist

app = FastAPI(title="ADAS SIH Backend", version="1.0")

# Allow the React dashboard (running on a different port/origin) to call this API.
# Tighten allow_origins to your deployed frontend URL before submission.
FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_STEPS = 300  # 30s of sim time at dt=0.1, mirrors run_all.py's cap


@app.get("/health")
def health():
    return {"status": "ok", "service": "adas-backend"}


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


@app.post("/api/road-conditions", response_model=schemas.RoadConditionOut)
def report_road_condition(req: schemas.RoadConditionCreate, db: Session = Depends(get_db)):
    """A car (simulated or real) flags a road: jam, pothole, bumpy road,
    accident, construction. Any future route request will avoid/penalize
    this road until it's cleared."""
    return crud.report_road_condition(db, req.road_id, req.condition_type, req.severity, req.reported_by)


@app.get("/api/road-conditions", response_model=list[schemas.RoadConditionOut])
def get_active_road_conditions(db: Session = Depends(get_db)):
    return crud.list_active_conditions(db)


@app.delete("/api/road-conditions/{condition_id}")
def clear_road_condition(condition_id: int, db: Session = Depends(get_db)):
    """Mark a condition resolved (jam cleared, pothole fixed)."""
    if not crud.clear_road_condition(db, condition_id):
        raise HTTPException(404, "Condition not found")
    return {"status": "cleared", "id": condition_id}


@app.get("/api/navigation/route", response_model=schemas.RouteOut)
def get_route(start: str, destination: str, db: Session = Depends(get_db)):
    """The 'Google Maps' endpoint: best route from start to destination,
    automatically routing around roads any car has reported as jammed,
    potholed, under construction, etc."""
    active = [
        {"road_id": c.road_id, "condition_type": c.condition_type, "severity": c.severity}
        for c in crud.list_active_conditions(db)
    ]
    try:
        result = road_network.calculate_route(start, destination, active)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


@app.websocket("/ws/live/{scenario_name}")
async def live_stream(ws: WebSocket, scenario_name: str, seed: int | None = None):
    """Stream live telemetry with a browser-controlled simulation playback speed.

    The MATLAB browser demo had a SIM SPEED control (0.5x/1x/2x/4x).
    The original FastAPI stream sent all 0.1 s simulation ticks as fast as the
    server could compute them, so the car appeared to race across the screen.
    Here the client can send {"type":"set_speed","value":0.5..4.0} while the
    run is active. The simulation clock remains physically correct (DT=0.1s);
    only real-time playback pacing changes.
    """
    if scenario_name not in ALL_SCENARIOS:
        await ws.close(code=4004, reason=f"Unknown scenario '{scenario_name}'")
        return

    await ws.accept()
    pipe = DrivingPipeline(scenario_name, seed=seed)
    latencies = []
    db = next(get_db())
    speed_multiplier = 1.0
    disconnected = asyncio.Event()

    async def receive_controls():
        nonlocal speed_multiplier
        try:
            while True:
                message = await ws.receive_json()
                if not isinstance(message, dict):
                    continue
                if message.get("type") == "set_speed":
                    try:
                        value = float(message.get("value", 1.0))
                        if value != value or value in (float("inf"), float("-inf")):
                            continue
                        speed_multiplier = max(0.25, min(4.0, value))
                    except (TypeError, ValueError):
                        continue
                elif message.get("type") == "spawn_agent":
                    # Manual button press: inject a pedestrian/cattle/etc into
                    # the live run right now, same as a scripted scenario agent.
                    agent_type = str(message.get("agent_type", ""))
                    behavior = message.get("behavior")
                    pipe.spawn_agent(agent_type, behavior)
        except (WebSocketDisconnect, RuntimeError):
            disconnected.set()

    control_task = asyncio.create_task(receive_controls())

    try:
        run_row = None
        for _ in range(MAX_STEPS):
            if disconnected.is_set():
                break

            telem = pipe.step()
            if telem.replan_latency_ms > 0:
                latencies.append(telem.replan_latency_ms)

            # Bridge to the global layer: if this car is crawling through
            # high risk, auto-flag the road it's on so the next car's
            # /api/navigation/route call routes around it. scenario_name
            # doubles as the road_id here since each local scenario is a
            # single stretch of road.
            if telem.ego_speed_kmh < 5.0 and telem.path_risk > 0.7:
                crud.report_road_condition(db, scenario_name, "JAM", telem.path_risk, scenario_name)

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

            # One simulation tick is DT seconds of simulated time. Pacing at
            # DT/speed means 1x matches the MATLAB demo, 0.5x is slower, etc.
            await asyncio.sleep(0.1 / speed_multiplier)

        # finalize the run row with summary metrics now that the sim has ended
        if run_row is not None and not disconnected.is_set():
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
        control_task.cancel()
        try:
            await control_task
        except asyncio.CancelledError:
            pass
        db.close()
