"""
VisionGuard — Fire Event Detector
Detects fire and smoke using YOLO fire model or color analysis fallback.
"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis

import config


class FireDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="fire", window_seconds=10.0)
        self.min_persistence = 0.8  # Fire is urgent — confirm quickly like a human operator would

    def check(self, analysis: FrameAnalysis) -> Optional[Any]:
        alert = super().check(analysis)
        if alert is None:
            return None

        # Gate: suppress low-confidence / borderline fire alerts
        if alert.risk_score < config.FIRE_RISK_GATE:
            return None

        return alert

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        fire_dets = analysis.fire_detections
        smoke_dets = analysis.smoke_detections

        if not fire_dets and not smoke_dets:
            return None

        max_fire_conf = max((d.confidence for d in fire_dets), default=0)
        max_smoke_conf = max((d.confidence for d in smoke_dets), default=0)
        total_fire_area = sum(d.frame_percent for d in fire_dets)
        total_smoke_area = sum(d.frame_percent for d in smoke_dets)

        return {
            "fire_detected": len(fire_dets) > 0,
            "smoke_detected": len(smoke_dets) > 0,
            "fire_confidence": max_fire_conf,
            "smoke_confidence": max_smoke_conf,
            "fire_area_percent": total_fire_area,
            "smoke_area_percent": total_smoke_area,
            "fire_count": len(fire_dets),
            "smoke_count": len(smoke_dets),
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        # Human-like confirmation: a person watching CCTV calls "fire" once they
        # see flames *keep appearing* for a moment, not after a single flicker
        # and not only when the model is extremely confident. The previous gate
        # demanded peak confidence >= 0.65, but fire models routinely score
        # real early-stage CCTV fire at 0.40-0.60, so fires were missed at the
        # start and only flagged once they were large. Smoke alone was also
        # never accepted, although smoke is often the first visible sign.
        fire_samples = [s for s in signal_window if s.get("fire_detected")]
        smoke_samples = [s for s in signal_window if s.get("smoke_detected")]
        fire_frames = len(fire_samples)
        smoke_frames = len(smoke_samples)

        peak_fire_conf = max((s.get("fire_confidence", 0.0) for s in signal_window), default=0.0)
        peak_smoke_conf = max((s.get("smoke_confidence", 0.0) for s in signal_window), default=0.0)

        def _span(samples):
            if len(samples) < 2:
                return 0.0
            return samples[-1].get("_timestamp", 0.0) - samples[0].get("_timestamp", 0.0)

        # Ratio of recent samples containing fire — filters one-off glitches
        recent = signal_window[-10:]
        recent_fire_ratio = sum(1 for s in recent if s.get("fire_detected")) / len(recent)

        is_genuine = (
            # Sustained fire: recurring over >= 0.6s with a clear detection
            (fire_frames >= 3 and _span(fire_samples) >= 0.6
             and peak_fire_conf >= 0.45 and recent_fire_ratio >= 0.4) or
            # Very confident fire confirms faster
            (fire_frames >= 2 and peak_fire_conf >= 0.70) or
            # Fire corroborated by smoke
            (fire_frames >= 2 and smoke_frames >= 2 and peak_fire_conf >= 0.40) or
            # Smoke-only early warning: sustained, confident plume
            (smoke_frames >= 5 and _span(smoke_samples) >= 2.0 and peak_smoke_conf >= 0.50)
        )
        if not is_genuine:
            return 0

        latest = signal_window[-1]
        score = 0

        # ── Fire scoring (confidence-gated tiers) ──────────────────────
        if fire_frames > 0:
            best_conf = peak_fire_conf

            if best_conf > 0.85:
                score += 45   # Very high confidence — almost certainly fire
            elif best_conf >= 0.65:
                score += 35   # Confident fire
            elif best_conf >= 0.45:
                score += 30   # Clear fire — passes FIRE_RISK_GATE once recurrence is confirmed
            else:
                score += 20   # Early / low-confidence fire

        # ── Smoke scoring (more reliable, less FP-prone) ───────────────
        if smoke_frames > 0:
            score += 20       # Smoke base
            best_smoke = peak_smoke_conf
            if best_smoke > 0.60:
                score += 15   # High-confidence smoke
            elif best_smoke >= 0.35:
                score += 10   # Moderate smoke

        # ── Corroboration: fire + smoke together ───────────────────────
        has_fire = any(s.get("fire_detected") for s in signal_window)
        has_smoke = any(s.get("smoke_detected") for s in signal_window)
        if has_fire and has_smoke:
            score += 20       # Both present in window = strong corroboration

        # ── Fire area (spatial extent) ─────────────────────────────────
        if latest["fire_area_percent"] > 1.0:
            score += 10
        if latest["fire_area_percent"] > 5.0:
            score += 15

        # ── Fire GROWING (3-frame area trend) ──────────────────────────
        if len(signal_window) >= 3:
            areas = [s["fire_area_percent"] for s in signal_window[-3:]]
            if areas[0] > 0 and areas[-1] > areas[0] * config.FIRE_GROWING_THRESHOLD:
                score += 15   # Fire is spreading — very dangerous

        # ── Persistence bonus (event is sustained over time) ───────────
        first_timestamp = signal_window[0].get("_timestamp")
        latest_timestamp = latest.get("_timestamp")
        if first_timestamp is not None and latest_timestamp is not None:
            persistence_seconds = latest_timestamp - first_timestamp
            if persistence_seconds >= 1.0:
                score += 10
            if persistence_seconds >= 2.5:
                score += 15

        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        parts = []
        if signals.get("fire_detected"):
            parts.append(f"Fire detected ({signals['fire_confidence']:.0%} confidence)")
        if signals.get("smoke_detected"):
            parts.append(f"Smoke detected ({signals['smoke_confidence']:.0%} confidence)")
        parts.append(f"Fire area: {signals['fire_area_percent']:.1f}% of frame")
        parts.append(f"Duration: {duration:.1f}s")
        return " | ".join(parts)
