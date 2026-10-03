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

    # Firearm class names produced by common weapon datasets
    _GUN_WORDS = ("gun", "pistol", "rifle", "firearm", "handgun", "revolver", "shotgun", "weapon")

    @classmethod
    def _is_gun(cls, name: str) -> bool:
        n = name.lower()
        return "knife" not in n and any(w in n for w in cls._GUN_WORDS)

    @staticmethod
    def _held_by(weapon, persons):
        """Return the person whose (slightly enlarged) box contains the weapon centre."""
        wx, wy = weapon.center
        for p in persons:
            x1, y1, x2, y2 = p.bbox
            mx, my = 0.25 * (x2 - x1), 0.10 * (y2 - y1)
            if x1 - mx <= wx <= x2 + mx and y1 - my <= wy <= y2 + my:
                return p
        return None

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        persons = analysis.persons
        poses = analysis.poses
        guns = [d for d in analysis.weapon_detections
                if self._is_gun(d.class_name) and d.confidence >= 0.45]
        knives = [d for d in analysis.weapon_detections if "knife" in d.class_name.lower()]

        if not guns and not knives:
            return None

        # ── Firearms ────────────────────────────────────────────────
        # A visible gun in someone's hands is a threat on its own; a human
        # operator doesn't wait for a "shooting pose". Previously guns were
        # ignored entirely (only knives were considered).
        gun_held = False
        gun_pointed = False
        gun_holder = None
        for g in guns:
            holder = self._held_by(g, persons)
            if holder is None:
                continue
            gun_held = True
            gun_holder = holder.vg_id
            others = [p for p in persons if p is not holder]
            # Pointed: an extended arm whose wrist is near the gun, aimed toward another person
            for pose in poses:
                if pose.track_id != holder.track_id:
                    continue
                for w, sh in ((pose.left_wrist, pose.left_shoulder), (pose.right_wrist, pose.right_shoulder)):
                    if w[2] < 0.3 or sh[2] < 0.3:
                        continue
                    near_gun = ((w[0] - g.center[0]) ** 2 + (w[1] - g.center[1]) ** 2) ** 0.5 < \
                        0.25 * max(1.0, holder.bbox[3] - holder.bbox[1])
                    arm_vec = (w[0] - sh[0], w[1] - sh[1])
                    for o in others:
                        to_o = (o.center[0] - sh[0], o.center[1] - sh[1])
                        dot = arm_vec[0] * to_o[0] + arm_vec[1] * to_o[1]
                        if near_gun and dot > 0:
                            gun_pointed = True
        # Very confident gun even without a matched holder (e.g. person occluded)
        confident_gun = any(g.confidence >= 0.70 for g in guns)

        # ── Knives (only active attacks; holding a kitchen knife is normal) ──
        stabbing_motion = False
        charging_with_knife = False
        if knives and len(persons) >= 2:
            for pose in poses:
                lw, rw = pose.left_wrist, pose.right_wrist
                ls, rs = pose.left_shoulder, pose.right_shoulder
                if (lw[2] > 0.4 and ls[2] > 0.4 and lw[1] < ls[1] - 30) or \
                        (rw[2] > 0.4 and rs[2] > 0.4 and rw[1] < rs[1] - 30):
                    stabbing_motion = True
            charging_with_knife = any(p.avg_velocity > 12.0 for p in persons)
        knife_attack = stabbing_motion or charging_with_knife

        if not (gun_held or confident_gun or knife_attack):
            return None

        weapons = guns + knives
        return {
            "weapon_count": len(weapons),
            "weapon_type": "gun" if guns else "knife",
            "gun_held": gun_held,
            "gun_pointed": gun_pointed,
            "gun_holder": gun_holder,
            "stabbing_motion": stabbing_motion,
            "attack_pose": stabbing_motion,
            "charging_with_knife": charging_with_knife,
            "num_persons": len(persons),
            "max_weapon_confidence": max(w.confidence for w in weapons),
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        # Weapon must be seen repeatedly, not in a single glitch frame
        if len(signal_window) < 3:
            return 0

        score = 0
        if latest.get("weapon_type") == "gun":
            score += 55                      # Firearm in the scene
            if latest.get("gun_held"):
                score += 15                  # In someone's hands
            if latest.get("gun_pointed"):
                score += 25                  # Aimed at another person
        else:
            score += 40
            if latest.get("stabbing_motion"):
                score += 35
            if latest.get("charging_with_knife"):
                score += 30

        if latest["num_persons"] >= 2:
            score += 10
        if latest.get("max_weapon_confidence", 0) >= 0.75:
            score += 5
        return min(score, 100)

    def _build_description(self, signals, risk_score, duration):
        if signals.get("weapon_type") == "gun":
            state = "pointed at a person" if signals.get("gun_pointed") else \
                ("held by " + signals["gun_holder"]) if signals.get("gun_held") else "visible"
            return (f"ARMED THREAT: firearm {state} | Persons: {signals['num_persons']} | "
                    f"Confidence: {signals['max_weapon_confidence']:.0%} | Duration: {duration:.1f}s")
        behaviors = []
        if signals.get("stabbing_motion"): behaviors.append("Stabbing/Thrusting Motion")
        if signals.get("charging_with_knife"): behaviors.append("Charging with Knife")
        return (f"KNIFE ATTACK THREAT: {', '.join(behaviors) or 'Aggressive Action'} | "
                f"Persons: {signals['num_persons']} | "
                f"Confidence: {signals['max_weapon_confidence']:.0%} | Duration: {duration:.1f}s")
