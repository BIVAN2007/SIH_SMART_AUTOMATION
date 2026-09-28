PROPOSED SOLUTION

Core Architecture: A closed-loop autonomous driving stack specifically designed for unstructured Indian roads.

Complete Pipeline: Seamless integration from Perception → Tracking → Prediction → Decision Logic → Planning → Control.

Edge-Case Handling: Effectively manages non-lane-based movement, informal merging, and mixed traffic (auto- rickshaws, pushcarts, cattle) that break Western-style ADAS.

Dynamic Adaptation: Real-time risk-map replanning utilizing agent-specific uncertainty cones (wider for erratic movers, tighter for structured traffic)

TECHNICAL APPROACH

Sensor Fusion
Camera, LiDAR and radar data are fused for robust perception in mixed traffic.

Scene Understanding
Objects are detected and tracked with ID, velocity and acceleration.

Uncertainty-Aware Prediction
Future trajectories are estimated using agent- specific uncertainty cones

Safe Decision & Planning
LaneFollow, Yield, Crawl and EmergencyStop feed a risk-map planner for real-time replanning.

Vehicle Control
Pure-pursuit converts the selected trajectory into steering, throttle and brake commands.


FEASIBILITY AND VIABILITY

Pipeline Validation:  Modular Python pipeline validated end-to-end across 5 realistic scenarios,achieving 100% completion and 0% collision in 4 out of 5 tests. Instantly deployable via DockerCompose with a live dashboard.

Identified Challenges:  Initial testing revealed a ~33% collision rate strictly within highly dense,chaotic market scenarios. Additional constraints include sensor cost and real-time performancelimits on embedded hardware.

Mitigation Strategy:  Retuning decision thresholds and planner cost weights for high-density traffic.Transitioning to lightweight edge models (YOLOv8-nano). Executing phased validation: Simulation→ Raspberry Pi rover testbed → Real-world trials.
