"""
perception.py
Multi-sensor perception layer: camera / LiDAR / radar -> object detections.

Two modes:
  - SimulatedPerception: noisy detections from ground-truth agents, used
    for algorithm validation and CI testing without hardware/CARLA.
  - The `Detection` dataclass and `PerceptionSource` interface are what a
    real detector plugs into (see integration notes at bottom of file).

Real deployment path:
  camera  -> Ultralytics YOLOv8 (fine-tuned on IDD - India Driving Dataset)
             for class + 2D bbox -> project to ground plane for (x,y)
  LiDAR   -> Open3D / PCL clustering (DBSCAN on point cloud) for 3D boxes
  radar   -> vendor driver CAN/UDP feed for range-rate (velocity) points
  fusion  -> combine per-sensor detections before handing to the tracker
             (tracker.py) -- this file only produces raw detections.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from scenarios import Agent


@dataclass
class Detection:
    type: str
    pos: np.ndarray       # [x, y] in ego/world frame (meters)
    vel: np.ndarray       # [vx, vy] estimate (may be noisy/absent for camera-only)
    confidence: float
    source: str           # 'camera' | 'lidar' | 'radar'


@dataclass
class SensorRanges:
    camera: float = 25.0
    lidar: float = 45.0
    max: float = 70.0


class SimulatedPerception:
    """Ground-truth-driven detection simulator. Swap this class for a real
    PerceptionSource implementation without touching tracker.py / predictor.py
    -- both only depend on the Detection dataclass shape."""

    def __init__(self, ranges: SensorRanges | None = None, seed: int | None = None):
        self.ranges = ranges or SensorRanges()
        self.rng = np.random.default_rng(seed)

    def sense(self, agents: list[Agent], ego_pos: np.ndarray) -> list[Detection]:
        dets: list[Detection] = []
        for a in agents:
            d = float(np.linalg.norm(a.pos - ego_pos))
            if d > self.ranges.max:
                continue

            if d < self.ranges.camera:
                pos_noise, vel_noise, conf, src = 0.15, 0.30, 0.92, "camera+lidar"
            elif d < self.ranges.lidar:
                pos_noise, vel_noise, conf, src = 0.30, 0.50, 0.80, "lidar"
            else:
                pos_noise, vel_noise, conf, src = 0.60, 0.40, 0.55, "radar"

            # occlusion / missed-detection probability (higher for small/soft targets)
            p_miss = 0.03 + (0.05 if a.type in ("pedestrian", "pushcart") else 0.0)
            if self.rng.random() < p_miss:
                continue

            dets.append(Detection(
                type=a.type,
                pos=a.pos + pos_noise * self.rng.standard_normal(2),
                vel=a.vel + vel_noise * self.rng.standard_normal(2),
                confidence=float(np.clip(conf + 0.05 * self.rng.standard_normal(), 0.3, 1.0)),
                source=src,
            ))
        return dets


# ---------------------------------------------------------------------------
# Real-detector integration sketch (not run in the hackathon sim, but this is
# the shape you'd fill in with an actual YOLOv8 model for the live demo):
#
# from ultralytics import YOLO
#
# class YoloCameraPerception:
#     def __init__(self, weights_path: str, homography: np.ndarray):
#         self.model = YOLO(weights_path)          # fine-tuned on IDD classes
#         self.H = homography                       # image-plane -> ground-plane
#
#     def sense(self, frame: np.ndarray) -> list[Detection]:
#         results = self.model(frame, verbose=False)[0]
#         dets = []
#         for box in results.boxes:
#             cls = self.model.names[int(box.cls)]
#             cx, cy = box.xywh[0][:2].tolist()
#             ground_xy = project_image_to_ground([cx, cy], self.H)
#             dets.append(Detection(type=cls, pos=np.array(ground_xy),
#                                    vel=np.zeros(2), confidence=float(box.conf),
#                                    source="camera"))
#         return dets
# ---------------------------------------------------------------------------
