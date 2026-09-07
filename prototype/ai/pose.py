"""
VisionGuard — Pose Estimator
Uses YOLOv8s-pose to estimate body keypoints for detected persons.
Used for fight detection, fall detection, kidnapping detection.
"""
import cv2
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import config
from utils import bbox_iou

logger = logging.getLogger(__name__)


@dataclass
class PoseResult:
    """Pose estimation result for a single person."""
    bbox: List[float]              # [x1, y1, x2, y2]
    confidence: float
    keypoints: np.ndarray          # (17, 3) array — x, y, confidence per keypoint
    track_id: Optional[int] = None # Matched track ID if available

    @property
    def nose(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[0])

    @property
    def left_shoulder(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[5])

    @property
    def right_shoulder(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[6])

    @property
    def left_wrist(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[9])

    @property
    def right_wrist(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[10])

    @property
    def left_hip(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[11])

    @property
    def right_hip(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[12])

    @property
    def left_ankle(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[15])

    @property
    def right_ankle(self) -> Tuple[float, float, float]:
        return tuple(self.keypoints[16])

    @property
    def body_angle(self) -> float:
        """
        Angle of the body from vertical (0 = standing, 90 = lying down).
        Calculated from mid-shoulder to mid-hip vector.
        """
        ls = self.left_shoulder
        rs = self.right_shoulder
        lh = self.left_hip
        rh = self.right_hip

        # Check keypoint confidence
        if ls[2] < 0.3 or rs[2] < 0.3 or lh[2] < 0.3 or rh[2] < 0.3:
            return 0.0  # Not confident enough

        mid_shoulder = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
        mid_hip = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)

        dx = mid_hip[0] - mid_shoulder[0]
        dy = mid_hip[1] - mid_shoulder[1]

        # Angle from vertical (dy dominant = standing, dx dominant = lying)
        angle = abs(np.degrees(np.arctan2(dx, dy)))
        return angle

    @property
    def arm_spread(self) -> float:
        """Distance between left and right wrists — indicates arm spread."""
        lw = self.left_wrist
        rw = self.right_wrist
        if lw[2] < 0.3 or rw[2] < 0.3:
            return 0.0
        dx = rw[0] - lw[0]
        dy = rw[1] - lw[1]
        return (dx ** 2 + dy ** 2) ** 0.5

    @property
    def height_ratio(self) -> float:
        """Ratio of bbox height to width. Standing person > 1.5, fallen < 1.0."""
        x1, y1, x2, y2 = self.bbox
        w = x2 - x1
        h = y2 - y1
        if w == 0:
            return 0.0
        return h / w

    @property
    def is_standing(self) -> bool:
        """Rough check if person is upright."""
        return self.body_angle < 30 and self.height_ratio > 1.2

    @property
    def is_fallen(self) -> bool:
        """Rough check if person has fallen."""
        return self.body_angle > 50 or self.height_ratio < 0.8


class PoseEstimator:
    """
    YOLOv8s-pose based pose estimation.
    Only runs when persons are detected (conditional inference to save GPU).
    """

    def __init__(self):
        self.model: Optional[YOLO] = None
        self._prev_keypoints: Dict[int, np.ndarray] = {}  # track_id -> smoothed (17, 3)

    @property
    def device(self):
        return config.DETECTION_DEVICE

    def load(self):
        """Load the YOLOv8-pose model."""
        logger.info("[POSE] Loading YOLOv8s-pose...")
        try:
            from ultralytics import YOLO
            self.model = YOLO(config.YOLO_POSE_MODEL)
            logger.info("[POSE] Model loaded successfully.")
        except Exception as e:
            logger.error("[POSE] Failed to load pose model: %s", e)
            self.model = None

    def estimate(self, frame: np.ndarray, num_persons: int = 0) -> List[PoseResult]:
        """
        Run pose estimation on a frame.
        Skips if no persons detected or too many (performance).
        """
        if self.model is None:
            return []

        # Conditional: only run if persons present and not too many
        if config.POSE_ONLY_WHEN_PERSONS and num_persons == 0:
            return []
        if num_persons > config.MAX_PERSONS_FOR_POSE:
            return []

        results = self.model.predict(
            frame,
            conf=config.POSE_CONF_THRESHOLD,
            imgsz=config.POSE_IMG_SIZE,
            device=self.device,
            half=config.USE_FP16,  # FP16 GPU acceleration
            verbose=False,
        )

        poses = []
        for result in results:
            if result.keypoints is None or result.boxes is None:
                continue

            for i in range(len(result.boxes)):
                bbox = result.boxes[i].xyxy[0].tolist()
                conf = float(result.boxes[i].conf[0])

                # Get keypoints (17 keypoints, each with x, y, confidence)
                kps = result.keypoints[i].data[0].cpu().numpy()  # (17, 3)

                pose = PoseResult(
                    bbox=bbox,
                    confidence=conf,
                    keypoints=kps,
                )
                poses.append(pose)

        return poses

    def match_poses_to_tracks(self, poses: List[PoseResult], tracks) -> List[PoseResult]:
        """
        Strict 1-to-1 bipartite matching between pose results and person tracks.
        Ensures:
        1. No track can receive more than 1 pose.
        2. No pose can be assigned to more than 1 track.
        3. Zero duplicate skeletons on any individual ("one person 2 pose bodies" eliminated).
        4. Zero incursion/cross-contamination across different persons.
        """
        if not poses or not tracks:
            return poses

        # Pose-Guided Semantic Correction: If a track was misclassified (e.g. firefighter misclassified as car/truck/chair),
        # but contains a valid human pose with >= 4 keypoints, reclassify it to person.
        for pose in poses:
            valid_kps = sum(1 for kp in pose.keypoints if len(kp) > 2 and kp[2] > 0.20)
            if valid_kps >= 4:
                for track in tracks:
                    if getattr(track, "category", "") != "person":
                        iou = bbox_iou(pose.bbox, track.bbox)
                        tb = track.bbox
                        t_h = tb[3] - tb[1]
                        t_w = max(1.0, tb[2] - tb[0])
                        # If overlapping and tall/vertical human profile
                        if iou > 0.20 or (t_h / t_w > 1.1 and bbox_iou(pose.bbox, track.bbox) > 0.15):
                            logger.info("[POSE] Correcting track %s (%s) -> person based on verified human pose (kps: %d)",
                                        getattr(track, "vg_id", track.track_id), track.class_name, valid_kps)
                            track.class_name = "person"
                            track.category = "person"

        person_tracks = [t for t in tracks if getattr(t, "category", "") == "person"]
        if not person_tracks:
            return poses

        # Compute pairwise IoU
        pairs = []
        for p_idx, pose in enumerate(poses):
            for track in person_tracks:
                iou = bbox_iou(pose.bbox, track.bbox)
                if iou > 0.20:
                    pairs.append((iou, p_idx, track.track_id))

        # Greedy match from highest IoU descending
        pairs.sort(key=lambda x: x[0], reverse=True)

        assigned_poses = set()
        assigned_tracks = set()

        for iou, p_idx, t_id in pairs:
            if p_idx not in assigned_poses and t_id not in assigned_tracks:
                assigned_poses.add(p_idx)
                assigned_tracks.add(t_id)
                poses[p_idx].track_id = t_id

        return poses

    def smooth_keypoints(self, poses: List[PoseResult]) -> List[PoseResult]:
        """
        Smooth keypoints across frames for tracked persons using Exponential Moving Average.
        Eliminates keypoint jitter while preserving 100% natural body movement.
        """
        active_ids = set()
        for p in poses:
            if p.track_id is not None:
                active_ids.add(p.track_id)
                if p.track_id in self._prev_keypoints:
                    prev_kps = self._prev_keypoints[p.track_id]
                    # Smooth keypoints with good confidence (> 0.15)
                    for k in range(len(p.keypoints)):
                        if p.keypoints[k, 2] > 0.15 and prev_kps[k, 2] > 0.15:
                            p.keypoints[k, 0] = 0.80 * p.keypoints[k, 0] + 0.20 * prev_kps[k, 0]
                            p.keypoints[k, 1] = 0.80 * p.keypoints[k, 1] + 0.20 * prev_kps[k, 1]
                self._prev_keypoints[p.track_id] = p.keypoints.copy()

        # Prune dead tracks
        for tid in list(self._prev_keypoints.keys()):
            if tid not in active_ids:
                del self._prev_keypoints[tid]

        return poses

    def reset(self):
        """Reset temporal state."""
        self._prev_keypoints.clear()

