"""
VisionGuard — Shared Geometry Utilities
Common math helpers used across detection, tracking, and event detectors.
"""
from typing import List


def bbox_iou(box1: List[float], box2: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    Each box is [x1, y1, x2, y2].
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter

    if union == 0:
        return 0.0
    return inter / union


def bbox_center(box: List[float]) -> tuple:
    """Get the center point of a bounding box [x1, y1, x2, y2]."""
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def euclidean_distance(p1: tuple, p2: tuple) -> float:
    """Euclidean distance between two (x, y) points."""
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
