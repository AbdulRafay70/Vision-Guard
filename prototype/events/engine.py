"""
VisionGuard — Event Engine
Runs all event detectors on each frame analysis and collects alerts.
"""
import logging
import time
from typing import List, Optional, Dict
from ai.pipeline import FrameAnalysis
from events.base import EventAlert

from events.fire import FireDetector
from events.car_accident import CarAccidentDetector
from events.bike_accident import BikeAccidentDetector
from events.fight import FightDetector
from events.robbery import RobberyDetector
from events.kidnapping import KidnappingDetector
from events.weapon_threat import WeaponThreatDetector
from events.crowd import CrowdDetector
from events.loitering import LoiteringDetector
from events.vehicle_obstruction import VehicleObstructionDetector
from events.abandoned_object import AbandonedObjectDetector
from events.audio_emergency import AudioEmergencyDetector

import config


# Event type emoji map
EVENT_EMOJI = {
    "fire": "🔥",
    "car_accident": "🚗",
    "bike_accident": "🏍️",
    "fight": "👊",
    "robbery": "🔫",
    "kidnapping": "🚨",
    "weapon_threat": "🔪",
    "crowd_crush": "👥",
    "loitering": "🧍",
    "vehicle_obstruction": "🚗",
    "abandoned_object": "🎒",
    "audio_emergency": "🔊",
}


class EventEngine:
    """
    Runs all 10 event detectors on each frame and collects alerts.
    """

    def __init__(self, audio_monitor=None):
        self.detectors = [
            FireDetector(),
            CarAccidentDetector(),
            BikeAccidentDetector(),
            FightDetector(),
            RobberyDetector(),
            KidnappingDetector(),
            WeaponThreatDetector(),
            CrowdDetector(),
            LoiteringDetector(),
            VehicleObstructionDetector(),
            AbandonedObjectDetector(),
            AudioEmergencyDetector(audio_monitor=audio_monitor),
        ]
        self.audio_monitor = audio_monitor

        self.active_alerts: List[EventAlert] = []
        self.alert_history: List[EventAlert] = []
        self._alert_count: int = 0

    def set_audio_monitor(self, audio_monitor):
        """Attach a live AudioMonitor after construction (Day 4 audio fusion)."""
        self.audio_monitor = audio_monitor
        for d in self.detectors:
            if isinstance(d, AudioEmergencyDetector):
                d.set_monitor(audio_monitor)

    def process(self, analysis: FrameAnalysis) -> List[EventAlert]:
        """
        Run all detectors on the frame analysis.
        Returns list of new alerts (may be empty).
        """
        if analysis is None:
            return []

        new_alerts = []

        for detector in self.detectors:
            try:
                if not self._should_run_detector(detector, analysis):
                    continue
                alert = detector.check(analysis)
                if alert is not None:
                    self._alert_count += 1
                    alert.frame_number = analysis.frame_number

                    # Check if we already have an active alert of this type
                    existing = self._find_active_alert(alert.event_type)
                    if existing:
                        # Update existing alert
                        existing.risk_score = max(existing.risk_score, alert.risk_score)
                        existing.duration_seconds = alert.duration_seconds
                        existing.details = alert.details
                    else:
                        # New alert
                        self.active_alerts.append(alert)
                        self.alert_history.append(alert)
                        new_alerts.append(alert)

            except Exception as e:
                # Don't let one detector crash the whole engine, but log it
                logging.error("[EVENT ENGINE] Detector '%s' failed: %s",
                              detector.event_type, e, exc_info=True)

        return new_alerts

    def _should_run_detector(self, detector, analysis: FrameAnalysis) -> bool:
        """Check preconditions to short-circuit detectors that cannot fire."""
        if isinstance(detector, FightDetector):
            return analysis.num_persons >= 2
        elif isinstance(detector, RobberyDetector):
            return analysis.num_persons >= 1
        elif isinstance(detector, KidnappingDetector):
            return analysis.num_persons >= 2
        elif isinstance(detector, LoiteringDetector):
            return analysis.num_persons >= 1
        elif isinstance(detector, CrowdDetector):
            return True  # Always run — crowd density depends on spatial distribution, not just count
        elif isinstance(detector, CarAccidentDetector):
            return analysis.num_vehicles > 0
        elif isinstance(detector, BikeAccidentDetector):
            return any(t.class_name == "motorcycle" for t in analysis.vehicles)
        elif isinstance(detector, VehicleObstructionDetector):
            return analysis.num_vehicles > 0
        # FireDetector, WeaponThreatDetector, AbandonedObjectDetector, AudioEmergencyDetector: always run
        return True

    def _find_active_alert(self, event_type: str) -> Optional[EventAlert]:
        """Find an active alert of the given type."""
        for alert in self.active_alerts:
            if alert.event_type == event_type:
                return alert
        return None

    def dismiss_alert(self, event_type: str):
        """Dismiss an active alert."""
        self.active_alerts = [a for a in self.active_alerts if a.event_type != event_type]

    def confirm_alert(self, event_type: str):
        """Confirm an alert and trigger dispatch."""
        alert = self._find_active_alert(event_type)
        if alert:
            alert.action = "CONFIRMED_DISPATCH"
            return alert
        return None

    def get_active_alerts(self) -> List[EventAlert]:
        return self.active_alerts

    def get_alert_count(self) -> int:
        return self._alert_count

    def get_status_summary(self) -> Dict:
        """Get summary for voice command responses."""
        return {
            "active_alerts": len(self.active_alerts),
            "total_alerts_today": self._alert_count,
            "alerts": [
                {
                    "type": a.event_type,
                    "emoji": EVENT_EMOJI.get(a.event_type, "⚠️"),
                    "risk": a.risk_score,
                    "level": a.risk_level,
                    "description": a.description,
                    "department": a.department,
                    "action": a.action,
                    "duration": a.duration_seconds,
                }
                for a in self.active_alerts
            ],
        }

    def reset(self):
        """Reset all detectors and alerts."""
        for d in self.detectors:
            d.reset()
        self.active_alerts.clear()
        self._alert_count = 0
