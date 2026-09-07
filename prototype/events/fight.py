"""
VisionGuard — Fight Event Detector
Detects street fights by analyzing person proximity, pose, and arm movement.
"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import numpy as np

import config


class FightDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="fight", window_seconds=8.0)
        self.min_persistence = config.FIGHT_MIN_DURATION_SECONDS

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        persons = analysis.persons
        poses = analysis.poses

        if len(persons) < config.FIGHT_MIN_PERSONS:
            return None

        if len(persons) > 4:
            return None  # Fight is a small-group event; large groups are crowd events

        # Check proximity between persons
        close_pairs = []
        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                p1 = persons[i]
                p2 = persons[j]
                dx = p1.center[0] - p2.center[0]
                dy = p1.center[1] - p2.center[1]
                dist = (dx ** 2 + dy ** 2) ** 0.5

                # Fight requires physical contact distance (calibrated in config.py)
                if dist < config.FIGHT_PROXIMITY_THRESHOLD:
                    close_pairs.append({
                        "person1": p1.vg_id,
                        "person2": p2.vg_id,
                        "distance": dist,
                    })

        if not close_pairs:
            return None

        # Check arm velocity (rapid arm movement = potential fighting)
        rapid_arm_movement = False
        aggressive_poses = 0

        for pose in poses:
            lw = pose.left_wrist
            rw = pose.right_wrist
            ls = pose.left_shoulder
            rs = pose.right_shoulder

            # Arm raised near or above shoulders = aggressive (50px tolerance for boxing guard)
            if lw[2] > 0.3 and ls[2] > 0.3 and lw[1] < ls[1] + 50:
                aggressive_poses += 1
            if rw[2] > 0.3 and rs[2] > 0.3 and rw[1] < rs[1] + 50:
                aggressive_poses += 1

            # Wide arm spread = aggressive stance
            if pose.arm_spread > 150:
                aggressive_poses += 1

        # Check velocity of persons (fast movement toward each other)
        high_velocity_persons = sum(
            1 for p in persons if p.avg_velocity > config.FIGHT_ARM_VELOCITY_THRESHOLD
        )

        # Check for weapons in the scene
        weapon_present = len(analysis.weapon_detections) > 0
        weapon_names = [d.class_name for d in analysis.weapon_detections]

        # Neural fight verification (Day 2 — violence_classifier_best.pt)
        # The classifier confirms whether the cropped persons are actually violent.
        violence_confirmed = analysis.violence_confirmed
        violence_confidence = analysis.max_violence_confidence

        # A street fight requires MUTUAL aggressive action (aggressive_poses >= 2 AND
        # fast movement >= 2) OR a weapon OR neural violence confirmation.
        heuristic_fight = aggressive_poses >= 2 or (aggressive_poses >= 1 and high_velocity_persons >= 1)
        is_real_fight = (heuristic_fight and violence_confirmed) or weapon_present
        if not is_real_fight:
            return None

        return {
            "num_persons": len(persons),
            "close_pairs": len(close_pairs),
            "closest_distance": min(p["distance"] for p in close_pairs),
            "aggressive_poses": aggressive_poses,
            "high_velocity_persons": high_velocity_persons,
            "weapon_present": weapon_present,
            "weapon_names": weapon_names,
            "violence_confirmed": violence_confirmed,
            "violence_confidence": violence_confidence,
            "persons_involved": [cp["person1"] for cp in close_pairs[:1]] + 
                               [cp["person2"] for cp in close_pairs[:1]],
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0

        # Close proximity
        if latest["close_pairs"] > 0:
            score += 15
        if latest["closest_distance"] < 60:
            score += 10  # Very close

        # Aggressive poses (requires mutual aggressive stances: >= 2)
        if latest["aggressive_poses"] >= 2:
            score += 25
        if latest["aggressive_poses"] >= 4:
            score += 15

        # Rapid movement
        if latest["high_velocity_persons"] >= 2:
            score += 20

        # WEAPON detected during fight — major escalation
        if latest.get("weapon_present", False):
            score += 25

        # Neural violence classifier confirmation (Day 2) — strong signal
        if latest.get("violence_confirmed", False):
            score += 30
            # Scale additional confidence by classifier certainty
            conf = latest.get("violence_confidence", 0.0)
            if conf >= 0.8:
                score += 10
            elif conf >= 0.6:
                score += 5

        # Persistence bonus — fight lasting longer = more confident
        if len(signal_window) >= 5:
            score += 10
        if len(signal_window) >= 10:
            score += 10

        # Multiple persons involved
        if latest["num_persons"] >= 3:
            score += 5

        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        involved = ", ".join(signals.get("persons_involved", []))
        weapon_info = ""
        if signals.get("weapon_present", False):
            weapon_info = f" | ⚠️ WEAPON: {', '.join(signals['weapon_names'])}"
        violence_info = ""
        if signals.get("violence_confirmed", False):
            conf = signals.get("violence_confidence", 0.0)
            violence_info = f" | 🧠 Neural-confirmed violence ({conf * 100:.0f}%)"
        return (
            f"Street fight detected | "
            f"{signals['num_persons']} persons, {signals['close_pairs']} close pair(s) | "
            f"Aggressive poses: {signals['aggressive_poses']} | "
            f"Involved: {involved}{weapon_info}{violence_info} | "
            f"Duration: {duration:.1f}s"
        )
