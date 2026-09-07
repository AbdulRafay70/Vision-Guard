"""
VisionGuard — Latest Frame Slot (Capacity = 1)
Thread-safe single-slot buffer implementing true overwrite / latest-frame semantics.
Camera ingestion NEVER waits or blocks on AI inference.
Readers receive a safe copy or immutable reference so camera write never corrupts reader memory.
"""
import time
import threading
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class TimestampedFrame:
    """A video frame stamped with monotonic capture time and sequence ID."""
    frame: np.ndarray
    frame_id: int
    capture_timestamp: float  # time.monotonic()

    @property
    def age_ms(self) -> float:
        """Current frame age in milliseconds since original camera capture."""
        return (time.monotonic() - self.capture_timestamp) * 1000.0


class LatestFrameSlot:
    """
    Capacity = 1 Frame Slot.
    - Camera thread calls `put(frame)`: immediately overwrites slot, never blocks.
    - Reader thread calls `get_latest()`: gets the most recent frame.
    - Tracks dropped stale frames when overwritten before an AI consumer reads it.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._lock = threading.Lock()
        self._current: Optional[TimestampedFrame] = None
        self._frame_counter: int = 0
        self._total_produced: int = 0
        self._total_consumed_display: int = 0
        self._total_consumed_ai: int = 0
        self._dropped_unprocessed: int = 0
        self._last_ai_read_frame_id: int = -1

    def put(self, frame: np.ndarray) -> TimestampedFrame:
        """
        Camera ingestion: store newest frame, overwriting any previous frame.
        Guaranteed non-blocking. Uses copy to guarantee reader thread safety.
        """
        capture_time = time.monotonic()
        with self._lock:
            self._frame_counter += 1
            self._total_produced += 1

            # If previous frame was never read by AI, it was dropped as stale
            if self._current is not None and self._current.frame_id > self._last_ai_read_frame_id:
                self._dropped_unprocessed += 1

            # Store safe copy so camera reader buffer mutation never affects consumers
            self._current = TimestampedFrame(
                frame=frame.copy(),
                frame_id=self._frame_counter,
                capture_timestamp=capture_time
            )
            return self._current

    def get_latest_for_display(self) -> Optional[TimestampedFrame]:
        """
        Display loop: get the most recent frame immediately without waiting.
        """
        with self._lock:
            if self._current is not None:
                self._total_consumed_display += 1
            return self._current

    def get_latest_for_ai(self) -> Optional[TimestampedFrame]:
        """
        AI worker: get newest frame only if it has not yet been processed by AI.
        If no new frame has arrived since last AI read, returns None (no duplicate work).
        """
        with self._lock:
            if self._current is None:
                return None
            if self._current.frame_id == self._last_ai_read_frame_id:
                return None  # No new frame arrived
            self._last_ai_read_frame_id = self._current.frame_id
            self._total_consumed_ai += 1
            return self._current

    def get_stats(self) -> dict:
        """Return slot telemetry."""
        with self._lock:
            current_age = self._current.age_ms if self._current is not None else 0.0
            return {
                "name": self.name,
                "produced": self._total_produced,
                "consumed_display": self._total_consumed_display,
                "consumed_ai": self._total_consumed_ai,
                "dropped_stale": self._dropped_unprocessed,
                "current_frame_id": self._current.frame_id if self._current else 0,
                "current_age_ms": round(current_age, 2),
                "buffer_capacity": 1,
            }
