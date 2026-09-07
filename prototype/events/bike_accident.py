"""VisionGuard — Bike Accident Detector"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import config

class BikeAccidentDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="bike_accident", window_seconds=8.0)
        self.min_persistence = 1.5

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        # Look for motorcycle + person near each other with person fallen
        bikes = [t for t in analysis.vehicles if t.class_name == "motorcycle"]
        persons = analysis.persons
        poses = analysis.poses

        if not bikes:
            return None

        fallen_riders = 0
        bike_stopped = False

        for bike in bikes:
            bike_vels = list(bike.velocities)
            if bike.is_stationary or (len(bike_vels) >= 3 and
                sum(bike_vels[-3:]) / 3 < config.BIKE_VELOCITY_DROP_THRESHOLD):
                bike_stopped = True

            # Check if any person near the bike has fallen
            for pose in poses:
                if pose.is_fallen or pose.body_angle > config.BIKE_RIDER_ANGLE_THRESHOLD:
                    # Check proximity to bike
                    px, py = (pose.bbox[0] + pose.bbox[2]) / 2, (pose.bbox[1] + pose.bbox[3]) / 2
                    bx, by = bike.center
                    dist = ((px - bx)**2 + (py - by)**2) ** 0.5
                    if dist < 200:  # Person near the bike
                        fallen_riders += 1

        # ONLY trigger bike accident signal if a rider has actually fallen near the bike
        if fallen_riders == 0:
            return None

        return {
            "bikes_detected": len(bikes),
            "bike_stopped": bike_stopped,
            "fallen_riders": fallen_riders,
            "persons_near_bikes": len(persons),
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0
        if latest["bike_stopped"]: score += 25
        if latest["fallen_riders"] > 0: score += 35
        if latest["fallen_riders"] > 0 and latest["bike_stopped"]: score += 20
        if len(signal_window) >= 4: score += 10
        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        return (f"Bike accident | {signals['bikes_detected']} bike(s) | "
                f"Stopped: {signals['bike_stopped']} | "
                f"Fallen riders: {signals['fallen_riders']} | Duration: {duration:.1f}s")
