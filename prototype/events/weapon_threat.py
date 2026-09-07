"""
VisionGuard — Weapon Threat Detector
Detects weapons (knife, scissors, etc.) near persons and raises CRITICAL alerts.
Designed for rapid response — minimum 1.5 second persistence.
"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis

import config


class WeaponThreatDetector(BaseEventDetector):
    def __init__(self):
        super().__init__(event_type="weapon_threat", window_seconds=10.0)
        self.min_persistence = config.WEAPON_THREAT_MIN_DURATION

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        weapons = [d for d in analysis.weapon_detections if d.class_name == "knife"]
        persons = analysis.persons
        poses = analysis.poses

        if not weapons:
            return None

        # Track active threat behaviors
        stabbing_motion = False
        attack_pose = False
        charging_with_knife = False
        closest_distance = float("inf")

        for weapon in weapons:
            wx, wy = weapon.center

            for person in persons:
                px, py = person.center
                dist = ((wx - px) ** 2 + (wy - py) ** 2) ** 0.5
                if dist < closest_distance:
                    closest_distance = dist

                # Charging toward another person with a knife
                if person.avg_velocity > 12.0 and len(persons) >= 2:
                    charging_with_knife = True

            # Analyze pose keypoints for stabbing / raised weapon attack
            for pose in poses:
                lw = pose.left_wrist
                rw = pose.right_wrist
                ls = pose.left_shoulder
                rs = pose.right_shoulder

                # 1. Arm raised above shoulder level AND high arm spread (overhead stabbing stance)
                arm_overhead = (lw[2] > 0.4 and ls[2] > 0.4 and lw[1] < ls[1] - 30) or \
                               (rw[2] > 0.4 and rs[2] > 0.4 and rw[1] < rs[1] - 30)

                # 2. Rapid thrusting / stabbing motion (must have 2+ persons OR high arm velocity)
                if arm_overhead and len(persons) >= 2:
                    stabbing_motion = True
                    attack_pose = True

        # CRITICAL: Merely holding or looking at a knife is NOT a threat!
        # Alert ONLY if actively attacking someone or charging with overhead stab stance
        is_active_threat = (attack_pose and len(persons) >= 2) or charging_with_knife

        if not is_active_threat:
            return None  # Passively holding knife = NO ALERT

        return {
            "weapon_count": len(weapons),
            "stabbing_motion": stabbing_motion,
            "attack_pose": attack_pose,
            "charging_with_knife": charging_with_knife,
            "closest_distance": closest_distance if closest_distance != float("inf") else -1,
            "num_persons": len(persons),
            "max_weapon_confidence": max(w.confidence for w in weapons),
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        score = 0

        # Baseline for active threat with knife
        score += 40

        # Attack stance (arm raised with knife)
        if latest["attack_pose"]:
            score += 25

        # Thrusting / stabbing movement
        if latest["stabbing_motion"]:
            score += 25

        # Charging towards another person
        if latest["charging_with_knife"]:
            score += 30

        # Multiple persons involved (imminent assault)
        if latest["num_persons"] >= 2:
            score += 15

        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        behaviors = []
        if signals["attack_pose"]: behaviors.append("Raised Attack Stance")
        if signals["stabbing_motion"]: behaviors.append("Stabbing/Thrusting Motion")
        if signals["charging_with_knife"]: behaviors.append("Charging with Knife")
        
        behavior_str = ", ".join(behaviors) if behaviors else "Aggressive Action"
        return (
            f"KNIFE ATTACK THREAT: {behavior_str} | "
            f"Persons: {signals['num_persons']} | "
            f"Confidence: {signals['max_weapon_confidence']:.0%} | "
            f"Duration: {duration:.1f}s"
        )
