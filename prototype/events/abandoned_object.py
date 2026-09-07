"""VisionGuard — Abandoned Object Detector"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import time
import config

class AbandonedObjectDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="abandoned_object", window_seconds=120.0)
        self.min_persistence = 30.0
        self._object_positions = {}   # track_id -> (first_seen, position)
        self._object_owners = {}      # object_track_id -> person_track_id

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        objects = analysis.objects  # backpack, suitcase, handbag
        persons = analysis.persons
        now = time.time()

        # Track objects and their nearest person
        for obj in objects:
            if obj.class_name not in ("backpack", "handbag", "suitcase"):
                continue

            if obj.track_id not in self._object_positions:
                self._object_positions[obj.track_id] = (now, obj.center)
                # Find nearest person
                nearest_person = None
                min_dist = float("inf")
                for p in persons:
                    dx = p.center[0] - obj.center[0]
                    dy = p.center[1] - obj.center[1]
                    dist = (dx**2 + dy**2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_person = p.track_id
                if nearest_person and min_dist < config.ABANDON_PERSON_DISTANCE_THRESHOLD:
                    self._object_owners[obj.track_id] = nearest_person

        # Check for abandoned objects
        abandoned = []
        for obj in objects:
            if obj.class_name not in ("backpack", "handbag", "suitcase"):
                continue
            if obj.track_id not in self._object_positions:
                continue

            first_seen, _ = self._object_positions[obj.track_id]
            stationary_time = now - first_seen

            if stationary_time < 30:
                continue

            # Check if owner (nearest person) has left
            owner_id = self._object_owners.get(obj.track_id)
            owner_present = False
            if owner_id:
                for p in persons:
                    if p.track_id == owner_id:
                        dx = p.center[0] - obj.center[0]
                        dy = p.center[1] - obj.center[1]
                        if (dx**2 + dy**2)**0.5 < config.ABANDON_PERSON_DISTANCE_THRESHOLD:
                            owner_present = True

            if not owner_present and stationary_time > config.ABANDON_OBJECT_TIME_THRESHOLD:
                abandoned.append({
                    "object_id": obj.vg_id,
                    "object_type": obj.class_name,
                    "stationary_time": stationary_time,
                    "owner_left": not owner_present,
                })

        if not abandoned:
            return None

        longest = max(abandoned, key=lambda x: x["stationary_time"])
        return longest

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0
        t = latest["stationary_time"]
        if t > 60: score += 25
        if t > 120: score += 20
        if t > 300: score += 15
        if latest["owner_left"]: score += 25
        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        return (f"Abandoned {signals['object_type']} | {signals['object_id']} | "
                f"Stationary: {signals['stationary_time']:.0f}s | "
                f"Owner left: {signals['owner_left']}")
