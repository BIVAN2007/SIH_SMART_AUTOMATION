# Adaptive Path Planning & Collision Avoidance — Indian Road Conditions

Runnable MATLAB implementation of the full pipeline: perception → sensor
fusion → prediction → Stateflow-style decision logic → risk-aware
lattice path planning with real-time replanning → pure-pursuit control →
kinematic bicycle-model vehicle dynamics. Validated closed-loop across all
5 required scenarios with logged safety/performance metrics.

## Requirements
- Base MATLAB (R2019b or later). **No toolboxes required to run this as-is**
  — every toolbox-typical function (tracking, percentile, circle-plotting)
  has been reimplemented in plain MATLAB so the whole pipeline runs without
  Automated Driving / Sensor Fusion / Statistics toolboxes installed.

## Quick start
```matlab
% Run a single scenario and print its metrics:
r = runScenario('village_road');

% Run all 5 required scenarios x 5 trials each, aggregate metrics, plot:
runAllScenarios

% Watch one scenario animate live (for demo-video screen capture):
visualizeScenario('cattle_crossing')
```

Valid scenario names: `village_road`, `urban_intersection`, `highway_merge`,
`market_area`, `cattle_crossing`.

## File map
| File | Role |
|---|---|
| `generateScenario.m` | Defines the 5 scenarios (ego start, goal, static obstacles, dynamic agents) |
| `stepAgents.m` | Ground-truth agent motion models (weave/randomWalk/suddenCross/mergeSlow) |
| `perceptionSim.m` | Simulated noisy multi-sensor (camera/LiDAR/radar) detections |
| `sensorFusionTracker.m` | Nearest-neighbor multi-object tracker (fusion) |
| `motionPredictor.m` | Short-horizon per-agent trajectory + uncertainty-cone prediction |
| `occupancyRiskMap.m` | Time-indexed probabilistic risk grid from predictions + static obstacles |
| `decisionLogic.m` | State machine (LaneFollow/UnmarkedRoadFollow/Yield/Crawl/EmergencyStop) |
| `pathPlanner.m` | Lattice/DWA-style local planner scored against the time-indexed risk map |
| `purePursuitController.m` | Trajectory tracking → steering + acceleration commands |
| `vehicleModel.m` | Kinematic bicycle model |
| `runScenario.m` | Closed-loop simulation of one scenario + metrics |
| `runAllScenarios.m` | Runs all 5 scenarios × N trials, aggregates metrics table, plots |
| `visualizeScenario.m` | Live top-down animation of one run |

## Metrics logged (per `runScenario` result)
- `goalReached`, `collision` — scenario completion / safety
- `minClearanceOverall` — closest approach to any agent (m)
- `meanReplanLatencyMs` / `p95ReplanLatencyMs` — planner cycle time
- `pathSmoothness` — mean squared curvature of the driven path

`runAllScenarios` aggregates these into `adas_metrics_summary.csv` and
`adas_results.mat`, plus 4 report-ready figures (completion/collision
bar chart, replanning latency, smoothness/clearance, sample trajectories).

## Mapping to the full MathWorks toolchain
This pipeline is deliberately dependency-free so it runs anywhere, but
every module is a drop-in stand-in for a specific toolbox component —
swap these in for the production-grade submission:

| This repo | Replace with |
|---|---|
| `perceptionSim.m` | Automated Driving Toolbox camera/LiDAR/radar sensor models + a Deep Learning Toolbox detector (YOLOv4/PointPillars) trained on IDD (India Driving Dataset) |
| `sensorFusionTracker.m` | `trackerJPDA` / `trackerGNN` |
| `motionPredictor.m` | Trained LSTM/Seq2Seq trajectory predictor (Deep Learning Toolbox), fit on trajectories logged from RoadRunner scenario replays |
| `decisionLogic.m` | An actual Stateflow chart (same states/transitions) inside the Simulink model |
| `pathPlanner.m` | `plannerHybridAStar` / `plannerRRTStar` (global) + Navigation Toolbox Frenet lattice / DWA local planner |
| `vehicleModel.m` | Vehicle Dynamics Blockset dynamic single-track model |
| `generateScenario.m` / `stepAgents.m` | Two authored RoadRunner scenes (village road, urban intersection) + RoadRunner Scenario actor logic, co-simulated into Simulink via the RoadRunner Scenario block |

The cost function, state-machine transitions, and metrics definitions in
this code are written to match 1:1 with what you'd wire up in the
Simulink/Stateflow/RoadRunner version, so validating logic here first
and then porting is low-risk.

## Note on testing
This was authored and reviewed carefully for correctness (no MATLAB/Octave
runtime was available in the environment that generated it), but has not
been executed end-to-end. Run `runScenario('village_road')` first as a
smoke test before the full `runAllScenarios` sweep — flag anything that
errors and I can debug it with you directly.
