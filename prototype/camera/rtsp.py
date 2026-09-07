"""
VisionGuard — RTSP Camera Source
Captures live RTSP video streams from IP cameras (Hikvision, Dahua, Uniview, Axis)
running over PoE Cat6 Ethernet. Includes auto-reconnect with exponential backoff.
"""
import cv2
import logging
import time
import threading
import numpy as np
from typing import Optional, Tuple

from camera.base import CameraSource
from camera.slot import LatestFrameSlot, TimestampedFrame

logger = logging.getLogger(__name__)


class RTSPSource(CameraSource):
    """
    RTSP stream reader for IP security cameras over PoE.
    Features:
    - Non-blocking background thread with LatestFrameSlot (capacity=1)
    - True overwrite semantics: zero network accumulation lag
    - Auto-reconnection with exponential backoff (5s → 10s → 30s → 60s cap)
    - Low-latency buffer configuration
    - Health status reporting
    """

    def __init__(self, rtsp_url: str, camera_name: str = "IP Camera",
                 width: int = 1280, height: int = 720):
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name
        self.width = width
        self.height = height

        self.cap: Optional[cv2.VideoCapture] = None
        self.running: bool = False
        self.connected: bool = False
        self.fps: float = 0.0

        # Latest frame slot (capacity = 1)
        self.slot = LatestFrameSlot(name=f"rtsp-{camera_name}")
        self._thread: Optional[threading.Thread] = None
        self._frame_count: int = 0
        self._start_time: float = 0.0

        # Exponential backoff for reconnection
        self._reconnect_base: float = 5.0
        self._reconnect_max: float = 60.0
        self._reconnect_current: float = self._reconnect_base
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 50

        # Health status
        self.last_error: str = ""
        self.is_healthy: bool = False

    def start(self) -> bool:
        """Start the background RTSP capture thread."""
        self.running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def _open_camera(self) -> bool:
        """Internal helper to establish RTSP connection."""
        if self.cap is not None:
            self.cap.release()

        logger.info("[RTSP] Connecting to %s (%s)...", self.camera_name, self.rtsp_url)
        # Force FFMPEG backend for RTSP streams
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)

        if not self.cap.isOpened():
            self._reconnect_attempts += 1
            self.last_error = f"Connection failed (attempt {self._reconnect_attempts})"
            self.is_healthy = False
            logger.warning("[RTSP] Failed to connect to %s (attempt %d)",
                           self.camera_name, self._reconnect_attempts)
            return False

        # Set low buffer size to minimize latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.connected = True
        self.is_healthy = True
        self._reconnect_current = self._reconnect_base  # Reset backoff on success
        self._reconnect_attempts = 0
        logger.info("[RTSP] Connected to %s", self.camera_name)
        return True

    def _capture_loop(self):
        """Continuously grab frames & handle reconnects with exponential backoff."""
        consecutive_failures = 0

        while self.running:
            if not self.connected:
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    logger.error("[RTSP] Max reconnection attempts reached for %s. "
                                 "Giving up.", self.camera_name)
                    self.is_healthy = False
                    time.sleep(30)  # Long wait before final retry cycle
                    self._reconnect_attempts = 0  # Reset for retry cycle

                if not self._open_camera():
                    # Exponential backoff: 5s → 10s → 20s → 40s → 60s (cap)
                    logger.info("[RTSP] Retrying %s in %.0fs...",
                                self.camera_name, self._reconnect_current)
                    time.sleep(self._reconnect_current)
                    self._reconnect_current = min(
                        self._reconnect_current * 2, self._reconnect_max
                    )
                    continue

            ret, frame = self.cap.read()

            if ret and frame is not None:
                consecutive_failures = 0
                if self.width > 0 and self.height > 0:
                    out_frame = cv2.resize(frame, (self.width, self.height))
                else:
                    out_frame = frame
                self.slot.put(out_frame)
                self._frame_count += 1

                elapsed = time.monotonic() - self._start_time
                if elapsed > 0:
                    self.fps = self._frame_count / elapsed
            else:
                consecutive_failures += 1
                if consecutive_failures > 30:  # ~1 sec of failures
                    logger.warning("[RTSP] Stream lost from %s. Reconnecting...",
                                   self.camera_name)
                    self.connected = False
                    self.is_healthy = False
                    self.last_error = "Stream lost"
                time.sleep(0.02)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Get the latest frame from the RTSP camera."""
        tf = self.slot.get_latest_for_display()
        if tf is not None:
            return True, tf.frame
        return False, None

    def read_timestamped(self) -> Optional[TimestampedFrame]:
        """Get the newest TimestampedFrame containing capture_timestamp and frame_id."""
        return self.slot.get_latest_for_display()

    def get_fps(self) -> float:
        return round(self.fps, 1)

    def get_health(self) -> dict:
        """Return health status for monitoring."""
        return {
            "camera": self.camera_name,
            "connected": self.connected,
            "healthy": self.is_healthy,
            "fps": self.get_fps(),
            "reconnect_attempts": self._reconnect_attempts,
            "last_error": self.last_error,
        }

    def stop(self):
        """Stop capture thread and release connection."""
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self.cap is not None:
            self.cap.release()
        logger.info("[RTSP] %s released.", self.camera_name)

    @property
    def source_name(self) -> str:
        return self.camera_name

    @property
    def source_type(self) -> str:
        return "rtsp"
