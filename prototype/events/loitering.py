"""VisionGuard — Loitering Detector"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import time
import config

class LoiteringDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="loitering", window_seconds=600.0)  # 10 min window
        self.min_persistence = 10.0
        self._person_entry_times = {}  # track_id -> first_seen

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        persons = analysis.persons
        now = time.time()

        for p in persons:
            if p.track_id not in self._person_entry_times:
                self._person_entry_times[p.track_id] = now

        # Find longest-dwelling person
        max_dwell = 0
        loiterer_id = None
        loiterer_stationary = False

        for p in persons:
            entry = self._person_entry_times.get(p.track_id, now)
            dwell = now - entry
            if dwell > max_dwell:
                max_dwell = dwell
                loiterer_id = p.vg_id
                loiterer_stationary = p.total_displacement < config.LOITER_MOVEMENT_THRESHOLD

        # Clean old entries
        active_ids = {p.track_id for p in persons}
        self._person_entry_times = {k: v for k, v in self._person_entry_times.items() if k in active_ids}

        if max_dwell < config.LOITER_TIME_THRESHOLD:  # Ignore until threshold reached
            return None

        return {
            "max_dwell_time": max_dwell,
            "loiterer_id": loiterer_id,
            "loiterer_stationary": loiterer_stationary,
            "total_persons": len(persons),
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0
        dwell = latest["max_dwell_time"]
        if dwell > 120: score += 15   # > 2 min
        if dwell > 300: score += 20   # > 5 min
        if dwell > 600: score += 20   # > 10 min
        if latest["loiterer_stationary"]: score += 15
        if latest["total_persons"] == 1: score += 10  # Alone = more suspicious
        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        return (f"Loitering detected | {signals['loiterer_id']} dwelling for "
                f"{signals['max_dwell_time']:.0f}s | "
                f"Stationary: {signals['loiterer_stationary']}")
