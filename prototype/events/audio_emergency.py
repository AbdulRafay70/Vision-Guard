"""
VisionGuard — Audio Emergency Detector (Day 4 — Rafay)
Fuses live YAMNet sound classifications (gunshot, explosion, scream, crash,
glass breaking) from the AudioMonitor microphone thread into the event engine.

Unlike the visual detectors, this detector reads its signals from the shared
AudioMonitor rolling window rather than from the frame analysis, so emergency
sounds raise alerts even when the corresponding visual event is off-camera.
"""
from typing import Dict, List, Optional, Any

from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis

import config


# Risk score per emergency sound keyword (higher = more urgent)
_SOUND_RISK = {
    "gunshot": 95,
    "gunfire": 95,
    "explosion": 95,
    "blast": 90,
    "screaming": 70,
    "scream": 70,
    "crash": 75,
    "glass": 60,
    "siren": 40,
}


class AudioEmergencyDetector(BaseEventDetector):
    """Raises alerts from live microphone emergency-sound detections."""

    def __init__(self, audio_monitor=None):
        super().__init__(event_type="audio_emergency", window_seconds=6.0)
        # Audio emergencies are near-instant — minimal persistence required
        self.min_persistence = 0.5
        self.audio_monitor = audio_monitor

    def set_monitor(self, audio_monitor):
        """Attach/replace the AudioMonitor source (used when mic starts later)."""
        self.audio_monitor = audio_monitor

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        if self.audio_monitor is None:
            return None

        try:
            events = self.audio_monitor.get_recent_events()
        except Exception:
            return None

        if not events:
            return None

        # Pick the most urgent sound in the recent window
        best = None
        best_risk = -1
        for ev in events:
            risk = self._risk_for(ev.sound_class)
            if risk > best_risk:
                best_risk = risk
                best = ev

        if best is None:
            return None

        return {
            "sound_class": best.sound_class,
            "confidence": best.confidence,
            "base_risk": best_risk,
            "num_sounds": len(events),
            "all_sounds": sorted(set(e.sound_class for e in events)),
        }

    @staticmethod
    def _risk_for(sound_class: str) -> int:
        name = sound_class.lower()
        for keyword, risk in _SOUND_RISK.items():
            if keyword in name:
                return risk
        return 30

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = latest.get("base_risk", 30)

        # Boost when multiple emergency sounds overlap (e.g. gunshot + scream)
        if latest.get("num_sounds", 1) >= 2:
            score += 5

        # Confidence scaling
        conf = latest.get("confidence", 0.0)
        if conf >= 0.8:
            score += 5

        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        sound = signals.get("sound_class", "Emergency sound")
        conf = signals.get("confidence", 0.0)
        others = signals.get("all_sounds", [])
        extra = ""
        if len(others) > 1:
            extra = f" | Also heard: {', '.join(o for o in others if o != sound)}"
        return (
            f"🔊 AUDIO EMERGENCY: {sound} detected | "
            f"Confidence: {conf * 100:.0f}% | "
            f"Risk: {risk_score}%{extra} | "
            f"Duration: {duration:.1f}s"
        )
