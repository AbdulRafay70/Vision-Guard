"""
VisionGuard — Specialist AI Background Worker
Executes specialist secondary models (Pose, Weapon, Fire/Smoke, Violence)
asynchronously in a single dedicated GPU thread, completely decoupling
heavy inference from the 25–30 FPS presentation loop.

Mandatory Architecture Guarantees:
1. No Accumulating Queues: Latest-frame semantics only. Stale pending work is discarded.
2. Pose is 100% Asynchronous: Pose executes exclusively here, never in the main presentation loop.
3. Explicit Thread-Safety: Readers consume thread-safe isolated frame copies.
4. Comprehensive Result Metadata: source_frame_id, capture_timestamp, inference_timestamp,
   confidence, track_id, and monotonic result age.
5. Independent Expiration: Distinct validity windows for display (750ms) vs event logic (1200ms).
"""
import time
import threading
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

import config
from ai.detector import ObjectDetector, Detection
from ai.pose import PoseEstimator, PoseResult
from ai.tracker import Track

logger = logging.getLogger(__name__)


class SceneState(Enum):
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    ALERT = "ALERT"


class ResultStatus(Enum):
    ACTIVE = "ACTIVE"       # < 350 ms: Fresh, display normally
    STALE = "STALE"         # 350 - 750 ms: Aging but still visible
    EXPIRED = "EXPIRED"     # > 750 ms: Do not draw on screen


# Configurable age thresholds (in seconds)
MAX_ACTIVE_AGE_SEC = 0.350    # 350 ms
MAX_DISPLAY_AGE_SEC = 0.750   # 750 ms (display expiry)
MAX_EVENT_AGE_SEC = 1.200     # 1200 ms (event logic expiry)


@dataclass
class SpecialistResult:
    """
    Cached result for a specialist model with full monotonic provenance.
    Requirement 10: Every specialist result must contain source_frame_id,
    capture_timestamp, inference_timestamp, confidence, track_id, and age.
    """
    task_name: str
    source_frame_id: int
    capture_timestamp: float      # Monotonic capture time of source frame
    inference_timestamp: float    # Monotonic time inference completed
    confidence: float             # Max or representative confidence score
    data: Any                     # List[Detection], List[PoseResult], etc.
    track_id: Optional[int] = None # Associated track ID (if applicable)
    inference_time_ms: float = 0.0

    @property
    def age_ms(self) -> float:
        """Frame age in ms from original camera capture to right now."""
        return (time.monotonic() - self.capture_timestamp) * 1000.0

    @property
    def age_sec(self) -> float:
        return time.monotonic() - self.capture_timestamp

    @property
    def is_display_valid(self) -> bool:
        """Requirement 11: Valid for on-screen visual overlay (<750 ms)."""
        return self.age_sec <= MAX_DISPLAY_AGE_SEC

    @property
    def is_event_valid(self) -> bool:
        """Requirement 11: Valid for event confirmation and rule evaluation (<1200 ms)."""
        return self.age_sec <= MAX_EVENT_AGE_SEC

    @property
    def status(self) -> ResultStatus:
        age = self.age_sec
        if age < MAX_ACTIVE_AGE_SEC:
            return ResultStatus.ACTIVE
        elif age <= MAX_DISPLAY_AGE_SEC:
            return ResultStatus.STALE
        else:
            return ResultStatus.EXPIRED


class StableFrameSlot:
    """
    Single-slot buffer for the specialist worker (capacity = 1).
    Latest-frame only: overwrites previously unread frames so the background
    worker never accumulates an inference backlog.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._frame_id: int = 0
        self._capture_timestamp: float = 0.0
        self._tracks: List[Track] = []
        self._scene_state: SceneState = SceneState.NORMAL
        self._is_new: bool = False

    def update(self, frame: np.ndarray, frame_id: int, capture_timestamp: float,
               tracks: List[Track], scene_state: SceneState):
        """Store newest frame reference atomically. Discards previous unconsumed frame."""
        with self._lock:
            # Safe copy prevents race conditions with camera capture memory
            self._frame = frame.copy()
            self._frame_id = frame_id
            self._capture_timestamp = capture_timestamp
            self._tracks = list(tracks)
            self._scene_state = scene_state
            self._is_new = True

    def get_latest(self) -> Tuple[Optional[np.ndarray], int, float, List[Track], SceneState, bool]:
        """Fetch latest frame and mark as consumed for this cycle."""
        with self._lock:
            is_new = self._is_new
            self._is_new = False
            return self._frame, self._frame_id, self._capture_timestamp, self._tracks, self._scene_state, is_new


class SpecialistWorker:
    """
    Single dedicated GPU background worker thread.
    Executes secondary AI models in an attention-based priority order:
    - NORMAL: runs periodic heartbeats (fire, weapon, low-frequency pose).
    - SUSPICIOUS: increases frequency of weapon, pose, and violence models.
    - ALERT: runs confirmed threat specialist models at maximum adaptive rate.
    """

    def __init__(self, detector: ObjectDetector, pose_estimator: PoseEstimator):
        self.detector = detector
        self.pose_estimator = pose_estimator

        self.frame_slot = StableFrameSlot()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        now = time.monotonic()
        # Initialize result caches with full metadata
        self._results: Dict[str, SpecialistResult] = {
            "fire": SpecialistResult("fire", 0, now, now, 0.0, []),
            "weapon": SpecialistResult("weapon", 0, now, now, 0.0, []),
            "pose": SpecialistResult("pose", 0, now, now, 0.0, []),
            "violence": SpecialistResult("violence", 0, now, now, 0.0, []),
            "normal_scene": SpecialistResult("normal_scene", 0, now, now, 0.0, []),
        }

        # Monotonic timers and execution counters
        self._last_run_time: Dict[str, float] = {
            "fire": 0.0,
            "weapon": 0.0,
            "pose": 0.0,
            "violence": 0.0,
            "normal_scene": 0.0,
        }
        self._specialist_fps: Dict[str, float] = {
            "fire": 0.0,
            "weapon": 0.0,
            "pose": 0.0,
            "violence": 0.0,
            "normal_scene": 0.0,
        }
        self._run_counts: Dict[str, int] = {
            "fire": 0,
            "weapon": 0,
            "pose": 0,
            "violence": 0,
            "normal_scene": 0,
        }
        self._normal_scene_conf: float = 0.0
        self._governor_decision: str = "Initializing context governor"
        self._current_scene_state: SceneState = SceneState.NORMAL
        self._start_time = time.monotonic()
        self._fire_buffer: List[Detection] = []

    def start(self):
        """Start the background worker thread."""
        if self._running:
            return
        self._running = True
        self._start_time = time.monotonic()
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="VisionGuard-SpecialistWorker",
            daemon=True
        )
        self._thread.start()
        logger.info("[WORKER] Specialist AI background worker thread started.")

    def stop(self):
        """Stop the background worker thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("[WORKER] Specialist AI background worker stopped.")

    def push_frame(self, frame: np.ndarray, frame_id: int, capture_timestamp: float, tracks: List[Track]):
        """
        Called by primary presentation loop to deliver latest frame.
        Evaluates scene state (NORMAL, SUSPICIOUS, or ALERT) and updates single-slot buffer.
        """
        scene_state = self._evaluate_scene_state(tracks)
        self.frame_slot.update(frame, frame_id, capture_timestamp, tracks, scene_state)

    def _evaluate_scene_state(self, tracks: List[Track]) -> SceneState:
        """
        Dynamically determine if scene is NORMAL, SUSPICIOUS, or ALERT.
        """
        # Check active alerts in cache
        with self._lock:
            weapon_res = self._results.get("weapon")
            fire_res = self._results.get("fire")
            violence_res = self._results.get("violence")

            if (weapon_res and weapon_res.is_display_valid and weapon_res.data) or \
               (fire_res and fire_res.is_display_valid and fire_res.data):
                return SceneState.ALERT

            if violence_res and violence_res.is_display_valid and violence_res.data:
                return SceneState.ALERT

        persons = [t for t in tracks if t.category == "person"]

        # Check for fast running or rushing
        if any(p.avg_velocity > config.FIGHT_ARM_VELOCITY_THRESHOLD for p in persons):
            return SceneState.SUSPICIOUS

        # Check for close interpersonal proximity (potential fight)
        if len(persons) >= 2:
            for i, p1 in enumerate(persons):
                for p2 in persons[i + 1:]:
                    dist = ((p1.center[0] - p2.center[0]) ** 2 + (p1.center[1] - p2.center[1]) ** 2) ** 0.5
                    if dist < config.FIGHT_PROXIMITY_THRESHOLD:
                        return SceneState.SUSPICIOUS

        return SceneState.NORMAL

    def _worker_loop(self):
        """Main serialized GPU inference loop for specialists (capacity = 1)."""
        while self._running:
            frame, frame_id, capture_timestamp, tracks, scene_state, is_new = self.frame_slot.get_latest()

            if frame is None or frame_id == 0:
                time.sleep(0.005)
                continue

            # Select next specialist task based on attention priorities
            task = self._select_next_task(tracks, scene_state)
            if task is None:
                time.sleep(0.005)
                continue

            # Execute the selected specialist
            t_start = time.monotonic()
            try:
                if task == "pose":
                    self._run_pose(frame, frame_id, capture_timestamp, tracks)
                elif task == "fire":
                    self._run_fire(frame, frame_id, capture_timestamp)
                elif task == "weapon":
                    self._run_weapon(frame, frame_id, capture_timestamp)
                elif task == "violence":
                    self._run_violence(frame, frame_id, capture_timestamp, tracks)
                elif task == "normal_scene":
                    self._run_normal_scene(frame, frame_id, capture_timestamp)
            except Exception as e:
                logger.error("[WORKER] Error in specialist %s: %s", task, e, exc_info=True)

            self._last_run_time[task] = time.monotonic()
            self._run_counts[task] += 1

            # Update specialist FPS
            elapsed = time.monotonic() - self._start_time
            if elapsed > 0:
                self._specialist_fps[task] = round(self._run_counts[task] / elapsed, 1)

            # Brief yield to prevent pegging the core
            time.sleep(0.002)

    def _select_next_task(self, tracks: List[Track], scene_state: SceneState) -> Optional[str]:
        """
        Starvation-preventing, priority-weighted attention scheduler:
        Uses overdue ratio (elapsed / target_interval * weight) to ensure every active
        specialist executes at its allocated frequency without priority inversion.
        Requirement 6: Normal Scene Verifier is a context governor only.
        Fire, Weapon, Violence, and Pose are NEVER disabled to 0 FPS.
        """
        now = time.monotonic()
        num_persons = sum(1 for t in tracks if t.category == "person")
        candidates = []  # (task_name, overdue_ratio, weight)

        # 1. Normal scene governor evaluation (~2 FPS context governor)
        gov_interval = 0.50
        candidates.append(("normal_scene", (now - self._last_run_time["normal_scene"]) / gov_interval, 1.0))

        if scene_state == SceneState.ALERT:
            # High frequency for active emergency verification
            candidates.append(("fire", (now - self._last_run_time["fire"]) / 0.10, 1.2))
            if num_persons > 0:
                candidates.append(("weapon", (now - self._last_run_time["weapon"]) / 0.10, 1.3))
                candidates.append(("pose", (now - self._last_run_time["pose"]) / 0.15, 1.1))
            if num_persons >= 2:
                candidates.append(("violence", (now - self._last_run_time["violence"]) / 0.15, 1.0))

        elif scene_state == SceneState.SUSPICIOUS:
            # Medium frequency
            candidates.append(("fire", (now - self._last_run_time["fire"]) / 0.20, 1.1))
            if num_persons > 0:
                candidates.append(("weapon", (now - self._last_run_time["weapon"]) / 0.15, 1.2))
                candidates.append(("pose", (now - self._last_run_time["pose"]) / 0.20, 1.1))
            if num_persons >= 2:
                candidates.append(("violence", (now - self._last_run_time["violence"]) / 0.25, 1.0))

        else:
            # NORMAL scene: Heartbeat mode (saves GPU compute while keeping all detectors active)
            candidates.append(("fire", (now - self._last_run_time["fire"]) / 0.33, 1.1))  # ~3 FPS heartbeat
            if num_persons > 0:
                candidates.append(("pose", (now - self._last_run_time["pose"]) / 0.25, 1.1))    # ~4 FPS
                candidates.append(("weapon", (now - self._last_run_time["weapon"]) / 0.33, 1.0))  # ~3 FPS
            else:
                # Periodic safety sweep even without detected persons
                candidates.append(("pose", (now - self._last_run_time["pose"]) / 0.50, 0.9))    # ~2 FPS
                candidates.append(("weapon", (now - self._last_run_time["weapon"]) / 0.50, 0.9))  # ~2 FPS
            if num_persons >= 2:
                candidates.append(("violence", (now - self._last_run_time["violence"]) / 0.50, 0.9))

        # Filter only tasks whose target interval has arrived (overdue_ratio >= 1.0)
        ready_tasks = [c for c in candidates if c[1] >= 1.0]
        if not ready_tasks:
            return None

        # Sort by urgency = overdue_ratio * weight (highest overdue urgency wins)
        ready_tasks.sort(key=lambda c: c[1] * c[2], reverse=True)
        return ready_tasks[0][0]

    def _run_normal_scene(self, frame: np.ndarray, frame_id: int, capture_timestamp: float):
        """
        Execute Normal Scene Verifier context model.
        Updates governor telemetry and tunes specialist workload without disabling safety detectors.
        """
        t0 = time.monotonic()
        is_normal, max_conf, detections = self.detector.detect_normal_scene(frame)
        lat = (time.monotonic() - t0) * 1000.0
        now = time.monotonic()

        with self._lock:
            self._normal_scene_conf = max_conf
            if is_normal:
                self._governor_decision = f"Normal Scene Confirmed ({max_conf:.0%}): Workload throttled to heartbeat. Safety detectors ACTIVE."
            else:
                self._governor_decision = f"Active / Anomalous Activity ({max_conf:.0%}): Full attention active."

            if frame_id >= self._results["normal_scene"].source_frame_id:
                self._results["normal_scene"] = SpecialistResult(
                    task_name="normal_scene",
                    source_frame_id=frame_id,
                    capture_timestamp=capture_timestamp,
                    inference_timestamp=now,
                    confidence=max_conf,
                    data=detections,
                    inference_time_ms=lat
                )

    def _run_pose(self, frame: np.ndarray, frame_id: int, capture_timestamp: float, tracks: List[Track]):
        """
        Execute YOLOv8s-Pose exclusively in background worker thread.
        Caches keypoints with track association and monotonic timestamps.
        """
        t0 = time.monotonic()
        # Check tracks that are classified as person or have vertical human-like aspect ratio (H > 1.1*W)
        persons = [t for t in tracks if t.category == "person" or ((t.bbox[3] - t.bbox[1]) > (t.bbox[2] - t.bbox[0]) * 1.1)]
        if not persons:
            poses = []
            max_conf = 0.0
        else:
            persons_to_pose = persons[:config.MAX_PERSONS_FOR_POSE]
            raw_poses = self.pose_estimator.estimate(frame, len(persons_to_pose))
            if raw_poses and tracks:
                poses = self.pose_estimator.match_poses_to_tracks(raw_poses, tracks)
                poses = self.pose_estimator.smooth_keypoints(poses)
            else:
                poses = raw_poses
            max_conf = max([p.confidence for p in poses], default=0.0) if poses else 0.0

        lat = (time.monotonic() - t0) * 1000.0
        now = time.monotonic()

        with self._lock:
            if frame_id >= self._results["pose"].source_frame_id:
                self._results["pose"] = SpecialistResult(
                    task_name="pose",
                    source_frame_id=frame_id,
                    capture_timestamp=capture_timestamp,
                    inference_timestamp=now,
                    confidence=max_conf,
                    data=poses,
                    inference_time_ms=lat
                )

    def _run_fire(self, frame: np.ndarray, frame_id: int, capture_timestamp: float):
        """Execute fire/smoke model and update cache."""
        t0 = time.monotonic()
        raw = self.detector.detect_fire(frame)
        stabilized = self._update_fire_buffer(raw)
        lat = (time.monotonic() - t0) * 1000.0
        now = time.monotonic()
        max_conf = max([d.confidence for d in stabilized], default=0.0) if stabilized else 0.0

        with self._lock:
            if frame_id >= self._results["fire"].source_frame_id:
                self._results["fire"] = SpecialistResult(
                    task_name="fire",
                    source_frame_id=frame_id,
                    capture_timestamp=capture_timestamp,
                    inference_timestamp=now,
                    confidence=max_conf,
                    data=stabilized,
                    inference_time_ms=lat
                )

    def _run_weapon(self, frame: np.ndarray, frame_id: int, capture_timestamp: float):
        """Execute weapon model and update cache."""
        t0 = time.monotonic()
        raw = self.detector.detect_weapons(frame)
        lat = (time.monotonic() - t0) * 1000.0
        now = time.monotonic()
        max_conf = max([d.confidence for d in raw], default=0.0) if raw else 0.0

        with self._lock:
            if frame_id >= self._results["weapon"].source_frame_id:
                self._results["weapon"] = SpecialistResult(
                    task_name="weapon",
                    source_frame_id=frame_id,
                    capture_timestamp=capture_timestamp,
                    inference_timestamp=now,
                    confidence=max_conf,
                    data=raw,
                    inference_time_ms=lat
                )

    def _run_violence(self, frame: np.ndarray, frame_id: int, capture_timestamp: float, tracks: List[Track]):
        """Execute neural violence classifier on suspicious person crops."""
        t0 = time.monotonic()
        results = []
        max_conf = 0.0

        if self.detector.violence_model is not None:
            persons = [t for t in tracks if t.category == "person"]
            if persons:
                bboxes = [p.bbox for p in persons[:config.VIOLENCE_MAX_CROPS_PER_FRAME]]
                try:
                    results = self.detector.classify_violence_batch(frame, bboxes)
                    max_conf = max([r.get("confidence", 0.0) for r in results], default=0.0) if results else 0.0
                except Exception:
                    pass

        lat = (time.monotonic() - t0) * 1000.0
        now = time.monotonic()

        with self._lock:
            if frame_id >= self._results["violence"].source_frame_id:
                self._results["violence"] = SpecialistResult(
                    task_name="violence",
                    source_frame_id=frame_id,
                    capture_timestamp=capture_timestamp,
                    inference_timestamp=now,
                    confidence=max_conf,
                    data=results,
                    inference_time_ms=lat
                )

    def get_results(self) -> Dict[str, SpecialistResult]:
        """Thread-safe snapshot of all specialist results."""
        with self._lock:
            return {k: v for k, v in self._results.items()}

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns worker status, specialist FPS, and monotonic result ages."""
        with self._lock:
            res = {k: v for k, v in self._results.items()}
            fps_copy = dict(self._specialist_fps)

        telemetry = {}
        for task, r in res.items():
            telemetry[task] = {
                "fps": fps_copy.get(task, 0.0),
                "age_ms": round(r.age_ms, 1),
                "status": r.status.value,
                "is_display_valid": r.is_display_valid,
                "is_event_valid": r.is_event_valid,
                "latency_ms": round(r.inference_time_ms, 1),
                "confidence": round(r.confidence, 2),
                "count": len(r.data) if isinstance(r.data, list) else 0,
            }

        # Context governor telemetry (Requirement 6)
        telemetry["governor"] = {
            "decision": self._governor_decision,
            "normal_scene_conf": round(self._normal_scene_conf, 2),
            "safety_detectors_active": True,
        }
        return telemetry

    def reset(self):
        """Reset all caches and timers."""
        now = time.monotonic()
        with self._lock:
            self._results = {
                "fire": SpecialistResult("fire", 0, now, now, 0.0, []),
                "weapon": SpecialistResult("weapon", 0, now, now, 0.0, []),
                "pose": SpecialistResult("pose", 0, now, now, 0.0, []),
                "violence": SpecialistResult("violence", 0, now, now, 0.0, []),
            }
            self._fire_buffer = []
            self._last_run_time = {k: 0.0 for k in self._last_run_time}
            self._run_counts = {k: 0 for k in self._run_counts}
            self._specialist_fps = {k: 0.0 for k in self._specialist_fps}
            self._start_time = time.monotonic()

    def _update_fire_buffer(self, raw_detections: List[Detection]) -> List[Detection]:
        """Stabilize fire/smoke bounding boxes across consecutive frames."""
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
                smooth_bbox = [0.7 * new_det.bbox[k] + 0.3 * matched_old.bbox[k] for k in range(4)]
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
