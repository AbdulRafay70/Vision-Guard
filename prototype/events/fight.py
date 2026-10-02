"""
VisionGuard — Fight Event Detector
Detects street fights by analyzing person proximity, pose, and arm movement.
"""
from typing import Dict, List, Optional, Any
from events.base import BaseEventDetector
from ai.pipeline import FrameAnalysis
import time
import numpy as np

import config


class FightDetector(BaseEventDetector):
    """
    Fight detection modelled on how a human operator recognises a fight:
      1. Two or more people are in physical contact range — judged relative to
         their body size, not a fixed pixel distance, so it works for people
         near and far from the camera.
      2. At least one of them is striking: wrists moving fast relative to the
         body (punches/swings), or arms raised in a guard/attack posture.
      3. The behaviour repeats over a short time rather than one frame.
    The neural violence classifier, when available, strengthens the decision,
    but is no longer mandatory — previously a missing or hesitant classifier
    meant fights were never reported at all.
    """

    # Keypoint indices (COCO-17)
    _LS, _RS, _LE, _RE, _LW, _RW, _LH, _RH = 5, 6, 7, 8, 9, 10, 11, 12

    def __init__(self):
        super().__init__(event_type="fight", window_seconds=8.0)
        self.min_persistence = config.FIGHT_MIN_DURATION_SECONDS
        # Per-track wrist history: track_id -> dict(t, rel, abs, kps, speed, approach)
        self._wrist_history: Dict[int, Any] = {}

    @staticmethod
    def _body_height(bbox) -> float:
        return max(1.0, bbox[3] - bbox[1])

    def _strike_score(self, pose, now: float, partner_centre=None) -> Dict[str, float]:
        """
        Return for one pose: wrist speed relative to the torso and speed of the
        wrist *toward the nearest partner* (both in body-heights/sec), raised-arm
        posture, and whether this is a fresh pose (not a repeated cached one).
        """
        kps = pose.keypoints
        h = self._body_height(pose.bbox)
        raised = 0
        for w, sh, el in ((self._LW, self._LS, self._LE), (self._RW, self._RS, self._RE)):
            if kps[w][2] > 0.3 and kps[sh][2] > 0.3:
                # Wrist at or above shoulder level (tolerance scaled to body size)
                if kps[w][1] < kps[sh][1] + 0.08 * h:
                    raised += 1
                # Arm extended outward (punch reach) — wrist far from shoulder
                elif np.hypot(kps[w][0] - kps[sh][0], kps[w][1] - kps[sh][1]) > 0.38 * h and \
                        kps[el][2] > 0.3:
                    raised += 1

        speed = 0.0
        approach = 0.0
        tid = pose.track_id
        if tid is None:
            return {"speed": 0.0, "approach": 0.0, "raised": raised, "fresh": False}
        prev = self._wrist_history.get(tid)
        # Poses come from an async cache and repeat across frames; only measure
        # motion (and count strikes) when a genuinely new pose arrives.
        if prev is not None and np.array_equal(prev["kps"], kps):
            return {"speed": prev["speed"], "approach": prev["approach"], "raised": raised, "fresh": False}

        wr_rel = np.full((2, 2), np.nan)
        wr_abs = np.full((2, 2), np.nan)
        torso = [k for k in (self._LS, self._RS, self._LH, self._RH) if kps[k][2] > 0.3]
        if torso:
            cx = float(np.mean([kps[k][0] for k in torso]))
            cy = float(np.mean([kps[k][1] for k in torso]))
            for n, w in enumerate((self._LW, self._RW)):
                if kps[w][2] > 0.3:
                    wr_abs[n] = kps[w][:2]
                    # Relative to torso so walking doesn't count as striking
                    wr_rel[n] = [(kps[w][0] - cx) / h, (kps[w][1] - cy) / h]
        if prev is not None:
            dt = now - prev["t"]
            if 0.02 < dt < 0.6:
                d = np.linalg.norm(wr_rel - prev["rel"], axis=1)
                d = d[~np.isnan(d)]
                if d.size:
                    speed = float(d.max() / dt)
                if partner_centre is not None:
                    pc = np.asarray(partner_centre, dtype=float)
                    before = np.linalg.norm(prev["abs"] - pc, axis=1)
                    after = np.linalg.norm(wr_abs - pc, axis=1)
                    closing = (before - after) / h
                    closing = closing[~np.isnan(closing)]
                    if closing.size:
                        approach = float(closing.max() / dt)
        self._wrist_history[tid] = {"t": now, "rel": wr_rel, "abs": wr_abs, "kps": kps.copy(),
                                    "speed": speed, "approach": approach}
        return {"speed": speed, "approach": approach, "raised": raised, "fresh": True}

    def _wrist_contact(self, pose, tracks_by_id) -> int:
        """1 if an extended wrist reaches into another person's upper body (head/torso)."""
        kps = pose.keypoints
        h = self._body_height(pose.bbox)
        shoulders = [k for k in (self._LS, self._RS) if kps[k][2] > 0.3]
        if not shoulders:
            return 0
        sx = float(np.mean([kps[k][0] for k in shoulders]))
        sy = float(np.mean([kps[k][1] for k in shoulders]))
        for w in (self._LW, self._RW):
            if kps[w][2] <= 0.3:
                continue
            wx, wy = kps[w][0], kps[w][1]
            if np.hypot(wx - sx, wy - sy) < 0.30 * h:
                continue  # Arm tucked in (guard), not reaching
            for tid, other in tracks_by_id.items():
                if tid == pose.track_id:
                    continue
                x1, y1, x2, y2 = other.bbox
                # Inner 80% width, upper 55% height of the other person = head/torso
                mx = 0.1 * (x2 - x1)
                if x1 + mx < wx < x2 - mx and y1 < wy < y1 + 0.55 * (y2 - y1):
                    return 1
        return 0

    def extract_signals(self, analysis: FrameAnalysis) -> Optional[Dict[str, Any]]:
        persons = analysis.persons
        poses = analysis.poses
        now = time.time()

        if len(persons) < config.FIGHT_MIN_PERSONS or len(persons) > 6:
            return None  # Large groups are crowd events

        # Scale-aware proximity: centres closer than ~1.1x the average body height
        close_pairs = []
        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                p1, p2 = persons[i], persons[j]
                avg_h = (self._body_height(p1.bbox) + self._body_height(p2.bbox)) / 2
                dist = float(np.hypot(p1.center[0] - p2.center[0], p1.center[1] - p2.center[1]))
                # Purely relative to body size: a fixed pixel cap wrongly rejected
                # close-up subjects (e.g. ~1000px-tall people in portrait video).
                limit = 1.1 * avg_h if avg_h > 40 else config.FIGHT_PROXIMITY_THRESHOLD
                if dist < limit:
                    close_pairs.append({"person1": p1.vg_id, "person2": p2.vg_id,
                                        "t1": p1.track_id, "t2": p2.track_id,
                                        "distance": dist, "norm_distance": dist / avg_h})

        if not close_pairs:
            return None

        involved = {cp["t1"] for cp in close_pairs} | {cp["t2"] for cp in close_pairs}

        aggressive_poses = 0
        strikers = 0
        fresh_strikes = 0
        contacts = 0
        max_wrist_speed = 0.0
        tracks_by_id = {p.track_id: p for p in persons}
        partners: Dict[int, Any] = {}
        for cp in close_pairs:
            partners.setdefault(cp["t1"], tracks_by_id[cp["t2"]].center)
            partners.setdefault(cp["t2"], tracks_by_id[cp["t1"]].center)
        for pose in poses:
            st = self._strike_score(pose, now, partners.get(pose.track_id))
            if pose.track_id not in involved:
                continue  # Only people in the close pair matter
            aggressive_poses += st["raised"]
            max_wrist_speed = max(max_wrist_speed, st["speed"])
            hit = self._wrist_contact(pose, tracks_by_id)
            contacts += hit
            # A punch is a fast wrist movement that travels *toward* the other
            # person (or lands on them). Speed alone also fires on equipment
            # handling, hose jitter, gesturing, etc. Pose is sampled only a few
            # times per second, so thresholds are modest.
            is_strike = (st["speed"] > 1.0 and st["approach"] > 0.6) or hit
            if is_strike:
                strikers += 1
                if st["fresh"]:
                    fresh_strikes += 1
        # Drop wrist history for tracks that disappeared
        live = {p.track_id for p in persons}
        for tid in list(self._wrist_history):
            if tid not in live:
                del self._wrist_history[tid]

        high_velocity_persons = sum(
            1 for p in persons
            if p.track_id in involved and p.avg_velocity > config.FIGHT_ARM_VELOCITY_THRESHOLD
        )

        weapon_present = len(analysis.weapon_detections) > 0
        weapon_names = [d.class_name for d in analysis.weapon_detections]
        violence_confirmed = analysis.violence_confirmed
        violence_confidence = analysis.max_violence_confidence

        # Evidence of active fighting in this frame
        striking = strikers >= 1 or aggressive_poses >= 2 or \
            (aggressive_poses >= 1 and high_velocity_persons >= 1)
        if not (striking or violence_confirmed or weapon_present):
            return None

        return {
            "num_persons": len(persons),
            "close_pairs": len(close_pairs),
            "closest_distance": min(p["distance"] for p in close_pairs),
            "closest_norm_distance": min(p["norm_distance"] for p in close_pairs),
            "aggressive_poses": aggressive_poses,
            "strikers": strikers,
            "contacts": contacts,
            "fresh_strikes": fresh_strikes,
            "max_wrist_speed": max_wrist_speed,
            "striking": striking,
            "high_velocity_persons": high_velocity_persons,
            "weapon_present": weapon_present,
            "weapon_names": weapon_names,
            "violence_confirmed": violence_confirmed,
            "violence_confidence": violence_confidence,
            "persons_involved": [close_pairs[0]["person1"], close_pairs[0]["person2"]],
        }

    def calculate_risk(self, signal_window: List[Dict[str, Any]]) -> int:
        latest = signal_window[-1]
        n = len(signal_window)
        striking_frames = sum(1 for s in signal_window if s.get("striking"))
        violent_frames = sum(1 for s in signal_window if s.get("violence_confirmed"))
        # Distinct strike events (fresh pose updates only — cached poses repeat
        # across many frames and must not be counted as repeated punches)
        strike_frames = sum(s.get("fresh_strikes", 0) for s in signal_window)

        # Recurrence gate: one raised arm or one hug is not a fight.
        repeated_striking = striking_frames >= 4 and strike_frames >= 2
        classifier_backed = violent_frames >= 2 and striking_frames >= 2
        if not (repeated_striking or classifier_backed or latest.get("weapon_present")):
            return 0

        score = 15  # Close contact
        if latest.get("closest_norm_distance", 1.0) < 0.6:
            score += 10  # Bodies overlapping / grappling

        if strike_frames >= 2:
            score += 20  # Repeated punches/swings
        if strike_frames >= 4:
            score += 10
        if any(s.get("aggressive_poses", 0) >= 2 for s in signal_window[-5:]):
            score += 10  # Guard/attack posture
        if latest.get("high_velocity_persons", 0) >= 2:
            score += 10  # Both moving fast — mutual exchange

        if latest.get("weapon_present", False):
            score += 25

        if violent_frames:
            score += 20
            conf = max(s.get("violence_confidence", 0.0) for s in signal_window)
            if conf >= 0.8:
                score += 10
            elif conf >= 0.6:
                score += 5

        # Persistence: fraction of the window showing fight behaviour
        if n >= 5 and striking_frames / n >= 0.5:
            score += 10

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
            f"Strikers: {signals.get('strikers', 0)} | Aggressive poses: {signals['aggressive_poses']} | "
            f"Involved: {involved}{weapon_info}{violence_info} | "
            f"Duration: {duration:.1f}s"
        )

    def reset(self):
        super().reset()
        self._wrist_history.clear()
