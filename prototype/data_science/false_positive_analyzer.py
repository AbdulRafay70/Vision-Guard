"""
VisionGuard — False Positive Error Analysis & Threshold Recommender
=====================================================================
Areeba's Day 5 Task: Error analysis on false positive logs

Analyzes detection evidence, event logs, and system thresholds to:
  1. Identify patterns in false positive detections
  2. Categorize FP causes (lighting, pose ambiguity, object misclass, etc.)
  3. Recommend threshold adjustments for config.py
  4. Generate detailed error analysis report

Usage:
  python false_positive_analyzer.py --evidence-dir prototype/evidence --config prototype/config.py
  python false_positive_analyzer.py --evidence-dir prototype/evidence --output fp_analysis_report.json
"""

import os
import sys
import json
import cv2
import argparse
import logging
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FPAnalyzer")


# ═══════════════════════════════════════════════════════
# EVIDENCE FILE PARSER
# ═══════════════════════════════════════════════════════

def parse_evidence_files(evidence_dir: str) -> list:
    """
    Parse evidence screenshots to extract event type, timestamp, and metadata.
    Evidence files follow naming convention: {event_type}_{timestamp}.jpg
    """
    events = []
    evidence_path = Path(evidence_dir)
    
    if not evidence_path.exists():
        logger.warning(f"Evidence directory not found: {evidence_dir}")
        return events
    
    for file in sorted(evidence_path.glob("*.jpg")):
        # Parse filename: fight_20260825_041354.jpg
        name = file.stem
        parts = name.rsplit("_", 2)
        
        if len(parts) >= 3:
            event_type = parts[0]
            try:
                date_str = parts[1]
                time_str = parts[2]
                timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except ValueError:
                timestamp = datetime.fromtimestamp(file.stat().st_mtime)
        elif len(parts) >= 2:
            event_type = parts[0]
            timestamp = datetime.fromtimestamp(file.stat().st_mtime)
        else:
            event_type = name
            timestamp = datetime.fromtimestamp(file.stat().st_mtime)
        
        # Analyze image properties
        img = cv2.imread(str(file))
        img_info = {}
        if img is not None:
            h, w = img.shape[:2]
            img_info = {
                "resolution": f"{w}x{h}",
                "brightness": float(cv2.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))[0]),
                "file_size_kb": file.stat().st_size / 1024,
            }
        
        events.append({
            "file": str(file),
            "filename": file.name,
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
            "image_info": img_info,
        })
    
    return events


# ═══════════════════════════════════════════════════════
# THRESHOLD ANALYSIS
# ═══════════════════════════════════════════════════════

def analyze_current_thresholds(config_path: str) -> dict:
    """
    Parse config.py to extract current threshold values.
    """
    thresholds = {}
    
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found: {config_path}")
        return thresholds
    
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract threshold-related constants
    patterns = [
        (r'DETECTION_CONF_THRESHOLD\s*=\s*([\d.]+)', "detection_confidence"),
        (r'DETECTION_IOU_THRESHOLD\s*=\s*([\d.]+)', "detection_iou"),
        (r'FIRE_MIN_CONFIDENCE\s*=\s*([\d.]+)', "fire_min_confidence"),
        (r'FIRE_MIN_AREA_PERCENT\s*=\s*([\d.]+)', "fire_min_area_percent"),
        (r'FIGHT_PROXIMITY_THRESHOLD\s*=\s*([\d.]+)', "fight_proximity"),
        (r'FIGHT_ARM_VELOCITY_THRESHOLD\s*=\s*([\d.]+)', "fight_arm_velocity"),
        (r'FIGHT_MIN_DURATION_SECONDS\s*=\s*([\d.]+)', "fight_min_duration"),
        (r'ACCIDENT_VELOCITY_DROP_THRESHOLD\s*=\s*([\d.]+)', "accident_velocity_drop"),
        (r'ACCIDENT_OVERLAP_IOU_THRESHOLD\s*=\s*([\d.]+)', "accident_overlap_iou"),
        (r'ROBBERY_VEHICLE_STOP_DURATION\s*=\s*([\d.]+)', "robbery_stop_duration"),
        (r'KIDNAPPING_STRUGGLE_THRESHOLD\s*=\s*([\d.]+)', "kidnapping_struggle"),
        (r'CROWD_WARNING_RATIO\s*=\s*([\d.]+)', "crowd_warning_ratio"),
        (r'CROWD_DANGER_RATIO\s*=\s*([\d.]+)', "crowd_danger_ratio"),
        (r'LOITER_TIME_THRESHOLD\s*=\s*([\d.]+)', "loiter_time"),
        (r'WEAPON_NEAR_PERSON_DISTANCE\s*=\s*([\d.]+)', "weapon_near_person"),
        (r'WEAPON_THREAT_MIN_DURATION\s*=\s*([\d.]+)', "weapon_threat_duration"),
        (r'AUDIO_CONFIDENCE_THRESHOLD\s*=\s*([\d.]+)', "audio_confidence"),
        (r'RISK_AUTO_DISPATCH_THRESHOLD\s*=\s*([\d.]+)', "risk_auto_dispatch"),
        (r'RISK_TEAM_REVIEW_THRESHOLD\s*=\s*([\d.]+)', "risk_team_review"),
        (r'EVENT_MIN_PERSISTENCE_SECONDS\s*=\s*([\d.]+)', "event_min_persistence"),
    ]
    
    for pattern, name in patterns:
        match = re.search(pattern, content)
        if match:
            thresholds[name] = float(match.group(1))
    
    return thresholds


# ═══════════════════════════════════════════════════════
# FALSE POSITIVE PATTERN ANALYSIS
# ═══════════════════════════════════════════════════════

def categorize_fp_patterns(events: list) -> dict:
    """
    Analyze detected events and categorize potential false positive patterns.
    """
    patterns = {
        "event_frequency": Counter(),
        "temporal_clusters": [],
        "rapid_fire_alerts": [],
        "low_light_events": [],
        "high_confidence_fps": [],
        "recommendations": [],
    }
    
    # Count event types
    for evt in events:
        patterns["event_frequency"][evt["event_type"]] += 1
    
    # Find temporal clusters (multiple events within 5 seconds)
    sorted_events = sorted(events, key=lambda x: x["timestamp"])
    for i in range(len(sorted_events) - 1):
        t1 = datetime.fromisoformat(sorted_events[i]["timestamp"])
        t2 = datetime.fromisoformat(sorted_events[i + 1]["timestamp"])
        diff = (t2 - t1).total_seconds()
        
        if diff < 5.0:
            patterns["temporal_clusters"].append({
                "event_1": sorted_events[i]["filename"],
                "event_2": sorted_events[i + 1]["filename"],
                "gap_seconds": diff,
                "types": [sorted_events[i]["event_type"], sorted_events[i + 1]["event_type"]],
            })
    
    # Find rapid-fire alerts (same event type within 3 seconds)
    for i in range(len(sorted_events) - 1):
        if sorted_events[i]["event_type"] == sorted_events[i + 1]["event_type"]:
            t1 = datetime.fromisoformat(sorted_events[i]["timestamp"])
            t2 = datetime.fromisoformat(sorted_events[i + 1]["timestamp"])
            diff = (t2 - t1).total_seconds()
            if diff < 3.0:
                patterns["rapid_fire_alerts"].append({
                    "event_type": sorted_events[i]["event_type"],
                    "gap_seconds": diff,
                    "files": [sorted_events[i]["filename"], sorted_events[i + 1]["filename"]],
                })
    
    # Check for low-light events (potential false positives)
    for evt in events:
        brightness = evt.get("image_info", {}).get("brightness", 128)
        if brightness < 60:
            patterns["low_light_events"].append({
                "file": evt["filename"],
                "event_type": evt["event_type"],
                "brightness": brightness,
            })
    
    return patterns


def generate_threshold_recommendations(patterns: dict, current_thresholds: dict) -> list:
    """
    Based on FP analysis, recommend threshold adjustments.
    """
    recommendations = []
    
    freq = patterns["event_frequency"]
    
    # Check fight false positives
    if freq.get("fight", 0) > 3:
        current_proximity = current_thresholds.get("fight_proximity", 200)
        current_duration = current_thresholds.get("fight_min_duration", 2.0)
        recommendations.append({
            "parameter": "FIGHT_PROXIMITY_THRESHOLD",
            "current": current_proximity,
            "recommended": max(current_proximity - 30, 100),
            "reason": f"High fight detection count ({freq['fight']}). Tightening proximity reduces false alarms from casual passing.",
        })
        recommendations.append({
            "parameter": "FIGHT_MIN_DURATION_SECONDS",
            "current": current_duration,
            "recommended": min(current_duration + 0.5, 4.0),
            "reason": "Increasing persistence requirement filters transient pose noise.",
        })
    
    # Check crowd false positives
    if freq.get("crowd_crush", 0) > 2:
        current_ratio = current_thresholds.get("crowd_danger_ratio", 0.9)
        recommendations.append({
            "parameter": "CROWD_DANGER_RATIO",
            "current": current_ratio,
            "recommended": min(current_ratio + 0.05, 0.95),
            "reason": f"Crowd crush detected {freq['crowd_crush']} times. Raising threshold reduces sensitivity.",
        })
    
    # Check fire false positives
    if freq.get("fire", 0) > 2:
        current_fire_conf = current_thresholds.get("fire_min_confidence", 0.70)
        recommendations.append({
            "parameter": "FIRE_MIN_CONFIDENCE",
            "current": current_fire_conf,
            "recommended": min(current_fire_conf + 0.05, 0.85),
            "reason": "Multiple fire detections may include red clothing/lights. Raising confidence filters weak signals.",
        })
    
    # Check for rapid-fire duplicate alerts
    if len(patterns["rapid_fire_alerts"]) > 0:
        current_persistence = current_thresholds.get("event_min_persistence", 1.0)
        recommendations.append({
            "parameter": "EVENT_MIN_PERSISTENCE_SECONDS",
            "current": current_persistence,
            "recommended": min(current_persistence + 0.5, 3.0),
            "reason": f"Duplicate rapid-fire alerts detected ({len(patterns['rapid_fire_alerts'])} instances). Increase cooldown.",
        })
    
    # Check for low-light false positives
    if len(patterns["low_light_events"]) > 0:
        current_conf = current_thresholds.get("detection_confidence", 0.30)
        recommendations.append({
            "parameter": "DETECTION_CONF_THRESHOLD",
            "current": current_conf,
            "recommended": min(current_conf + 0.05, 0.45),
            "reason": f"{len(patterns['low_light_events'])} events in low-light conditions. Higher confidence reduces noise.",
        })
    
    # General recommendation for robbery
    if freq.get("robbery", 0) > 1:
        current_stop = current_thresholds.get("robbery_stop_duration", 3.0)
        recommendations.append({
            "parameter": "ROBBERY_VEHICLE_STOP_DURATION",
            "current": current_stop,
            "recommended": min(current_stop + 1.0, 5.0),
            "reason": "Robbery detections may include normal stops. Increasing stop duration requirement.",
        })
    
    return recommendations


# ═══════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════

def generate_report(events: list, patterns: dict, thresholds: dict, 
                    recommendations: list, output_path: str = None):
    """Generate and print the complete error analysis report."""
    
    print(f"\n{'═' * 65}")
    print(f"  📊 VISIONGUARD FALSE POSITIVE ERROR ANALYSIS REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═' * 65}")
    
    # ── Section 1: Event Summary ──
    print(f"\n  📋 EVENT SUMMARY")
    print(f"  {'─' * 50}")
    print(f"  Total evidence files analyzed: {len(events)}")
    
    freq = patterns["event_frequency"]
    for event_type, count in freq.most_common():
        print(f"    {event_type:25s}: {count} detections")
    
    # ── Section 2: Temporal Analysis ──
    print(f"\n  ⏱️  TEMPORAL ANALYSIS")
    print(f"  {'─' * 50}")
    
    if patterns["temporal_clusters"]:
        print(f"  Temporal clusters (events < 5s apart): {len(patterns['temporal_clusters'])}")
        for cluster in patterns["temporal_clusters"][:5]:
            print(f"    → {cluster['types'][0]} ↔ {cluster['types'][1]} ({cluster['gap_seconds']:.1f}s gap)")
    else:
        print(f"  ✅ No temporal clusters detected")
    
    if patterns["rapid_fire_alerts"]:
        print(f"\n  ⚠️  Rapid-fire duplicate alerts: {len(patterns['rapid_fire_alerts'])}")
        for alert in patterns["rapid_fire_alerts"][:5]:
            print(f"    → {alert['event_type']} fired twice in {alert['gap_seconds']:.1f}s")
    else:
        print(f"  ✅ No rapid-fire duplicates detected")
    
    # ── Section 3: Environmental Analysis ──
    print(f"\n  🌙 ENVIRONMENTAL ANALYSIS")
    print(f"  {'─' * 50}")
    
    if patterns["low_light_events"]:
        print(f"  ⚠️  Low-light events (brightness < 60): {len(patterns['low_light_events'])}")
        for evt in patterns["low_light_events"]:
            print(f"    → {evt['event_type']:20s} brightness={evt['brightness']:.1f}")
    else:
        print(f"  ✅ No low-light false positive concerns")
    
    # ── Section 4: Threshold Recommendations ──
    print(f"\n  🔧 THRESHOLD RECOMMENDATIONS FOR config.py")
    print(f"  {'─' * 50}")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"\n  [{i}] {rec['parameter']}")
            print(f"      Current:     {rec['current']}")
            print(f"      Recommended: {rec['recommended']}")
            print(f"      Reason:      {rec['reason']}")
    else:
        print(f"  ✅ No threshold changes recommended — current config looks good!")
    
    # ── Section 5: Current Thresholds ──
    print(f"\n  📐 CURRENT THRESHOLD VALUES")
    print(f"  {'─' * 50}")
    for name, value in sorted(thresholds.items()):
        print(f"    {name:35s}: {value}")
    
    print(f"\n{'═' * 65}")
    print(f"  End of Error Analysis Report")
    print(f"{'═' * 65}\n")
    
    # Save JSON report
    if output_path:
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_evidence_files": len(events),
            "event_frequency": dict(freq),
            "temporal_clusters": len(patterns["temporal_clusters"]),
            "rapid_fire_alerts": len(patterns["rapid_fire_alerts"]),
            "low_light_events": len(patterns["low_light_events"]),
            "current_thresholds": thresholds,
            "recommendations": recommendations,
            "events": events,
        }
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="VisionGuard False Positive Error Analysis",
    )
    parser.add_argument("--evidence-dir", type=str, 
                       default="prototype/evidence",
                       help="Path to evidence screenshots directory")
    parser.add_argument("--config", type=str,
                       default="prototype/config.py",
                       help="Path to config.py for threshold analysis")
    parser.add_argument("--output", type=str, default=None,
                       help="Save detailed JSON report to this file")
    
    args = parser.parse_args()
    
    # Parse evidence
    events = parse_evidence_files(args.evidence_dir)
    
    # Analyze thresholds
    thresholds = analyze_current_thresholds(args.config)
    
    # Categorize FP patterns
    patterns = categorize_fp_patterns(events)
    
    # Generate recommendations
    recommendations = generate_threshold_recommendations(patterns, thresholds)
    
    # Generate report
    generate_report(events, patterns, thresholds, recommendations, args.output)


if __name__ == "__main__":
    main()
