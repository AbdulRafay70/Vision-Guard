"""
VisionGuard — Video File Source
Loads and plays back a video file frame by frame for AI processing.
"""
import cv2
import logging
import time
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

from camera.base import CameraSource
from camera.slot import LatestFrameSlot, TimestampedFrame

logger = logging.getLogger(__name__)


class VideoFileSource(CameraSource):
    """
    Reads frames from a video file (.mp4, .avi, .mkv, etc.).
    Supports play, pause, seek, frame stepping, and timestamped frame slot.
    """

    def __init__(self, file_path: str, loop: bool = False, throttle: bool = True):
        self.file_path = Path(file_path)
        self.loop = loop
        self.throttle = throttle
        self.cap: Optional[cv2.VideoCapture] = None
        self.paused: bool = False
        self.finished: bool = False
        self._frame_count: int = 0
        self._total_frames: int = 0
        self._fps: float = 30.0
        self._width: int = 0
        self._height: int = 0
        self._last_frame_time: float = 0.0
        self.slot = LatestFrameSlot(name=f"video-{self.file_path.name}")

    def start(self) -> bool:
        """Open the video file."""
        if not self.file_path.exists():
            logger.error("[VIDEO] File not found: %s", self.file_path)
            return False

        self.cap = cv2.VideoCapture(str(self.file_path))

        if not self.cap.isOpened():
            logger.error("[VIDEO] Cannot open video: %s", self.file_path)
            return False

        self._total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info("[VIDEO] Loaded: %s (%dx%d, %.1f FPS, %d frames, %.1fs)",
                     self.file_path.name, self._width, self._height,
                     self._fps, self._total_frames,
                     self._total_frames / self._fps if self._fps else 0)

        self._last_frame_time = time.monotonic()
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read the next frame from the video.
        Respects video FPS timing for natural playback speed.
        Returns (success, frame).
        """
        if self.cap is None or self.finished:
            return False, None

        if self.paused:
            # When paused, return the current frame without advancing
            current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_pos > 0:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos - 1)
            ret, frame = self.cap.read()
            if ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
            return ret, frame

        # Accurate pacing to match video nominal FPS without decode latency drift
        if self.throttle and self._fps > 0:
            frame_interval = 1.0 / self._fps
            now = time.monotonic()
            if self._last_frame_time == 0.0:
                self._last_frame_time = now
            else:
                target_time = self._last_frame_time + frame_interval
                wait_time = target_time - now
                if 0.001 < wait_time < 1.0:
                    time.sleep(wait_time)
                self._last_frame_time = time.monotonic()

        ret, frame = self.cap.read()

        if ret and frame is not None:
            self._frame_count += 1
            self.slot.put(frame)
            return True, frame
        else:
            if self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._frame_count = 0
                self._last_frame_time = time.monotonic()
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.slot.put(frame)
                    return True, frame
                return False, None
            else:
                self.finished = True
                return False, None

    def read_timestamped(self) -> Optional[TimestampedFrame]:
        """Return the latest TimestampedFrame."""
        tf = self.slot.get_latest_for_display()
        if tf is None:
            # If slot empty, do a direct read
            success, _ = self.read()
            if success:
                return self.slot.get_latest_for_display()
        return tf

    def toggle_pause(self):
        """Pause or resume playback."""
        self.paused = not self.paused
        state = "PAUSED" if self.paused else "PLAYING"
        logger.info("[VIDEO] %s", state)

    def step_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Advance one frame (when paused)."""
        if self.cap is None:
            return False, None
        ret, frame = self.cap.read()
        if ret:
            self._frame_count += 1
        return ret, frame

    def seek(self, frame_number: int):
        """Seek to a specific frame."""
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self._frame_count = frame_number
            logger.info("[VIDEO] Seeked to frame %d", frame_number)

    def get_progress(self) -> Tuple[int, int]:
        """Returns (current_frame, total_frames)."""
        return self._frame_count, self._total_frames

    def get_fps(self) -> float:
        return self._fps

    def get_frame_count(self) -> int:
        return self._frame_count

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened() and not self.finished

    def stop(self):
        """Release the video file."""
        if self.cap is not None:
            self.cap.release()
        logger.info("[VIDEO] Released: %s", self.file_path.name)

    @property
    def source_name(self) -> str:
        return self.file_path.name

    @property
    def source_type(self) -> str:
        return "video"
