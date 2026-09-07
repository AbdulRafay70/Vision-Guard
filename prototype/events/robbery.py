"""VisionGuard — Robbery Detector"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import config


class RobberyDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="robbery", window_seconds=15.0)
        self.min_persistence = 3.0

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        vehicles = analysis.vehicles
        persons = analysis.persons
        poses = analysis.poses

        if len(persons) < config.ROBBERY_MIN_SUSPECTS:
            return None

        if len(persons) > 8:
            return None  # Robbery is a small-group event; large groups are crowd events

        has_weapon = len(analysis.weapon_detections) > 0

        # Compute stopped vehicles (stationary or near-zero velocity)
        stopped_vehicles = [v for v in vehicles if v.is_stationary]

        # Compute fast-moving persons (rushing from vehicle or toward target)
        fast_persons = [p for p in persons if p.avg_velocity > config.ROBBERY_RUSH_VELOCITY]

        # Count aggressive poses from skeleton keypoints
        aggressive = 0
        for pose in poses:
            # Wide arm spread indicates aggressive/threatening stance
            if pose.arm_spread > 150:
                aggressive += 1
            # Arm raised above shoulder (threatening gesture)
            lw = pose.left_wrist
            ls = pose.left_shoulder
            rw = pose.right_wrist
            rs = pose.right_shoulder
            if (lw[2] > 0.3 and ls[2] > 0.3 and lw[1] < ls[1]) or \
               (rw[2] > 0.3 and rs[2] > 0.3 and rw[1] < rs[1]):
                aggressive += 1

        # Robbery requires EITHER a detected weapon OR (a stopped vehicle AND rushing suspects)
        if not has_weapon and (not stopped_vehicles or not fast_persons):
            return None

        return {
            "stopped_vehicles": len(stopped_vehicles),
            "fast_persons": len(fast_persons),
            "total_persons": len(persons),
            "aggressive_poses": aggressive,
            "vehicle_involved": stopped_vehicles[0].vg_id if stopped_vehicles else "none",
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0
        if latest["stopped_vehicles"] > 0: score += 20
        if latest["fast_persons"] >= 2: score += 25
        if latest["aggressive_poses"] > 0: score += 20
        if latest["stopped_vehicles"] > 0 and latest["fast_persons"] >= 2: score += 15
        if len(signal_window) >= 5: score += 10
        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        return (f"Robbery suspected | Vehicle: {signals['vehicle_involved']} | "
                f"{signals['fast_persons']} persons rushing | "
                f"Aggressive poses: {signals['aggressive_poses']} | Duration: {duration:.1f}s")
