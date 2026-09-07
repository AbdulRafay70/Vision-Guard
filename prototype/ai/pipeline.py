"""
VisionGuard — AI Pipeline
Orchestrates: Detection → Tracking → Pose Estimation → Event Detection
Runs all AI components in sequence on each frame.

Performance: Detection + tracking run in a SINGLE model.track() call
to avoid redundant YOLO inference (2× FPS improvement).
"""
import logging
import cv2
import time
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ai.detector import ObjectDetector, Detection
from ai.tracker import ObjectTracker, Track
from ai.pose import PoseEstimator, PoseResult
from ai.specialist_worker import SpecialistWorker, ResultStatus
from utils import bbox_iou

import config

logger = logging.getLogger(__name__)


@dataclass
class FrameAnalysis:
    """Complete analysis result for a single frame."""
    frame_number: int
    timestamp: float
    detections: List[Detection] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    poses: List[PoseResult] = field(default_factory=list)
    violence_results: List[Dict[str, Any]] = field(default_factory=list)  # Neural fight verification
    specialist_telemetry: Dict[str, Any] = field(default_factory=dict)
    ai_fps: float = 0.0
    processing_time_ms: float = 0.0

    @property
    def persons(self) -> List[Track]:
        return [t for t in self.tracks if t.category == "person"]

    @property
    def vehicles(self) -> List[Track]:
        return [t for t in self.tracks if t.category == "vehicle"]

    @property
    def objects(self) -> List[Track]:
        return [t for t in self.tracks if t.category == "object"]

    @property
    def fire_detections(self) -> List[Detection]:
        return [d for d in self.detections if d.category == "fire"]

    @property
    def smoke_detections(self) -> List[Detection]:
        return [d for d in self.detections if d.category == "smoke"]

    @property
    def weapon_detections(self) -> List[Detection]:
        return [d for d in self.detections if d.category == "weapon"]

    @property
    def num_persons(self) -> int:
        return len(self.persons)

    @property
    def num_vehicles(self) -> int:
        return len(self.vehicles)

    @property
    def violence_confirmed(self) -> bool:
        """True if the violence classifier confirmed aggressive behavior."""
        return any(v.get("is_violent", False) for v in self.violence_results)

    @property
    def max_violence_confidence(self) -> float:
        """Highest violence classifier confidence score."""
        if not self.violence_results:
            return 0.0
        return max(v.get("confidence", 0.0) for v in self.violence_results)

    def get_summary(self) -> str:
        parts = []
        if self.num_persons > 0:
            parts.append(f"{self.num_persons} person{'s' if self.num_persons > 1 else ''}")
        if self.num_vehicles > 0:
            parts.append(f"{self.num_vehicles} vehicle{'s' if self.num_vehicles > 1 else ''}")
        obj_count = len(self.objects)
        if obj_count > 0:
            parts.append(f"{obj_count} object{'s' if obj_count > 1 else ''}")
        if self.weapon_detections:
            weapon_names = set(d.class_name for d in self.weapon_detections)
            parts.append(f"⚠️ WEAPON ({', '.join(weapon_names)})")
        if self.fire_detections:
            parts.append(f"FIRE ({len(self.fire_detections)})")
        if self.smoke_detections:
            parts.append(f"SMOKE ({len(self.smoke_detections)})")
        return ", ".join(parts) if parts else "No detections"


class AIPipeline:
    """
    Decoupled Asynchronous AI Pipeline:
    - Primary Path: Fast YOLOv8s Detection + Tracking runs at ~30 FPS on main presentation thread.
    - Secondary Path: Specialist models (Fire/Smoke, Weapon, Pose, Violence) run asynchronously
      in a dedicated background GPU worker thread with attention-based prioritization and max-age expiration.
    """

    def __init__(self, async_mode: bool = True):
        self.async_mode = async_mode
        self.detector = ObjectDetector()
        self.tracker = ObjectTracker()
        self.pose_estimator = PoseEstimator()
        self.specialist_worker = SpecialistWorker(self.detector, self.pose_estimator)

        self._frame_count: int = 0
        self._ai_frame_count: int = 0
        self._start_time: float = 0.0
        self._last_analysis: Optional[FrameAnalysis] = None

        # Synchronous fallback counters (used if async_mode=False)
        self._pose_frame_counter: int = 0
        self._pose_cooldown_frames: int = config.POSE_COOLDOWN_FRAMES
        self._last_poses: List[PoseResult] = []
        self._fire_frame_counter: int = 0
        self._weapon_frame_counter: int = 0
        self._last_fire_detections: List[Detection] = []
        self._last_weapon_detections: List[Detection] = []
        self._fire_buffer: List[Dict[str, Any]] = []

    def load_models(self):
        """Load all AI models and start background specialist worker."""
        logger.info("=" * 60)
        logger.info("  LOADING AI MODELS (ASYNC DECOUPLED PIPELINE)")
        logger.info("=" * 60)

        self.detector.load()
        self.pose_estimator.load()

        # Warmup: run dummy inference to trigger CUDA kernel JIT compilation
        logger.info("  Warming up models...")
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        try:
            self.detector.model.predict(dummy, device=config.DETECTION_DEVICE, half=config.USE_FP16, verbose=False)
        except Exception:
            pass
        if self.detector.fire_model is not None:
            try:
                self.detector.fire_model.predict(dummy, device=config.DETECTION_DEVICE, half=config.USE_FP16, verbose=False)
            except Exception:
                pass
        if self.detector.weapon_model is not None:
            try:
                self.detector.weapon_model.predict(dummy, device=config.DETECTION_DEVICE, half=config.USE_FP16, verbose=False)
            except Exception:
                pass
        if self.pose_estimator.model is not None:
            try:
                self.pose_estimator.model.predict(dummy, device=config.DETECTION_DEVICE, half=config.USE_FP16, verbose=False)
            except Exception:
                pass
        if self.detector.violence_model is not None:
            try:
                dummy_small = np.zeros((224, 224, 3), dtype=np.uint8)
                self.detector.violence_model.predict(dummy_small, device=config.DETECTION_DEVICE, half=config.USE_FP16, verbose=False)
            except Exception:
                pass
        logger.info("  Model warmup complete.")

        # Start specialist background worker thread in async mode
        if self.async_mode:
            self.specialist_worker.start()

        self._start_time = time.time()
        logger.info("=" * 60)
        logger.info("  ALL MODELS LOADED — ASYNC WORKER READY")
        logger.info("=" * 60)

    def stop(self):
        """Stop background worker threads."""
        if self.async_mode:
            self.specialist_worker.stop()

    def process_frame(self, frame: np.ndarray, capture_timestamp: Optional[float] = None,
                      frame_id: Optional[int] = None) -> Optional[FrameAnalysis]:
        """
        Process a single frame.
        Primary Path: Fast YOLOv8s Detection + BYTETrack.
        All specialist models (Pose, Weapon, Fire, Violence) execute asynchronously
        in the SpecialistWorker background thread and are fetched from cache.
        The main presentation loop NEVER blocks on secondary inference.
        """
        self._frame_count += 1
        current_fid = frame_id if frame_id is not None else self._frame_count
        c_time = capture_timestamp if capture_timestamp is not None else time.monotonic()

        if not self.async_mode:
            return self._process_frame_synchronous(frame)

        start = time.monotonic()
        self._ai_frame_count += 1

        # Step 1: FAST PRIMARY PATH — Detection + Tracking in ONE model.track() call
        detections, tracks = self.tracker.update(frame, self.detector.model)

        # Step 2: Push latest frame reference, frame ID, capture time, and tracks to specialist worker
        self.specialist_worker.push_frame(frame, current_fid, c_time, tracks)

        # Step 3: Fetch cached specialist results (monotonic age-based validity check)
        specialist_results = self.specialist_worker.get_results()
        telemetry = self.specialist_worker.get_telemetry()

        # Merge active specialist detections (skip expired detections > 750ms)
        fire_res = specialist_results.get("fire")
        if fire_res and fire_res.is_display_valid and fire_res.data:
            detections.extend(fire_res.data)

        weapon_res = specialist_results.get("weapon")
        if weapon_res and weapon_res.is_display_valid and weapon_res.data:
            detections.extend(weapon_res.data)

        # Step 4: POSE ESTIMATION — Retrieved exclusively from async specialist cache
        poses = []
        pose_res = specialist_results.get("pose")
        if pose_res and pose_res.is_display_valid and pose_res.data:
            poses = pose_res.data

        # Semantic Pose-Guided Correction: If a human skeleton is confirmed inside an object/vehicle box (e.g. firefighter misclassified as car)
        if poses:
            for pose in poses:
                valid_kps = sum(1 for kp in pose.keypoints if len(kp) > 2 and kp[2] > 0.20)
                if valid_kps >= 4:
                    for track in tracks:
                        if track.category != "person" and bbox_iou(pose.bbox, track.bbox) > 0.20:
                            track.class_name = "person"
                            track.category = "person"
                    for det in detections:
                        if det.category != "person" and bbox_iou(pose.bbox, det.bbox) > 0.20:
                            det.class_name = "person"
                            det.category = "person"

        # Step 5: VIOLENCE CLASSIFICATION — Retrieved exclusively from async specialist cache
        violence_results = []
        viol_res = specialist_results.get("violence")
        if viol_res and viol_res.is_display_valid and viol_res.data:
            violence_results = viol_res.data

        # Calculate Primary AI presentation metrics
        elapsed = time.monotonic() - self._start_time
        ai_fps = self._ai_frame_count / elapsed if elapsed > 0 else 0.0
        processing_time = (time.monotonic() - start) * 1000.0  # ms

        analysis = FrameAnalysis(
            frame_number=current_fid,
            timestamp=c_time,
            detections=detections,
            tracks=tracks,
            poses=poses,
            violence_results=violence_results,
            specialist_telemetry=telemetry,
            ai_fps=round(ai_fps, 1),
            processing_time_ms=processing_time,
        )
        self._last_analysis = analysis
        return analysis

    def _process_frame_synchronous(self, frame: np.ndarray) -> Optional[FrameAnalysis]:
        """Synchronous pipeline mode for baseline benchmarking."""
        if self._frame_count % config.AI_PROCESS_EVERY_N_FRAMES != 0:
            return self._last_analysis

        start = time.time()
        self._ai_frame_count += 1
        self._pose_frame_counter += 1

        detections, tracks = self.tracker.update(frame, self.detector.model)

        self._fire_frame_counter += 1
        if self._fire_frame_counter % config.FIRE_DETECT_EVERY_N_AI_FRAMES == 0:
            raw_fire = self.detector.detect_fire(frame)
            fire_detections = self._update_fire_buffer(raw_fire)
            self._last_fire_detections = fire_detections
        else:
            fire_detections = self._last_fire_detections
        detections.extend(fire_detections)

        self._weapon_frame_counter += 1
        if self._weapon_frame_counter % config.WEAPON_DETECT_EVERY_N_AI_FRAMES == 0:
            weapon_detections = self.detector.detect_weapons(frame)
            self._last_weapon_detections = weapon_detections
        else:
            weapon_detections = self._last_weapon_detections
        detections.extend(weapon_detections)

        num_persons = len([t for t in tracks if t.category == "person" or ((t.bbox[3] - t.bbox[1]) > (t.bbox[2] - t.bbox[0]) * 1.1)])
        poses = self._run_pose_conditional(frame, num_persons)
        if poses and tracks:
            poses = self.pose_estimator.match_poses_to_tracks(poses, tracks)
            poses = self.pose_estimator.smooth_keypoints(poses)
            self._last_poses = poses

            # Semantic Pose-Guided Correction
            for pose in poses:
                valid_kps = sum(1 for kp in pose.keypoints if len(kp) > 2 and kp[2] > 0.20)
                if valid_kps >= 4:
                    for track in tracks:
                        if track.category != "person" and bbox_iou(pose.bbox, track.bbox) > 0.20:
                            track.class_name = "person"
                            track.category = "person"
                    for det in detections:
                        if det.category != "person" and bbox_iou(pose.bbox, det.bbox) > 0.20:
                            det.class_name = "person"
                            det.category = "person"
        elif not num_persons:
            self._last_poses = []
            self.pose_estimator.reset()
            poses = []
        elif self._last_poses:
            poses = self._last_poses

        violence_results = self._run_violence_classifier(frame, tracks, poses)

        elapsed = time.time() - self._start_time
        ai_fps = self._ai_frame_count / elapsed if elapsed > 0 else 0
        processing_time = (time.time() - start) * 1000.0

        analysis = FrameAnalysis(
            frame_number=self._frame_count,
            timestamp=time.time(),
            detections=detections,
            tracks=tracks,
            poses=poses,
            violence_results=violence_results,
            specialist_telemetry={},
            ai_fps=round(ai_fps, 1),
            processing_time_ms=round(processing_time, 1),
        )
        self._last_analysis = analysis
        return analysis

    def _run_pose_conditional(self, frame: np.ndarray, num_persons: int) -> List[PoseResult]:
        """
        Run pose estimation with a cooldown to save GPU.
        Only runs every N AI frames when persons are present.
        """
        if not config.POSE_ONLY_WHEN_PERSONS or num_persons == 0:
            self._last_poses = []
            return []

        # Cooldown: skip pose on intermediate frames
        if self._pose_frame_counter % self._pose_cooldown_frames != 0:
            return []  # Will reuse _last_poses

        return self.pose_estimator.estimate(frame, num_persons)

    def _run_violence_classifier(
        self, frame: np.ndarray, tracks: List[Track], poses: List[PoseResult]
    ) -> List[Dict[str, Any]]:
        """
        Neural fight verification (Day 2 — Rafay).
        Runs violence_classifier_best.pt on person crops that show aggressive
        pose indicators (arm raised above shoulder, wide arm spread).
        Only processes up to 3 persons per frame to limit GPU cost.
        """
        if self.detector.violence_model is None:
            return []

        results = []
        persons = [t for t in tracks if t.category == "person"]
        if not persons:
            return []

        # Identify aggressive-looking persons via pose analysis
        aggressive_bboxes = []
        for pose in poses:
            lw, rw = pose.left_wrist, pose.right_wrist
            ls, rs = pose.left_shoulder, pose.right_shoulder

            # Check for raised arms (fight indicator)
            is_aggressive = (
                (lw[2] > 0.3 and ls[2] > 0.3 and lw[1] < ls[1]) or
                (rw[2] > 0.3 and rs[2] > 0.3 and rw[1] < rs[1]) or
                pose.arm_spread > 150
            )
            if is_aggressive:
                aggressive_bboxes.append(pose.bbox)

        # Also check persons with high velocity (rushing)
        for p in persons:
            if p.avg_velocity > config.FIGHT_ARM_VELOCITY_THRESHOLD:
                aggressive_bboxes.append(p.bbox)

        # Also classify persons in close proximity (potential fighting even without pose/velocity signals)
        if len(persons) >= 2:
            for i, p1 in enumerate(persons):
                for p2 in persons[i+1:]:
                    dist = ((p1.center[0] - p2.center[0])**2 + (p1.center[1] - p2.center[1])**2)**0.5
                    if dist < config.FIGHT_PROXIMITY_THRESHOLD:
                        aggressive_bboxes.append(p1.bbox)
                        aggressive_bboxes.append(p2.bbox)

        # Deduplicate and limit crops (GPU budget from config)
        max_crops = config.VIOLENCE_MAX_CROPS_PER_FRAME
        seen = set()
        unique_bboxes = []
        for bbox in aggressive_bboxes:
            key = tuple(int(v / 20) * 20 for v in bbox)  # Bucket by 20px
            if key not in seen:
                seen.add(key)
                unique_bboxes.append(bbox)
            if len(unique_bboxes) >= max_crops:
                break

        # Run violence classifier in a single batched call
        if unique_bboxes:
            try:
                batch_results = self.detector.classify_violence_batch(frame, unique_bboxes)
                for result in batch_results:
                    if isinstance(result, dict) and result.get("available", False):
                        results.append(result)
            except Exception as e:
                # Fallback to per-crop calls if batch inference fails
                logger.debug("[VIOLENCE] Batch call failed (%s), falling back to per-crop", e)
                for bbox in unique_bboxes:
                    try:
                        result = self.detector.classify_violence(frame, bbox)
                        if isinstance(result, dict) and result.get("available", False):
                            results.append(result)
                    except Exception:
                        pass

        return results

    def get_tracker_summary(self) -> Dict:
        """Get current tracking summary."""
        return self.tracker.get_summary()

    def reset(self):
        """Full pipeline reset — clears tracker AND all stagger counters.

        Required between videos in batch mode so that fire/weapon cadence
        and cached detections from a previous video do not bleed into
        the next one.
        """
        # Tracker state
        self.tracker.reset()

        # Frame / timing counters
        self._frame_count = 0
        self._ai_frame_count = 0
        self._start_time = time.time()

        # Stagger counters (fire, weapon, pose)
        self._fire_frame_counter = 0
        self._weapon_frame_counter = 0
        self._pose_frame_counter = 0

        # Cached detection / pose state
        self._last_fire_detections = []
        self._last_weapon_detections = []
        self._last_poses = []
        self._fire_buffer = []
        self.pose_estimator.reset()

        # Last analysis result
        self._last_analysis = None

        if self.async_mode:
            self.specialist_worker.reset()

    def _update_fire_buffer(self, raw_detections: List[Detection]) -> List[Detection]:
        """
        Stabilize bounding box coordinates for fire and smoke across consecutive detections
        to prevent visual jitter on screen. Does not inject phantom detections when model sees nothing.
        """
        if not raw_detections:
            self._fire_buffer = []
            return []

        smoothed: List[Detection] = []
        for new_det in raw_detections:
            matched_old = None
            for old_det in self._fire_buffer:
                if old_det.category == new_det.category:
                    dx = abs(old_det.center[0] - new_det.center[0]) if old_det.center and new_det.center else 999
                    dy = abs(old_det.center[1] - new_det.center[1]) if old_det.center and new_det.center else 999
                    if dx < 80 and dy < 80:
                        matched_old = old_det
                        break

            if matched_old is not None:
                smooth_bbox = [
                    0.7 * new_det.bbox[k] + 0.3 * matched_old.bbox[k] for k in range(4)
                ]
                det = Detection(
                    bbox=smooth_bbox,
                    confidence=new_det.confidence,
                    class_id=new_det.class_id,
                    class_name=new_det.class_name,
                    category=new_det.category,
                )
                det.frame_percent = new_det.frame_percent
                smoothed.append(det)
            else:
                smoothed.append(new_det)

        self._fire_buffer = smoothed
        return smoothed

    def reset_tracks(self):
        """Reset all tracks (delegates to full reset for completeness)."""
        self.reset()

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def ai_frame_count(self) -> int:
        return self._ai_frame_count
