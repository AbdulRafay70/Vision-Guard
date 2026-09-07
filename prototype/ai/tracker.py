"""
VisionGuard — Object Tracker
Tracks detected objects across frames using ByteTrack-style tracking
via Ultralytics built-in tracker.
Assigns persistent VG-IDs to tracked objects.
"""
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time

from ai.detector import Detection, _categorize_class

import config

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """A tracked object with persistent ID and history."""
    track_id: int                    # Unique track ID
    vg_id: str                       # VisionGuard ID (e.g., "VG-001")
    class_name: str                  # person, car, etc.
    category: str                    # person, vehicle, object, fire, smoke
    confidence: float                # Latest detection confidence
    bbox: List[float]                # Latest [x1, y1, x2, y2]
    center: Tuple[float, float]      # Latest center point
    first_seen: float                # Timestamp when first detected
    last_seen: float                 # Timestamp of last detection
    is_active: bool = True           # Currently visible
    positions: deque = field(default_factory=lambda: deque(maxlen=config.MOTION_HISTORY_LENGTH))
    velocities: deque = field(default_factory=lambda: deque(maxlen=config.MOTION_HISTORY_LENGTH))

    @property
    def age_seconds(self) -> float:
        """How long this track has been alive."""
        return time.time() - self.first_seen

    @property
    def dwell_time(self) -> float:
        """How long this track has been visible."""
        return self.last_seen - self.first_seen

    @property
    def current_velocity(self) -> float:
        """Current speed in pixels/frame."""
        if len(self.velocities) > 0:
            return self.velocities[-1]
        return 0.0

    @property
    def avg_velocity(self) -> float:
        """Average speed over recent frames."""
        if len(self.velocities) == 0:
            return 0.0
        recent = list(self.velocities)[-config.VELOCITY_SMOOTHING:]
        return sum(recent) / len(recent)

    @property
    def is_stationary(self) -> bool:
        """Check if the object is essentially not moving."""
        return self.avg_velocity < config.VEHICLE_STOP_VELOCITY_THRESHOLD

    @property
    def total_displacement(self) -> float:
        """Total distance from first position to current position."""
        if len(self.positions) < 2:
            return 0.0
        first = self.positions[0]
        last = self.positions[-1]
        dx = last[0] - first[0]
        dy = last[1] - first[1]
        return (dx ** 2 + dy ** 2) ** 0.5


# Maximum seconds a lost track is kept before cleanup
_TRACK_MAX_INACTIVE_SECONDS = 3.0
# Maximum number of concurrent active tracks
_MAX_ACTIVE_TRACKS = 100


class ObjectTracker:
    """
    Manages tracked objects across frames.
    Uses Ultralytics built-in ByteTrack for association,
    then wraps results in our Track objects with VG-IDs.

    Performs detection + tracking in a SINGLE model.track() call
    to avoid redundant YOLO inference.
    """

    def __init__(self):
        self.tracks: Dict[int, Track] = {}  # track_id -> Track
        self._next_vg_id: int = 1
        self._id_map: Dict[int, str] = {}   # ultralytics_id -> vg_id

    def _get_vg_id(self, ultra_id: int) -> str:
        """Get or create a VG-ID for an Ultralytics track ID."""
        if ultra_id not in self._id_map:
            self._id_map[ultra_id] = f"VG-{self._next_vg_id:03d}"
            self._next_vg_id += 1
        return self._id_map[ultra_id]

    def update(self, frame: np.ndarray, model) -> Tuple[List[Detection], List["Track"]]:
        """
        Run detection AND tracking in a single model.track() call.
        This replaces the old two-pass approach (model.predict + model.track)
        and cuts inference time roughly in half.

        Args:
            frame: Current video frame
            model: The YOLO model instance (has .track() method)

        Returns:
            Tuple of (detections list, active tracks list)
        """
        now = time.time()
        h, w = frame.shape[:2]
        frame_area = h * w

        # Single YOLO pass: detection + ByteTrack association
        # FP16 half-precision enabled on CUDA for ~2x speedup (Rafay Day 1)
        results = model.track(
            frame,
            conf=config.DETECTION_CONF_THRESHOLD,
            iou=config.DETECTION_IOU_THRESHOLD,
            imgsz=config.DETECTION_IMG_SIZE,
            persist=True,  # Maintain tracks across frames
            tracker="bytetrack.yaml",
            verbose=False,
            device=config.DETECTION_DEVICE,
            half=config.USE_FP16,  # FP16 half-precision GPU inference
        )

        detections = []
        current_ids = set()

        for result in results:
            if result.boxes is None or result.boxes.id is None:
                continue

            for i, box in enumerate(result.boxes):
                ultra_id = int(box.id[0])
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                center = ((x1 + x2) / 2, (y1 + y2) / 2)

                # Only track classes we care about
                if class_id not in config.COCO_CLASSES_OF_INTEREST:
                    continue

                class_name = config.COCO_CLASSES_OF_INTEREST[class_id]

                # Aspect-ratio sanity check: Vehicles (car/truck/bus) are wide/horizontal.
                # A tall vertical box (H > 1.35*W) with human-like height is a person in bulky gear (e.g. firefighter/SCBA).
                box_w = max(1.0, x2 - x1)
                box_h = max(1.0, y2 - y1)
                if class_name in ("car", "truck", "bus") and (box_h / box_w) > 1.35:
                    class_name = "person"
                    class_id = 0

                category = _categorize_class(class_name)

                # Build Detection object (for event detectors + display)
                det = Detection(
                    bbox=[x1, y1, x2, y2],
                    confidence=confidence,
                    class_id=class_id,
                    class_name=class_name,
                    category=category,
                )
                det.frame_percent = (det.area / frame_area) * 100
                detections.append(det)

                # Update tracking state
                vg_id = self._get_vg_id(ultra_id)
                current_ids.add(ultra_id)

                if ultra_id in self.tracks:
                    # Update existing track
                    track = self.tracks[ultra_id]
                    track.class_name = class_name
                    track.category = category
                    track.confidence = confidence
                    track.bbox = [x1, y1, x2, y2]

                    # Calculate velocity
                    if len(track.positions) > 0:
                        prev = track.positions[-1]
                        dx = center[0] - prev[0]
                        dy = center[1] - prev[1]
                        velocity = (dx ** 2 + dy ** 2) ** 0.5
                        track.velocities.append(velocity)

                    track.center = center
                    track.positions.append(center)
                    track.last_seen = now
                    track.is_active = True
                else:
                    # Enforce max active tracks cap
                    active_count = sum(1 for t in self.tracks.values() if t.is_active)
                    if active_count >= _MAX_ACTIVE_TRACKS:
                        continue

                    # Create new track
                    track = Track(
                        track_id=ultra_id,
                        vg_id=vg_id,
                        class_name=class_name,
                        category=category,
                        confidence=confidence,
                        bbox=[x1, y1, x2, y2],
                        center=center,
                        first_seen=now,
                        last_seen=now,
                        is_active=True,
                        positions=deque([center], maxlen=config.MOTION_HISTORY_LENGTH),
                        velocities=deque([], maxlen=config.MOTION_HISTORY_LENGTH),
                    )
                    self.tracks[ultra_id] = track

        # Mark tracks not seen in this frame as inactive
        for tid, track in self.tracks.items():
            if tid not in current_ids:
                track.is_active = False

        # Clean up inactive tracks (reduced from 5s to 3s for better memory)
        to_remove = [
            tid for tid, track in self.tracks.items()
            if not track.is_active and (now - track.last_seen) > _TRACK_MAX_INACTIVE_SECONDS
        ]
        for tid in to_remove:
            vg_id = self.tracks[tid].vg_id
            del self.tracks[tid]
            self._id_map.pop(tid, None)
            logger.debug("[TRACKER] Cleaned up inactive track %s (%s)", vg_id, tid)

        return detections, self.get_active_tracks()

    def get_active_tracks(self) -> List[Track]:
        """Get all currently active tracks."""
        return [t for t in self.tracks.values() if t.is_active]

    def get_person_tracks(self) -> List[Track]:
        """Get active person tracks."""
        return [t for t in self.get_active_tracks() if t.category == "person"]

    def get_vehicle_tracks(self) -> List[Track]:
        """Get active vehicle tracks."""
        return [t for t in self.get_active_tracks() if t.category == "vehicle"]

    def get_object_tracks(self) -> List[Track]:
        """Get active object tracks."""
        return [t for t in self.get_active_tracks() if t.category == "object"]

    def get_track_by_vg_id(self, vg_id: str) -> Optional[Track]:
        """Find a track by its VG-ID."""
        for track in self.tracks.values():
            if track.vg_id == vg_id:
                return track
        return None

    def get_summary(self) -> Dict:
        """Get a summary of current tracking state."""
        active = self.get_active_tracks()
        return {
            "total_active": len(active),
            "persons": len([t for t in active if t.category == "person"]),
            "vehicles": len([t for t in active if t.category == "vehicle"]),
            "objects": len([t for t in active if t.category == "object"]),
            "total_ever": self._next_vg_id - 1,
        }

    def reset(self):
        """Clear all tracks."""
        self.tracks.clear()
        self._id_map.clear()
        self._next_vg_id = 1
        logger.info("[TRACKER] All tracks reset.")
