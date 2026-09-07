"""
VisionGuard — Evidence Package Generator
Generates tamper-proof legal-ready evidence packages with SHA-256 hashes.
Supports both screenshot and video clip evidence.
"""
import hashlib
import json
import logging
import time
import cv2
import numpy as np
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from threading import Thread

from events.base import EventAlert
import config

logger = logging.getLogger(__name__)

# Number of seconds of pre-event video to keep in the rolling buffer
_CLIP_PRE_SECONDS = 5
# Number of seconds of post-event video to capture after alert
_CLIP_POST_SECONDS = 3
# Assumed FPS for buffer size calculation
_BUFFER_FPS = 15


class FrameBuffer:
    """
    Rolling frame buffer that keeps the last N seconds of video frames.
    Used to create video clips when events are detected.
    """

    def __init__(self, max_seconds: float = _CLIP_PRE_SECONDS, fps: float = _BUFFER_FPS):
        self._max_frames = int(max_seconds * fps)
        self._buffer: deque = deque(maxlen=self._max_frames)
        self._fps = fps

    def push(self, frame: np.ndarray):
        """Add a frame to the rolling buffer."""
        self._buffer.append(frame.copy())

    def dump(self) -> List[np.ndarray]:
        """Return all buffered frames in chronological order."""
        return list(self._buffer)

    def clear(self):
        self._buffer.clear()

    @property
    def size(self) -> int:
        return len(self._buffer)


class EvidencePackageGenerator:
    """
    Creates tamper-proof evidence packages for confirmed emergency events.
    Supports both screenshot and video clip evidence.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or config.EVIDENCE_DIR
        self.output_dir.mkdir(exist_ok=True)
        self._frame_buffer = FrameBuffer()
        # Track active clip recordings: event_type -> (VideoWriter, post_frames_left)
        self._active_clips: Dict[str, dict] = {}

    def push_frame(self, frame: np.ndarray):
        """
        Push a frame into the rolling buffer.
        Call this on every processed frame (before event detection).
        """
        self._frame_buffer.push(frame)
        # Also write to any active post-event clips
        self._write_to_active_clips(frame)

    def create_package(self, frame: np.ndarray, alert: EventAlert) -> Dict[str, Any]:
        """
        Takes an emergency frame and alert object, saves screenshot,
        calculates SHA-256 hash, and saves structured evidence manifest.
        Also triggers video clip creation from the rolling buffer.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_id = f"VG-EVID-{alert.event_type.upper()}-{timestamp_str}"

        # 1. Save Image Evidence
        img_filename = f"{package_id}.jpg"
        img_path = self.output_dir / img_filename
        cv2.imwrite(str(img_path), frame)

        # 2. Compute SHA-256 Digital Fingerprint
        with open(img_path, "rb") as f:
            file_bytes = f.read()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # 3. Create video clip from buffer (pre-event + post-event)
        clip_filename = f"{package_id}.mp4"
        clip_path = self._create_clip(alert, clip_filename, frame)

        # 4. Create Manifest Package Data
        package_manifest = {
            "evidence_package_id": package_id,
            "timestamp_iso": datetime.now().isoformat(),
            "event_type": alert.event_type,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "confidence": alert.confidence,
            "duration_seconds": alert.duration_seconds,
            "description": alert.description,
            "details": alert.details,
            "department_routed": {
                "name": alert.department,
                "dial": alert.dial,
                "priority": alert.priority,
                "action": alert.action
            },
            "evidence_files": {
                "screenshot": img_filename,
                "video_clip": clip_filename if clip_path else None,
            },
            "integrity": {
                "sha256_hash": sha256_hash,
                "image_filename": img_filename,
                "tamper_proof": True
            }
        }

        # 5. Save Manifest JSON
        json_filename = f"{package_id}.json"
        json_path = self.output_dir / json_filename
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(package_manifest, f, indent=2, ensure_ascii=False)

        logger.info("[EVIDENCE] Package Created: %s (SHA-256: %s...)",
                     package_id, sha256_hash[:16])

        return package_manifest

    def _create_clip(self, alert: EventAlert, clip_filename: str,
                     current_frame: np.ndarray) -> Optional[Path]:
        """
        Create a video clip from the rolling buffer (pre-event frames)
        plus the current frame and future post-event frames.
        """
        pre_frames = self._frame_buffer.dump()
        if not pre_frames:
            return None

        clip_path = self.output_dir / clip_filename
        h, w = current_frame.shape[:2]

        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(clip_path), fourcc, _BUFFER_FPS, (w, h))

            if not writer.isOpened():
                logger.warning("[EVIDENCE] Failed to create video writer for %s", clip_filename)
                return None

            # Write pre-event frames from buffer
            for f in pre_frames:
                resized = cv2.resize(f, (w, h)) if f.shape[:2] != (h, w) else f
                writer.write(resized)

            # Write the current trigger frame
            writer.write(current_frame)

            # Set up post-event capture
            post_frames_needed = int(_CLIP_POST_SECONDS * _BUFFER_FPS)
            self._active_clips[alert.event_type] = {
                "writer": writer,
                "path": clip_path,
                "post_frames_left": post_frames_needed,
                "frame_size": (w, h),
            }

            logger.info("[EVIDENCE] Clip started: %s (%d pre-event frames, "
                         "%d post-event frames to capture)",
                         clip_filename, len(pre_frames), post_frames_needed)
            return clip_path

        except Exception as e:
            logger.error("[EVIDENCE] Failed to create clip: %s", e)
            return None

    def _write_to_active_clips(self, frame: np.ndarray):
        """Write the current frame to any active post-event clip recordings."""
        finished = []
        for event_type, clip_info in self._active_clips.items():
            writer = clip_info["writer"]
            w, h = clip_info["frame_size"]

            try:
                resized = cv2.resize(frame, (w, h)) if frame.shape[:2] != (h, w) else frame
                writer.write(resized)
                clip_info["post_frames_left"] -= 1

                if clip_info["post_frames_left"] <= 0:
                    writer.release()
                    finished.append(event_type)
                    logger.info("[EVIDENCE] Clip completed: %s", clip_info["path"].name)
            except Exception as e:
                logger.error("[EVIDENCE] Clip write error: %s", e)
                writer.release()
                finished.append(event_type)

        for event_type in finished:
            self._active_clips.pop(event_type, None)
