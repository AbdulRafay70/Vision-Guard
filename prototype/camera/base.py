"""
VisionGuard — Abstract Camera Source
Shared interface for all camera sources (webcam, RTSP, video file).
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np


class CameraSource(ABC):
    """
    Abstract base class for all video input sources.
    Ensures a uniform interface for webcam, RTSP, and video file sources.
    """

    @abstractmethod
    def start(self) -> bool:
        """Initialize and start capturing. Returns True on success."""
        ...

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read the latest frame.
        Returns (success, frame). Frame is a BGR numpy array.
        """
        ...

    @abstractmethod
    def stop(self):
        """Stop capturing and release all resources."""
        ...

    @abstractmethod
    def is_opened(self) -> bool:
        """Check if the source is still active and usable."""
        ...

    @abstractmethod
    def get_fps(self) -> float:
        """Return the current or nominal FPS."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for display (e.g., 'Webcam-0', 'Main Entrance')."""
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Source type identifier: 'webcam', 'rtsp', or 'video'."""
        ...
