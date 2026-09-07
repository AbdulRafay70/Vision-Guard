"""
VisionGuard — Display Module
Draws AI overlays on video frames: bounding boxes, track IDs, skeletons, events.
"""
import cv2
import numpy as np
from typing import List, Optional

from ai.pipeline import FrameAnalysis
from ai.tracker import Track
from ai.pose import PoseResult
from events.base import EventAlert

import config


# Skeleton connections for drawing
SKELETON_CONNECTIONS = [
    (0, 1), (0, 2), (1, 3), (2, 4),     # Head
    (5, 6),                                # Shoulders
    (5, 7), (7, 9),                        # Left arm
    (6, 8), (8, 10),                       # Right arm
    (5, 11), (6, 12),                      # Torso
    (11, 12),                              # Hips
    (11, 13), (13, 15),                    # Left leg
    (12, 14), (14, 16),                    # Right leg
]


class DisplayRenderer:
    """Draws AI overlays on video frames for display and MJPEG streaming."""

    def __init__(self):
        self.show_detections = True
        self.show_tracks = True
        self.show_skeletons = True  # Enabled by default: yellow 17-keypoint body skeletons & joints
        self.show_info = True

    def render(self, frame: np.ndarray, analysis: Optional[FrameAnalysis],
               alerts: List[EventAlert], source_name: str = "Unknown") -> np.ndarray:
        """
        Render all overlays on the frame.
        Returns a copy with all annotations drawn.
        """
        display = frame.copy()

        if analysis is not None:
            if self.show_tracks:
                self._draw_tracks(display, analysis.tracks)
            elif self.show_detections:
                self._draw_detections(display, analysis)

            if self.show_skeletons:
                self._draw_skeletons(display, analysis.poses)

            # Draw fire/smoke detections with special color
            self._draw_fire_smoke(display, analysis)

        # Draw event alerts on frame
        if alerts:
            self._draw_alerts(display, alerts)

        # Draw info bar
        if self.show_info:
            self._draw_info_bar(display, analysis, alerts, source_name)

        return display

    def _draw_tracks(self, frame: np.ndarray, tracks: List[Track]):
        """Draw tracked objects with VG-IDs."""
        for track in tracks:
            x1, y1, x2, y2 = [int(v) for v in track.bbox]

            # Color by category
            if track.category == "person":
                color = config.COLOR_PERSON
            elif track.category == "vehicle":
                color = config.COLOR_VEHICLE
            else:
                color = config.COLOR_OBJECT

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw label with VG-ID
            label = f"{track.vg_id} {track.class_name} {track.confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]

            # Background for label
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 8),
                         (x1 + label_size[0] + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

            # Draw velocity indicator
            vel = track.avg_velocity
            if vel > 1:
                vel_text = f"v={vel:.1f}"
                cv2.putText(frame, vel_text, (x1, y2 + 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    def _draw_detections(self, frame: np.ndarray, analysis: FrameAnalysis):
        """Draw raw detections (without tracking)."""
        for det in analysis.detections:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]

            if det.category == "person":
                color = config.COLOR_PERSON
            elif det.category == "vehicle":
                color = config.COLOR_VEHICLE
            elif det.category in ("fire", "smoke"):
                color = config.COLOR_FIRE
            else:
                color = config.COLOR_OBJECT

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def _draw_skeletons(self, frame: np.ndarray, poses: List[PoseResult]):
        """Draw pose skeletons using fast integer line rasterization (cv2.LINE_8)."""
        for pose in poses:
            kps = pose.keypoints

            # Fast integer lines (saves ~70% CPU rasterization time compared to anti-aliased subpixel lines)
            for i, j in SKELETON_CONNECTIONS:
                if kps[i][2] > 0.25 and kps[j][2] > 0.25:
                    pt1 = (int(kps[i][0]), int(kps[i][1]))
                    pt2 = (int(kps[j][0]), int(kps[j][1]))
                    cv2.line(frame, pt1, pt2, config.COLOR_SKELETON, 2, cv2.LINE_8)

            # Draw keypoints (fast integer circles)
            for i, (x, y, conf) in enumerate(kps):
                if conf > 0.25:
                    cv2.circle(frame, (int(x), int(y)), 3, config.COLOR_SKELETON, -1, cv2.LINE_8)

            # Show body angle if significant
            angle = pose.body_angle
            if angle > 25:
                center = ((pose.bbox[0] + pose.bbox[2]) / 2,
                         (pose.bbox[1] + pose.bbox[3]) / 2)
                label = f"angle={angle:.0f}°"
                color = config.COLOR_RISK_HIGH if angle > 45 else config.COLOR_RISK_MEDIUM
                cv2.putText(frame, label, (int(center[0]), int(center[1]) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_8)

    def _draw_fire_smoke(self, frame: np.ndarray, analysis: FrameAnalysis):
        """Draw fire/smoke with flashing border and freshness indication."""
        fire_telemetry = analysis.specialist_telemetry.get("fire", {})
        status = fire_telemetry.get("status", "ACTIVE")
        age_ms = fire_telemetry.get("age_ms", 0.0)

        # Do not display expired detections (> 750 ms)
        if status == "EXPIRED":
            return

        for det in analysis.fire_detections + analysis.smoke_detections:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            color = config.COLOR_FIRE if det.category == "fire" else config.COLOR_SMOKE

            # Border style based on freshness
            thickness = 3 if status == "ACTIVE" else 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

            stale_tag = f" [STALE {int(age_ms)}ms]" if status == "STALE" else ""
            label = f"{'🔥 FIRE' if det.category == 'fire' else 'SMOKE'} {det.confidence:.0%}{stale_tag}"
            cv2.putText(frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    def _draw_alerts(self, frame: np.ndarray, alerts: List[EventAlert]):
        """Draw event alert banner on the frame."""
        h, w = frame.shape[:2]

        for i, alert in enumerate(alerts[-3:]):  # Show latest 3 alerts
            y_offset = h - 80 - (i * 70)

            # Alert background
            if alert.risk_level == "CRITICAL":
                bg_color = (0, 0, 180)
            elif alert.risk_level == "HIGH":
                bg_color = (0, 80, 180)
            else:
                bg_color = (0, 120, 120)

            overlay = frame.copy()
            cv2.rectangle(overlay, (10, y_offset), (w - 10, y_offset + 60), bg_color, -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            # Alert text
            alert_text = f"{alert.event_type.upper()} | Risk: {alert.risk_score}% | {alert.risk_level}"
            cv2.putText(frame, alert_text, (20, y_offset + 22),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            dept_text = f"Dept: {alert.department} ({alert.dial}) | Action: {alert.action}"
            cv2.putText(frame, dept_text, (20, y_offset + 48),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    def _draw_info_bar(self, frame: np.ndarray, analysis: Optional[FrameAnalysis],
                       alerts: List[EventAlert], source_name: str):
        """Draw comprehensive decoupled architecture info bar at the top of the frame."""
        h, w = frame.shape[:2]

        # Top bar background (expand height to 55px to fit architecture telemetry)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 55), (25, 25, 25), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Title
        title = f"VisionGuard [{source_name}]"
        cv2.putText(frame, title, (10, 18),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 255), 1)

        if analysis:
            # Row 1: Primary Pipeline presentation stats
            stats = (f"Presentation: ~30 FPS | "
                     f"Primary AI: {analysis.processing_time_ms:.0f}ms | "
                     f"Frame: #{analysis.frame_number}")
            cv2.putText(frame, stats, (10, 36),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

            # Row 2: Async Specialist Worker Telemetry
            telemetry = analysis.specialist_telemetry
            if telemetry:
                f_fps = telemetry.get('fire', {}).get('fps', 0)
                f_age = telemetry.get('fire', {}).get('age_ms', 0)
                w_fps = telemetry.get('weapon', {}).get('fps', 0)
                p_fps = telemetry.get('pose', {}).get('fps', 0)
                spec_text = f"Async Specialists: Fire {f_fps} FPS ({int(f_age)}ms) | Weapon {w_fps} FPS | Pose {p_fps} FPS"
            else:
                spec_text = "Mode: Synchronous Chained Pipeline"
            cv2.putText(frame, spec_text, (10, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 220, 140), 1)

            # Detection summary (right side)
            summary = analysis.get_summary()
            cv2.putText(frame, summary, (w - 430, 22),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 0), 1)

        # Alert count
        if alerts:
            alert_text = f"ALERTS: {len(alerts)}"
            cv2.putText(frame, alert_text, (w - 140, 44),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    def toggle_detections(self):
        self.show_detections = not self.show_detections

    def toggle_tracks(self):
        self.show_tracks = not self.show_tracks

    def toggle_skeletons(self):
        self.show_skeletons = not self.show_skeletons

    def toggle_info(self):
        self.show_info = not self.show_info
