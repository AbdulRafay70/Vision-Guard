"""
VisionGuard — Car Accident Detector
Detects vehicle collisions via sudden velocity drop and bbox overlap.
"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
from utils import bbox_iou

import config


class CarAccidentDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="car_accident", window_seconds=8.0)
        self.min_persistence = 1.5  # Accidents are sudden

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        vehicles = analysis.vehicles
        if len(vehicles) < config.ACCIDENT_MIN_VEHICLES:
            return None

        # Check for sudden velocity drops
        sudden_stops = []
        for v in vehicles:
            vels = list(v.velocities)
            if len(vels) >= 3:
                recent_avg = sum(vels[-3:]) / 3
                prev_avg = sum(vels[-6:-3]) / 3 if len(vels) >= 6 else recent_avg
                velocity_drop = prev_avg - recent_avg

                if velocity_drop > config.ACCIDENT_VELOCITY_DROP_THRESHOLD:
                    sudden_stops.append({
                        "vehicle": v.vg_id,
                        "velocity_drop": velocity_drop,
                        "current_velocity": recent_avg,
                    })

        # Check for bbox overlap between vehicles (collision)
        # ONLY count overlap if at least one vehicle had motion / sudden stop (not parked cars)
        overlapping_pairs = []
        for i in range(len(vehicles)):
            for j in range(i + 1, len(vehicles)):
                v1, v2 = vehicles[i], vehicles[j]
                v1_vels = list(v1.velocities)
                v2_vels = list(v2.velocities)
                # Both vehicles must have had active movement (> 5.0 px/frame) before collision (not stationary parked cars)
                v1_moving = len(v1_vels) >= 3 and sum(v1_vels[-3:]) / 3 > 5.0
                v2_moving = len(v2_vels) >= 3 and sum(v2_vels[-3:]) / 3 > 5.0
                
                if v1_moving and v2_moving:
                    iou = bbox_iou(v1.bbox, v2.bbox)
                    if iou > config.ACCIDENT_OVERLAP_IOU_THRESHOLD:
                        overlapping_pairs.append({
                            "vehicle1": v1.vg_id,
                            "vehicle2": v2.vg_id,
                            "iou": iou,
                        })

        # MUST have both a sudden velocity stop AND an active overlap to be an accident
        if not (sudden_stops and overlapping_pairs):
            return None

        return {
            "num_vehicles": len(vehicles),
            "sudden_stops": len(sudden_stops),
            "overlapping_pairs": len(overlapping_pairs),
            "max_velocity_drop": max((s["velocity_drop"] for s in sudden_stops), default=0),
            "max_overlap_iou": max((p["iou"] for p in overlapping_pairs), default=0),
            "vehicles_involved": [s["vehicle"] for s in sudden_stops[:2]],
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0

        # Sudden velocity drop
        if latest["sudden_stops"] > 0:
            score += 25
        if latest["max_velocity_drop"] > 25:
            score += 15

        # Vehicle overlap (collision)
        if latest["overlapping_pairs"] > 0:
            score += 30
        if latest["max_overlap_iou"] > 0.3:
            score += 15

        # Both sudden stop AND overlap = very likely accident
        if latest["sudden_stops"] > 0 and latest["overlapping_pairs"] > 0:
            score += 15

        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        involved = ", ".join(signals.get("vehicles_involved", []))
        return (
            f"Car accident detected | "
            f"{signals['num_vehicles']} vehicles | "
            f"Velocity drop: {signals['max_velocity_drop']:.1f} px/f | "
            f"Overlap IoU: {signals['max_overlap_iou']:.2f} | "
            f"Involved: {involved}"
        )
