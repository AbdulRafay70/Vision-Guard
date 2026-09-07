"""VisionGuard — Webcam Source
Captures frames from the laptop's webcam using OpenCV.
Uses async threaded frame buffering with a 2-slot circular buffer to
prevent stream lag. Stale frames are automatically dropped so the AI
pipeline always receives the most recent frame.
"""
import cv2
import logging
import time
import threading
import numpy as np
from collections import deque
from typing import Optional, Tuple

from camera.base import CameraSource
from camera.slot import LatestFrameSlot, TimestampedFrame

logger = logging.getLogger(__name__)


class WebcamSource(CameraSource):
    """
    Captures frames from the laptop webcam using a background daemon thread.
    Uses LatestFrameSlot (capacity=1) with true overwrite semantics:
    - Camera ingestion NEVER waits or blocks.
    - Stale frames are immediately replaced.
    - Displays and AI workers read the newest frame safely without mutation risk.
    """

    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None
        self.running: bool = False
        self.fps: float = 0.0

        # Latest frame slot (capacity = 1)
        self.slot = LatestFrameSlot(name=f"webcam-{camera_index}")
        self._thread: Optional[threading.Thread] = None
        self._frame_count: int = 0
        self._start_time: float = 0.0

    def start(self) -> bool:
        """Open the webcam and start capturing in a background daemon thread."""
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            logger.error("[WEBCAM] Cannot open webcam (index %d)", self.camera_index)
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info("[WEBCAM] Opened camera %d at %dx%d", self.camera_index, actual_w, actual_h)

        self.running = True
        self._start_time = time.monotonic()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True,
                                        name=f"webcam-{self.camera_index}-buffer")
        self._thread.start()
        logger.info("[WEBCAM] Non-blocking LatestFrameSlot capture thread started.")
        return True

    def _capture_loop(self):
        """
        Background daemon thread: continuously reads frames from webcam
        directly into the 1-capacity LatestFrameSlot.
        """
        while self.running:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.slot.put(frame)
                self._frame_count += 1
                elapsed = time.monotonic() - self._start_time
                if elapsed > 0:
                    self.fps = self._frame_count / elapsed
            else:
                time.sleep(0.005)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Return the latest frame from the slot."""
        tf = self.slot.get_latest_for_display()
        if tf is not None:
            return True, tf.frame
        return False, None

    def read_timestamped(self) -> Optional[TimestampedFrame]:
        """Return the newest TimestampedFrame containing capture_timestamp and frame_id."""
        return self.slot.get_latest_for_display()

    def get_fps(self) -> float:
        """Get current capture FPS."""
        return round(self.fps, 1)

    def get_frame_count(self) -> int:
        """Total frames captured."""
        return self._frame_count

    def get_dropped_count(self) -> int:
        """Total stale frames dropped by the slot."""
        return self.slot.get_stats().get("dropped_stale", 0)

    def is_opened(self) -> bool:
        """Check if webcam is still open and active."""
        return self.cap is not None and self.cap.isOpened() and self.running

    def stop(self):
        """Stop the webcam and release resources."""
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self.cap is not None:
            self.cap.release()
        logger.info("[WEBCAM] Camera released. Frames captured: %d, dropped: %d",
                    self._frame_count, self.get_dropped_count())

    @property
    def source_name(self) -> str:
        return f"Webcam-{self.camera_index}"

    @property
    def source_type(self) -> str:
        return "webcam"
