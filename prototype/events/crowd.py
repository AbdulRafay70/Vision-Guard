"""
VisionGuard — Crowd Density Detector
Counts persons in the frame, tracks growth rate, predicts overcrowding.
"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import time

import config


class CrowdDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="crowd_crush", window_seconds=60.0)
        self.min_persistence = 8.0  # Crowd situations develop over time, not instantly
        self._crowd_history = []     # (timestamp, count) pairs

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        person_count = analysis.num_persons
        now = time.time()

        # Always record crowd data
        self._crowd_history.append((now, person_count))

        # Clean old history
        cutoff = now - config.CROWD_HISTORY_WINDOW
        self._crowd_history = [(t, c) for t, c in self._crowd_history if t > cutoff]

        # Calculate growth rate
        growth_rate = 0.0
        if len(self._crowd_history) >= 5:
            old_count = self._crowd_history[0][1]
            time_diff = (now - self._crowd_history[0][0]) / 60.0  # minutes
            if time_diff > 0.5:  # Need at least 30 seconds of history for meaningful growth rate
                growth_rate = (person_count - old_count) / time_diff
                growth_rate = min(growth_rate, 30)  # Cap to prevent runaway extrapolation

        # Calculate density ratio
        capacity = config.CROWD_ZONE_CAPACITY
        density_ratio = person_count / capacity if capacity > 0 else 0

        # Predict future count
        predicted_5min = person_count + (growth_rate * 5)

        # Only return signals if crowd is notable (8+ people)
        # A group of 5-7 people (e.g. a fight) is NOT a crowd
        if person_count < 8:
            return None

        return {
            "current_count": person_count,
            "zone_capacity": capacity,
            "density_ratio": density_ratio,
            "growth_rate": round(growth_rate, 2),  # people per minute
            "predicted_5min": round(predicted_5min),
            "is_growing": growth_rate > 0.5,
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0
        ratio = latest["density_ratio"]

        # Current density
        if ratio > 0.5:
            score += 15
        if ratio > 0.7:
            score += 20
        if ratio > 0.9:
            score += 25
        if ratio > 1.0:
            score += 15  # Over capacity

        # Growth rate
        if latest["growth_rate"] > 2:
            score += 10
        if latest["growth_rate"] > 5:
            score += 10

        # Predicted overcrowding
        if latest["predicted_5min"] > latest["zone_capacity"]:
            score += 15

        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        return (
            f"Crowd density alert | "
            f"{signals['current_count']} people (capacity: {signals['zone_capacity']}) | "
            f"Density: {signals['density_ratio']:.0%} | "
            f"Growth: {signals['growth_rate']:+.1f}/min | "
            f"Predicted in 5min: {signals['predicted_5min']}"
        )
