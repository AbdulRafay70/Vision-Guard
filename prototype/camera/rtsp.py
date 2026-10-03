"""
VisionGuard — Network Camera Source (RTSP / HTTP-MJPEG)
Captures live streams from IP cameras, WiFi cameras and DVR/NVR channels
(Hikvision, Dahua/CP Plus, Uniview, XMeye, Tapo, Ezviz, V380, …).

Reliability features:
- RTSP over TCP first (no packet loss on WiFi), automatic fall back to UDP
- Open / read timeouts so a dead host never blocks the thread
- Stall watchdog: no new frame for STALL_SECONDS → reconnect
- Exponential backoff 2s → 4s → … → 30s, retries forever while running
- Clear failure diagnosis (wrong password / wrong path / unreachable) via an
  RTSP DESCRIBE handshake, exposed through get_health()
"""
import logging
import os
import threading
import time
from collections import deque
from typing import Optional, Tuple

import cv2
import numpy as np

from camera.base import CameraSource
from camera.slot import LatestFrameSlot, TimestampedFrame

logger = logging.getLogger(__name__)

OPEN_TIMEOUT_MS = 8000
READ_TIMEOUT_MS = 8000
STALL_SECONDS = 10.0
_ffmpeg_env_lock = threading.Lock()


class RTSPSource(CameraSource):
    """Background-thread network stream reader with self-healing reconnects."""

    def __init__(self, rtsp_url: str, camera_name: str = "IP Camera",
                 width: int = 1280, height: int = 720, transport: str = "auto"):
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name
        self.max_width = width          # frames wider than this are scaled down (aspect preserved)
        self.transport = transport      # "auto" | "tcp" | "udp"

        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.connected = False
        self.fps = 0.0

        self.slot = LatestFrameSlot(name=f"rtsp-{camera_name}")
        self._thread: Optional[threading.Thread] = None
        self._frame_times: deque = deque(maxlen=60)
        self._last_frame_at = 0.0

        self._backoff = 2.0
        self._backoff_max = 30.0
        self._failures = 0
        self._active_transport = ""

        self.state = "connecting"       # connecting | online | reconnecting | error
        self.last_error = ""
        self.is_healthy = False
        self.resolution: Tuple[int, int] = (0, 0)

    # ── lifecycle ──────────────────────────────────────────────────────
    def start(self) -> bool:
        """Start the capture thread and wait briefly for the first frame.

        Returns True when the first frame arrives within the open timeout.
        Returns False on a definite failure (unreachable / wrong credentials);
        the thread keeps retrying in the background either way until stop().
        """
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name=f"rtsp-{self.camera_name}")
        self._thread.start()
        deadline = time.monotonic() + (OPEN_TIMEOUT_MS / 1000.0) + 4
        while time.monotonic() < deadline:
            if self._last_frame_at:
                return True
            if self.state == "error" and self._failures >= 1:
                return False
            time.sleep(0.1)
        return bool(self._last_frame_at)

    def stop(self):
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.connected = False
        logger.info("[RTSP] %s released.", self.camera_name)

    # ── connection ─────────────────────────────────────────────────────
    def _transports(self):
        if not self.rtsp_url.lower().startswith("rtsp"):
            return [""]
        if self.transport in ("tcp", "udp"):
            return [self.transport]
        # Alternate TCP / UDP across failed attempts, TCP first
        return ["tcp", "udp"] if self._failures % 4 < 2 else ["udp", "tcp"]

    def _open(self, transport: str) -> bool:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        opts = "stimeout;5000000|timeout;5000000"
        if transport:
            opts = f"rtsp_transport;{transport}|" + opts
        params = []
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            params = [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, OPEN_TIMEOUT_MS, cv2.CAP_PROP_READ_TIMEOUT_MSEC, READ_TIMEOUT_MS]
        with _ffmpeg_env_lock:  # FFmpeg options are read from the environment at open time
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = opts
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG, params) if params else cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap.release()
            return False
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap = cap
        self._active_transport = transport or "http"
        return True

    def _diagnose(self) -> str:
        """Explain a failed open using an RTSP handshake (fast, no decoding)."""
        if not self.rtsp_url.lower().startswith("rtsp"):
            return "Could not open the HTTP stream"
        try:
            from camera.discovery import rtsp_describe
            code, info = rtsp_describe(self.rtsp_url)
        except Exception as e:  # pragma: no cover
            return f"Connection failed ({e})"
        if code == 401:
            return "Wrong username or password"
        if code in (404, 400):
            return "Stream path not found on the device (wrong channel or URL)"
        if code == 0:
            return f"Device unreachable ({info or 'no answer'})"
        if code == 200:
            return "Device answered but no video was decoded (codec or bandwidth issue)"
        return f"Device returned RTSP {code}"

    def _capture_loop(self):
        while self.running:
            if not self.connected:
                self.state = "connecting" if not self._last_frame_at else "reconnecting"
                opened = False
                for t in self._transports():
                    if not self.running:
                        return
                    if self._open(t):
                        opened = True
                        break
                if not opened:
                    self._failures += 1
                    self.last_error = self._diagnose()
                    self.state = "error"
                    self.is_healthy = False
                    logger.warning("[RTSP] %s: %s (attempt %d, retry in %.0fs)",
                                   self.camera_name, self.last_error, self._failures, self._backoff)
                    self._sleep(self._backoff)
                    self._backoff = min(self._backoff * 2, self._backoff_max)
                    continue
                self.connected = True
                self._stall_since = time.monotonic()
                logger.info("[RTSP] Connected to %s via %s", self.camera_name, self._active_transport)

            ok, frame = self.cap.read()
            now = time.monotonic()
            if ok and frame is not None:
                h, w = frame.shape[:2]
                self.resolution = (w, h)
                if self.max_width and w > self.max_width:
                    frame = cv2.resize(frame, (self.max_width, int(h * self.max_width / w)))
                self.slot.put(frame)
                self._last_frame_at = now
                self._stall_since = now
                self._frame_times.append(now)
                if len(self._frame_times) > 1:
                    span = self._frame_times[-1] - self._frame_times[0]
                    self.fps = (len(self._frame_times) - 1) / span if span > 0 else 0.0
                if self.state != "online":
                    self.state, self.is_healthy, self.last_error = "online", True, ""
                    self._backoff, self._failures = 2.0, 0
            elif now - self._stall_since > STALL_SECONDS or not ok and self.cap is not None and not self.cap.isOpened():
                logger.warning("[RTSP] %s stalled for %.0fs — reconnecting", self.camera_name, now - self._stall_since)
                self.last_error = "Stream stalled — reconnecting"
                self.state, self.is_healthy, self.connected = "reconnecting", False, False
                self._failures += 1
            else:
                time.sleep(0.02)

    def _sleep(self, seconds: float):
        end = time.monotonic() + seconds
        while self.running and time.monotonic() < end:
            time.sleep(0.2)

    # ── CameraSource interface ─────────────────────────────────────────
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        tf = self.slot.get_latest_for_display()
        if tf is not None:
            return True, tf.frame
        return False, None

    def read_timestamped(self) -> Optional[TimestampedFrame]:
        return self.slot.get_latest_for_display()

    def is_opened(self) -> bool:
        return self.running and self.connected

    def get_fps(self) -> float:
        return round(self.fps, 1)

    def get_health(self) -> dict:
        return {
            "camera": self.camera_name,
            "state": self.state,
            "connected": self.connected,
            "healthy": self.is_healthy,
            "fps": self.get_fps(),
            "transport": self._active_transport,
            "resolution": list(self.resolution),
            "failures": self._failures,
            "last_frame_age_s": round(time.monotonic() - self._last_frame_at, 1) if self._last_frame_at else None,
            "last_error": self.last_error,
        }

    @property
    def source_name(self) -> str:
        return self.camera_name

    @property
    def source_type(self) -> str:
        return "rtsp"
