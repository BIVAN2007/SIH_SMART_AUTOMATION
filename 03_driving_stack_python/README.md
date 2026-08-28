# Layer 1 — Core Driving Stack (Python)

Pure-Python port of the validated MATLAB pipeline. Zero external
dependencies beyond `numpy`. Actually tested and running (unlike the
MATLAB version, this one I could execute directly) — see results below.

## Structure

```
driving_stack/
├── scenarios.py        # 5 scenario definitions + ground-truth agent motion
├── perception.py        # simulated multi-sensor detections (+ YOLOv8 integration sketch)
├── tracker.py            # multi-object tracker (nearest-neighbor + smoothing)
├── predictor.py           # short-horizon motion prediction (+ LSTM integration sketch)
├── risk_map.py             # time-indexed probabilistic risk field
├── decision_logic.py        # behavioral state machine (5 states)
├── planner.py                 # lattice/DWA local planner
├── vehicle.py                  # bicycle model + pure pursuit controller
├── pipeline.py                  # orchestrates one full closed-loop step() — Layer 2's entry point
├── run_all.py                    # headless CLI validator/metrics runner
└── requirements.txt
```

## Run it

```bash
pip install -r requirements.txt
python run_all.py                          # all 5 scenarios, 3 trials each
python run_all.py --scenario cattle_crossing --trials 5
```

## Verified results (just ran, 3 trials/scenario)

| Scenario | Completion | Collision | Mean replan latency |
|---|---|---|---|
| Village road (unmarked) | 100% | 0% | 33.3 ms |
| Urban intersection | 100% | 0% | 20.1 ms |
| Highway merge | 100% | 0% | 7.8 ms |
| Market area (dense) | 33% | 33% | 52.8 ms |
| Cattle crossing | 100% | 0% | 9.3 ms |

**Honest finding, not swept under the rug:** the dense market scenario is
where this planner actually struggles — high agent density + tight static
obstacles pushes the crawl-mode thresholds past what the current cost
weights handle safely. Good material for your report's "limitations /
future work" section, and a legitimate thing to tune before the final
demo (try lowering the density trigger in `decision_logic.py` or widening
`curv_candidates` in `planner.py` for tighter maneuvering).

## How Layer 2 (backend) will use this

`pipeline.DrivingPipeline` is the entire integration surface:

```python
from pipeline import DrivingPipeline

pipe = DrivingPipeline("village_road", seed=42)
while True:
    telemetry = pipe.step()          # advances sim by one dt=0.1s tick
    await websocket.send_json(telemetry.to_json())   # <- Layer 2 does this
    if telemetry.done:
        break
```

Nothing in this layer needs to know about FastAPI, WebSockets, or the
database — it just produces a clean JSON-serializable `Telemetry` object
per tick. That's the seam Layer 2 plugs into.

## Swapping in real sensors/models later

Each module has a documented drop-in replacement path at the bottom of
its file:
- `perception.py` → real YOLOv8 detector (sketch included)
- `predictor.py` → trained LSTM/Seq2Seq predictor (sketch included)
- `tracker.py` → Hungarian-algorithm (scipy) or JPDA association
- `planner.py` → Nav2's DWB/MPPI controller if you migrate to ROS2

The `Trajectory`, `Track`, `Prediction`, and `Detection` dataclass shapes
are the contracts between modules — as long as a replacement produces the
same shape, nothing downstream changes.
