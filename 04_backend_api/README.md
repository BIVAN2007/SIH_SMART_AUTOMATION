# Layer 2 — Backend API + Database

FastAPI backend wrapping the Layer 1 `driving_stack` pipeline, with a
Postgres-backed run/metrics database and a WebSocket endpoint for live
telemetry streaming to the dashboard.

## What's actually inside

```
sih_backend/
├── app/
│   ├── driving_stack/       # Layer 1 pipeline, copied in as a package
│   │                          (imports converted to relative — verified working, see below)
│   ├── database.py           # SQLAlchemy engine/session (SQLite locally, Postgres in Docker)
│   ├── models.py              # Run + TelemetrySnapshot ORM tables
│   ├── schemas.py               # Pydantic request/response contracts
│   ├── crud.py                   # DB operations
│   └── main.py                    # FastAPI app: REST + WebSocket routes
├── requirements.txt
├── Dockerfile
├── docker-compose.yml         # postgres + backend, one command
├── .env.example
└── test_ws_client.py            # manual test script for the live stream
```

## What I verified vs. what I couldn't

This sandbox has no network access, so I could not `pip install
fastapi/sqlalchemy/psycopg2` or spin up a Postgres server here — I could
not run `uvicorn` end-to-end in this environment.

What I **did** verify directly:
- The `driving_stack` package (copied into `app/`, imports converted to
  relative) runs correctly through the same `DrivingPipeline` interface
  as Layer 1 — ran a full scenario, confirmed telemetry output.
- Every backend file (`database.py`, `models.py`, `schemas.py`, `crud.py`,
  `main.py`) is syntactically valid Python (`py_compile` clean).

What's untested: the actual FastAPI/SQLAlchemy/Postgres wiring, since
those libraries aren't installed here. Run the smoke test below first —
if anything errors, send me the traceback and I'll fix it directly.

## Local setup (SQLite, zero external services)

```bash
cd sih_backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Then open **http://localhost:8000/docs** — FastAPI auto-generates
interactive API docs, you can trigger runs and see responses right there
without writing any frontend code yet.

### Smoke test
```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"scenario": "village_road", "seed": 42}'

curl http://localhost:8000/api/metrics/summary
```

### Live stream test
```bash
# terminal 1
uvicorn app.main:app --reload --port 8000
# terminal 2
python test_ws_client.py cattle_crossing
```
You should see telemetry ticks print once per ~0.1s of sim time.

## Deployed version (Postgres via Docker Compose)

```bash
docker compose up --build
```
This starts Postgres + the backend together, backend on port 8000,
`DATABASE_URL` wired automatically. Same API, same endpoints — the only
difference is persistence survives container restarts and it's the real
multi-service setup you'd point a hosted frontend at.

For a public demo link: push this to Railway or Render, both support
`docker-compose`-style multi-service deploys directly from a GitHub repo.

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/scenarios` | List the 5 valid scenario names |
| POST | `/api/runs` | Run one scenario headlessly to completion, persist + return summary metrics |
| GET | `/api/runs?scenario=&limit=` | List past runs, optionally filtered |
| GET | `/api/runs/{id}` | Single run detail |
| GET | `/api/metrics/summary` | Aggregate completion/collision rate per scenario — feeds your report table |
| WS | `/ws/live/{scenario_name}?seed=` | Streams one telemetry JSON message per sim tick; auto-persists the run + per-tick snapshots on completion |

### Telemetry message shape (what the WebSocket sends each tick)
```json
{
  "t": 4.2,
  "ego_pos": [24.1, -2.3],
  "ego_theta": 0.05,
  "ego_speed_kmh": 28.4,
  "agents": [{"type": "auto_rickshaw", "pos": [25.5, -18.2]}, ...],
  "tracks": [{"id": 3, "type": "pedestrian", "pos": [25.0, -3.1], "vel": [0.1, 1.0]}, ...],
  "planned_path": [[24.3, -2.1], [24.6, -1.9], ...],
  "mode": "Yield",
  "mode_note": "Time-to-collision below caution threshold — ceding right-of-way.",
  "min_ttc": 2.4,
  "nearest_dist": 6.1,
  "min_clearance_m": 3.2,
  "replan_latency_ms": 18.3,
  "path_risk": 0.31,
  "path_smoothness": 0.08,
  "done": false,
  "collision": false
}
```
This is exactly what your React dashboard subscribes to and renders —
same shape as the fields in the `live_demo.html` browser demo from
earlier, so porting that visualization logic into React components is
mostly a direct translation.

## Next: Layer 3 (frontend dashboard)

Whenever you're ready, this is what a React app would connect to:
```js
const ws = new WebSocket(`ws://localhost:8000/ws/live/${scenario}`);
ws.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  // update canvas/map, metrics panel, mode badge — same data the
  // live_demo.html canvas rendering already consumes
};
```
