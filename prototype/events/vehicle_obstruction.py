"""
VisionGuard — Vehicle Obstruction Detector
Detects when a vehicle is stopped in a driving zone for too long.
"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import time

import config


class VehicleObstructionDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="vehicle_obstruction", window_seconds=30.0)
        self.min_persistence = config.VEHICLE_STOP_DURATION_THRESHOLD
        self._vehicle_stop_times = {}  # track_id -> stop_start_time

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        vehicles = analysis.vehicles
        now = time.time()

        # Need at least 2 vehicles to consider obstruction
        # A single "stopped vehicle" in a non-traffic scene is almost always a misdetection
        if len(vehicles) < 2:
            return None

        stopped_vehicles = []
        for v in vehicles:
            if v.is_stationary:
                if v.track_id not in self._vehicle_stop_times:
                    self._vehicle_stop_times[v.track_id] = now

                stop_duration = now - self._vehicle_stop_times[v.track_id]
                other_moving = sum(1 for ov in vehicles
                                   if ov.track_id != v.track_id and not ov.is_stationary)

                stopped_vehicles.append({
                    "vehicle_id": v.vg_id,
                    "stop_duration": stop_duration,
                    "other_vehicles_moving": other_moving,
                    "velocity": v.avg_velocity,
                })
            else:
                self._vehicle_stop_times.pop(v.track_id, None)

        if not stopped_vehicles:
            return None

        # Get the longest-stopped vehicle
        longest = max(stopped_vehicles, key=lambda x: x["stop_duration"])

        if longest["stop_duration"] < 8.0:  # Need at least 8 seconds of sustained stop
            return None

        return {
            "stopped_count": len(stopped_vehicles),
            "longest_stop_duration": longest["stop_duration"],
            "longest_stop_vehicle": longest["vehicle_id"],
            "other_traffic_moving": longest["other_vehicles_moving"] > 0,
            "total_vehicles": len(vehicles),
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0

        duration = latest["longest_stop_duration"]

        if duration > 10:
            score += 25
        if duration > 30:
            score += 20
        if duration > 60:
            score += 15

        # Other traffic moving around it = more suspicious
        if latest["other_traffic_moving"]:
            score += 20

        # Multiple stopped vehicles = possibly accident scene
        if latest["stopped_count"] >= 2:
            score += 10

        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        return (
            f"Vehicle obstruction | "
            f"{signals['longest_stop_vehicle']} stopped for "
            f"{signals['longest_stop_duration']:.0f}s | "
            f"Other traffic moving: {'Yes' if signals['other_traffic_moving'] else 'No'} | "
            f"{signals['total_vehicles']} total vehicles"
        )
