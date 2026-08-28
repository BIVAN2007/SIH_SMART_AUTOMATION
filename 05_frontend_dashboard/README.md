# Layer 3 — React Live Dashboard

Vite + React dashboard that connects to Layer 2's FastAPI backend: live
WebSocket telemetry rendered on canvas, plus a database-backed run-history
panel pulled from the REST API.

## Structure

```
sih_frontend/
├── src/
│   ├── config.js                    # backend URLs (env-overridable)
│   ├── api.js                        # REST client (scenarios/runs/metrics)
│   ├── hooks/useSimulationSocket.js   # WebSocket connection + telemetry state
│   ├── components/
│   │   ├── SimulationCanvas.jsx        # live top-down render
│   │   ├── ModeBadge.jsx                # decision-state indicator
│   │   ├── MetricsPanel.jsx              # live single-run telemetry
│   │   ├── MetricsSummary.jsx             # DB-backed aggregate history
│   │   └── TransportControls.jsx           # scenario picker, start/stop
│   ├── App.jsx                        # wires it all together
│   ├── main.jsx                        # React entry point
│   └── index.css                        # dark technical dashboard theme
├── index.html
├── package.json
└── vite.config.js
```

## What I verified vs. what I couldn't

No network access in this sandbox (npm registry returns 403), so I could
not run `npm install` or `vite dev` here.

What I **did** verify: every `.js`/`.jsx` file compiles cleanly through
`esbuild` (found a cached copy on this machine) — confirms all JSX syntax,
imports, and exports are structurally correct. That's a real syntax
guarantee, not just a manual read-through.

What's untested: the actual running app in a browser, and the live
WebSocket connection to a running backend (since Layer 2 also couldn't be
started here). Run the setup below — if anything breaks, send me the
error and I'll fix it directly.

## Setup

Requires Layer 2 (`sih_backend`) running first.

```bash
cd sih_backend
uvicorn app.main:app --reload --port 8000
```

Then, in another terminal:
```bash
cd sih_frontend
npm install
npm run dev
```
Open **http://localhost:5173**.

## Using it

1. Pick a scenario from the dropdown, hit **Start live run**
2. Watch the canvas animate — ego vehicle (teal), agents (colored by
   type), planned path (teal dashed, turns red when risky), driven trail
3. Right panel shows live metrics (speed, clearance, replan latency,
   active tracks) and the current decision state (LaneFollow/Yield/
   Crawl/EmergencyStop) with the same reasoning note the backend produces
4. **Run history** panel at the bottom pulls aggregate completion/
   collision rates per scenario straight from the Postgres/SQLite
   database — every run you complete here (or trigger via `POST
   /api/runs`) shows up there after a refresh

## Deploying

- **Vercel** or **Netlify**: point either at this folder, build command
  `npm run build`, output dir `dist`. Set `VITE_API_BASE` /
  `VITE_WS_BASE` env vars to your deployed backend's URL (must be
  `https://`/`wss://` if the backend is deployed with TLS).
- Keep CORS open (or scope it to your frontend's exact origin) in the
  backend's `main.py` — already set to `allow_origins=["*"]` for hackathon
  simplicity; tighten it before final submission if you want to look
  security-conscious to judges.

## What's left for a complete SIH submission

- **Batch-run trigger UI**: a button that calls `POST /api/runs` in a
  loop across all 5 scenarios × N trials (the REST endpoint already
  supports this — just needs a "Run full validation sweep" button and a
  results table, maybe 30 minutes of work)
- **Replay mode**: `GET /api/runs/{id}` + stored `TelemetrySnapshot` rows
  already give you everything needed to replay a past run without
  re-simulating — same `SimulationCanvas` component, fed from an array
  instead of a live socket
- **Optional**: swap the canvas for a proper map library (deck.gl/
  Mapbox) if you want it to look more like a real ops dashboard for the
  demo — not necessary, but scores well visually
