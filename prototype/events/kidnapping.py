"""VisionGuard — Kidnapping Detector"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import config

class KidnappingDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="kidnapping", window_seconds=15.0)
        self.min_persistence = 3.0

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        persons = analysis.persons
        vehicles = analysis.vehicles
        poses = analysis.poses

        if len(persons) < 2:
            return None

        # Pattern: person approaches another rapidly → struggle → forced movement toward vehicle
        rapid_approach = False
        struggle_detected = False
        forced_toward_vehicle = False

        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                p1, p2 = persons[i], persons[j]
                dx = p1.center[0] - p2.center[0]
                dy = p1.center[1] - p2.center[1]
                dist = (dx**2 + dy**2) ** 0.5

                # Rapid approach: close distance (<80px) and fast charging velocity (>20px/frame)
                if dist < 80 and (p1.avg_velocity > 20.0 or p2.avg_velocity > 20.0):
                    rapid_approach = True

        # Struggle: high pose variance AND rapid movement / proximity
        if rapid_approach or forced_toward_vehicle:
            for pose in poses:
                if pose.arm_spread > 180 or pose.body_angle > 45:
                    struggle_detected = True

        # MUST be forced toward a vehicle OR rapid approach right next to a vehicle (<150px)
        if not forced_toward_vehicle:
            # Check if rapid approach happened near a vehicle
            near_vehicle = False
            for p in persons:
                for v in vehicles:
                    dist = ((p.center[0] - v.center[0])**2 + (p.center[1] - v.center[1])**2) ** 0.5
                    if dist < 150:
                        near_vehicle = True
            if not (rapid_approach and struggle_detected and near_vehicle):
                return None

        return {
            "rapid_approach": rapid_approach,
            "struggle_detected": struggle_detected,
            "forced_toward_vehicle": forced_toward_vehicle,
            "num_persons": len(persons),
            "vehicles_nearby": len(vehicles),
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0
        if latest["rapid_approach"]: score += 20
        if latest["struggle_detected"]: score += 25
        if latest["forced_toward_vehicle"]: score += 25
        if latest["rapid_approach"] and latest["struggle_detected"]: score += 15
        if len(signal_window) >= 5: score += 10
        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        return (f"Kidnapping suspected | Rapid approach: {signals['rapid_approach']} | "
                f"Struggle: {signals['struggle_detected']} | "
                f"Forced toward vehicle: {signals['forced_toward_vehicle']} | "
                f"Duration: {duration:.1f}s")
