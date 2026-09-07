"""
VisionGuard Prototype — Configuration
All thresholds, model paths, and system settings in one place.
Supports .env file for sensitive credentials via python-dotenv.
"""
import os
import logging
from pathlib import Path

# Load .env file if it exists (before reading any env vars)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; env vars must be set manually

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# THIRD-PARTY LOG NOISE SUPPRESSION
# ═══════════════════════════════════════════════════════
class _SilenceUltralyticsDeprecation(logging.Filter):
    """Drop ultralytics' per-inference "'half' is deprecated" WARNING.

    FP16 half-precision (`half=True`) is emitted as a deprecation notice by
    ultralytics on EVERY predict()/track() call. It cannot be silenced the
    usual ways:

      • warnings.filterwarnings(...)  — the notice goes through the ultralytics
        LOGGER, not Python's warnings module, so the filter never sees it.
      • logger.setLevel(ERROR)        — ultralytics calls set_logging(verbose=
        False) on each inference, resetting its own level back to WARNING.

    A logger-level filter survives those resets (set_logging only touches the
    level and handlers, never filters) and keeps console/log output readable.
    FP16 itself is unaffected — `half=` still applies on CUDA; this only hides
    the forward-compatibility notice.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "deprecated" not in record.getMessage().lower()


def _silence_third_party_noise() -> None:
    """Install the deprecation filter on the ultralytics logger (idempotent)."""
    ultra = logging.getLogger("ultralytics")
    if not any(isinstance(f, _SilenceUltralyticsDeprecation) for f in ultra.filters):
        ultra.addFilter(_SilenceUltralyticsDeprecation())


# Applied at import time so every entry point (run.py, run_web.py,
# stress_test.py, web server, data-science tools) gets clean output.
_silence_third_party_noise()

# ═══════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
EVIDENCE_DIR = BASE_DIR / "evidence"
TEST_VIDEOS_DIR = BASE_DIR / "test_videos"
TEST_AUDIO_DIR = BASE_DIR / "test_audio"

# Create directories if they don't exist
MODELS_DIR.mkdir(exist_ok=True)
EVIDENCE_DIR.mkdir(exist_ok=True)
TEST_VIDEOS_DIR.mkdir(exist_ok=True)
TEST_AUDIO_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════
# MODEL SETTINGS
# ═══════════════════════════════════════════════════════
YOLO_MODEL = "yolov8s.pt"                  # COCO pre-trained (auto-downloads)
YOLO_POSE_MODEL = "yolov8s-pose.pt"        # Pose estimation (auto-downloads)
FIRE_MODEL = str(MODELS_DIR / "fire_smoke_best.pt")  # Fine-tuned fire/smoke (optional)
FIRE_MODEL_V2 = str(MODELS_DIR / "fire_smoke_best_v2.pt")  # Fire/Smoke v2 (D-Fire trained)
VIOLENCE_MODEL = str(MODELS_DIR / "violence_classifier_best.pt")  # Fine-tuned violence classifier model
WEAPON_MODEL = str(MODELS_DIR / "weapon_detection_best.pt")  # Fine-tuned weapon detection model (Day 4)
NORMAL_SCENE_MODEL = str(MODELS_DIR / "normal_scene_verifier_best.pt")  # Normal scene context verifier

DETECTION_CONF_THRESHOLD = 0.35       # COCO detection confidence
DETECTION_IOU_THRESHOLD = 0.40             # NMS IoU threshold
DETECTION_IMG_SIZE = 480                   # Balanced 480p resolution (22+ FPS on Quadro T1000)
FIRE_IMG_SIZE = 640                   # Full resolution — fire/smoke is safety-critical
WEAPON_IMG_SIZE = 416                 # Reduced resolution for weapon model
POSE_IMG_SIZE = 416                   # Reduced resolution for pose model (faster inference)
NORMAL_SCENE_IMG_SIZE = 480           # Resolution for normal scene verifier
NORMAL_SCENE_CONF_THRESHOLD = 0.45    # Minimum confidence to confirm normal scene activity

# Requirement 9: Configurable validity windows
DISPLAY_VALIDITY_SEC = 0.750          # Max age (seconds) to show visual overlay (750ms)
EVENT_VALIDITY_SEC = 1.200            # Max age (seconds) for event rule confirmation (1200ms)

import torch
DETECTION_DEVICE = 0 if torch.cuda.is_available() else 'cpu'

# FP16 Half-Precision Inference (Day 1 — Rafay)
USE_FP16 = True if torch.cuda.is_available() else False

# Classes we care about from COCO (class_id: name)
COCO_CLASSES_OF_INTEREST = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    28: "suitcase",
    39: "bottle",
    41: "cup",
    42: "fork",
    43: "knife",
    44: "spoon",
    56: "chair",
    62: "tv",
    63: "laptop",
    64: "mouse",
    66: "keyboard",
    67: "cell phone",
    73: "book",
}

# Fire model classes (if using custom fire model)
FIRE_CLASSES = {
    0: "fire",
    1: "smoke",
}

# Weapon classes — COCO class names treated as weapons
WEAPON_CLASSES = {"knife", "gun", "pistol", "rifle", "firearm", "weapon"}

# ═══════════════════════════════════════════════════════
# WEAPON THREAT DETECTION
# ═══════════════════════════════════════════════════════
WEAPON_NEAR_PERSON_DISTANCE = 250     # Pixels — weapon bbox center to person bbox center
WEAPON_THREAT_MIN_DURATION = 0.5      # Seconds — very urgent, near-instant response

# ═══════════════════════════════════════════════════════
# TRACKING SETTINGS
# ═══════════════════════════════════════════════════════
TRACK_HIGH_THRESH = 0.5       # High confidence threshold for tracking
TRACK_LOW_THRESH = 0.1        # Low confidence threshold for tracking
TRACK_MATCH_THRESH = 0.8      # Matching threshold
TRACK_BUFFER = 30             # Frames to keep lost tracks (30 frames ≈ 1 sec at 30fps)
TRACK_FRAME_RATE = 30         # Expected frame rate

# ═══════════════════════════════════════════════════════
# POSE ESTIMATION SETTINGS
POSE_CONF_THRESHOLD = 0.25  # Lower threshold detects persons during motion blur and distance
# COCO keypoint indices
KEYPOINT_NAMES = {
    0: "nose", 1: "left_eye", 2: "right_eye",
    3: "left_ear", 4: "right_ear",
    5: "left_shoulder", 6: "right_shoulder",
    7: "left_elbow", 8: "right_elbow",
    9: "left_wrist", 10: "right_wrist",
    11: "left_hip", 12: "right_hip",
    13: "left_knee", 14: "right_knee",
    15: "left_ankle", 16: "right_ankle",
}

# ═══════════════════════════════════════════════════════
# MOTION ANALYSIS
# ═══════════════════════════════════════════════════════
MOTION_HISTORY_LENGTH = 30    # Frames of position history to keep
VELOCITY_SMOOTHING = 5        # Frames to average for velocity calculation

# ═══════════════════════════════════════════════════════
# EVENT DETECTION THRESHOLDS
# ═══════════════════════════════════════════════════════

# Temporal window (seconds of signal history for event detection)
EVENT_WINDOW_SECONDS = 5.0
EVENT_MIN_PERSISTENCE_SECONDS = 1.5  # Calibrated (Day 5 FP Analysis): raised from 1.0 to prevent duplicate alerts

# Fire Detection
FIRE_MIN_CONFIDENCE = 0.35            # Calibrated for real-world CCTV fire (0.35+ ensures continuous detection without lighting FP)
FIRE_SMOKE_MIN_CONFIDENCE = 0.35      # Catches genuine smoke plumes
FIRE_RISK_GATE = 30                   # Minimum risk score to emit a fire alert
FIRE_MIN_AREA_PERCENT = 0.2           # Catches small fires and distant smoke plumes
FIRE_MAX_AREA_PERCENT = 65.0          # Reject single-frame full-screen lighting glitches (>65% frame)
FIRE_GROWING_THRESHOLD = 1.3          # Fire area growth factor

# Car Accident Detection
ACCIDENT_VELOCITY_DROP_THRESHOLD = 15.0    # px/frame sudden velocity drop
ACCIDENT_OVERLAP_IOU_THRESHOLD = 0.15      # Bbox overlap between vehicles
ACCIDENT_MIN_VEHICLES = 2

# Bike Accident Detection
BIKE_RIDER_ANGLE_THRESHOLD = 45.0    # Degrees — rider angle from vertical
BIKE_VELOCITY_DROP_THRESHOLD = 10.0

# Fight Detection
# ── Calibrated (Day 2 — Rafay) to eliminate false positives on normal street clips.
#    Velocity raised 12→16 px/frame so ordinary walking/hand gestures do not
#    register as "high velocity"; proximity tightened so only genuine physical
#    contact distance counts. Neural violence classifier must also clear
#    VIOLENCE_CONF_THRESHOLD before a fight alert is raised.
FIGHT_PROXIMITY_THRESHOLD = 200       # Pixels — physical contact distance (balanced for portrait/landscape video)
FIGHT_ARM_VELOCITY_THRESHOLD = 16.0  # px/frame arm movement speed (calibrated from 12.0)
FIGHT_MIN_PERSONS = 2
FIGHT_MIN_DURATION_SECONDS = 3.5     # Must persist 3.5s (raised to filter transient crowd false positives)

# Violence Classifier (Day 2 — neural fight verification)
VIOLENCE_CONF_THRESHOLD = 0.70       # Min classifier confidence to confirm violence (raised to reduce false positives)
VIOLENCE_MAX_CROPS_PER_FRAME = 3     # GPU budget: max person crops classified per frame

# Robbery Detection
ROBBERY_VEHICLE_STOP_DURATION = 3.0  # Vehicle stops for 3+ sec
ROBBERY_RUSH_VELOCITY = 30.0         # Raised from 20 — normal crowd movement < 30; genuine robbery sprint > 30
ROBBERY_MIN_SUSPECTS = 2

# Kidnapping Detection
KIDNAPPING_APPROACH_VELOCITY = 15.0
KIDNAPPING_STRUGGLE_THRESHOLD = 20.0  # Pose variance indicating struggle
KIDNAPPING_FORCED_MOVEMENT_SPEED = 10.0

# Crowd Detection
CROWD_ZONE_CAPACITY = 50             # Default zone capacity
CROWD_WARNING_RATIO = 0.7            # 70% = warning
CROWD_DANGER_RATIO = 0.95            # Calibrated (Day 5 FP Analysis): raised from 0.9 to filter false crowd alarms
CROWD_HISTORY_WINDOW = 300           # 5 minutes of crowd data

# Loitering Detection
LOITER_TIME_THRESHOLD = 300          # 5 minutes (seconds) — prevents false alerts for normal standing
LOITER_MOVEMENT_THRESHOLD = 50       # Max pixels movement to count as "stationary"

# Vehicle Obstruction Detection
VEHICLE_STOP_VELOCITY_THRESHOLD = 2.0  # px/frame — essentially stopped
VEHICLE_STOP_DURATION_THRESHOLD = 10.0 # Seconds stopped

# Abandoned Object Detection
ABANDON_OBJECT_TIME_THRESHOLD = 60     # Seconds object is alone
ABANDON_PERSON_DISTANCE_THRESHOLD = 200 # Pixels — person must be this far away

# ═══════════════════════════════════════════════════════
# RISK SCORING
# ═══════════════════════════════════════════════════════
RISK_AUTO_DISPATCH_THRESHOLD = 85    # ≥ 85% = auto-dispatch
RISK_TEAM_REVIEW_THRESHOLD = 50     # 50-84% = team review
# < 50% = log only

# ═══════════════════════════════════════════════════════
# DEPARTMENT ROUTING
# ═══════════════════════════════════════════════════════
DEPARTMENT_ROUTING = {
    "fire":                 {"dept": "Fire Brigade", "dial": "16", "priority": "CRITICAL"},
    "car_accident":         {"dept": "Edhi / Rescue", "dial": "115", "priority": "CRITICAL"},
    "bike_accident":        {"dept": "Edhi / Rescue", "dial": "115", "priority": "HIGH"},
    "fight":                {"dept": "Sindh Police / Rangers", "dial": "15", "priority": "HIGH"},
    "robbery":              {"dept": "Sindh Police / Rangers", "dial": "15", "priority": "CRITICAL"},
    "kidnapping":           {"dept": "Police / CIA / Rangers", "dial": "15", "priority": "CRITICAL"},
    "weapon_threat":        {"dept": "Sindh Police / Rangers", "dial": "15", "priority": "CRITICAL"},
    "crowd_crush":          {"dept": "Disaster Management", "dial": "1122", "priority": "CRITICAL"},
    "loitering":            {"dept": "Sindh Police", "dial": "15", "priority": "LOW"},
    "vehicle_obstruction":  {"dept": "Traffic Police", "dial": "1915", "priority": "MEDIUM"},
    "abandoned_object":     {"dept": "Police / Bomb Squad", "dial": "15", "priority": "HIGH"},
    "audio_emergency":      {"dept": "Sindh Police / Rangers", "dial": "15", "priority": "CRITICAL"},
}

# ═══════════════════════════════════════════════════════
# AUDIO SETTINGS
# ═══════════════════════════════════════════════════════
AUDIO_SAMPLE_RATE = 16000           # YAMNet requires 16kHz
AUDIO_CHUNK_DURATION = 1.0          # Seconds per audio chunk
AUDIO_EMERGENCY_CLASSES = [
    "Gunshot, gunfire",
    "Explosion",
    "Screaming",
    "Glass",                         # Glass breaking
    "Crash",
    "Siren",
]
AUDIO_CONFIDENCE_THRESHOLD = 0.4

# Live microphone monitoring (Day 4 — Rafay)
# Captures audio from the microphone in a background thread and fuses
# YAMNet emergency-sound detections into the event engine.
AUDIO_ENABLED = os.environ.get("VISIONGUARD_AUDIO", "true").lower() == "true"
AUDIO_DEVICE = None                   # None = system default microphone (or int index)
AUDIO_EVENT_MEMORY_SECONDS = 5.0      # Rolling window of recent audio events kept for fusion
AUDIO_QUEUE_MAXSIZE = 8               # Microphone→classifier waveform queue depth

# ═══════════════════════════════════════════════════════
# VOICE COMMANDS (Gemini) — credentials from .env
# ═══════════════════════════════════════════════════════
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.6-flash"

# ═══════════════════════════════════════════════════════
# DISPLAY SETTINGS
# ═══════════════════════════════════════════════════════
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720
DISPLAY_FPS = 30

# Colors (BGR for OpenCV)
COLOR_PERSON = (0, 255, 0)        # Green
COLOR_VEHICLE = (255, 165, 0)     # Orange
COLOR_OBJECT = (255, 255, 0)      # Cyan
COLOR_FIRE = (0, 0, 255)          # Red
COLOR_SMOKE = (128, 128, 128)     # Gray
COLOR_EVENT = (0, 0, 255)         # Red
COLOR_SKELETON = (0, 255, 255)    # Yellow
COLOR_TRACK_ID = (255, 255, 255)  # White
COLOR_RISK_LOW = (0, 255, 0)      # Green
COLOR_RISK_MEDIUM = (0, 165, 255) # Orange
COLOR_RISK_HIGH = (0, 0, 255)     # Red

# ═══════════════════════════════════════════════════════
# WEB DASHBOARD & MULTI-CAMERA SETTINGS
# ═══════════════════════════════════════════════════════
WEB_HOST = "0.0.0.0"
WEB_PORT = 8000

# Web dashboard authentication (set via .env)
WEB_USERNAME = os.environ.get("VISIONGUARD_USER", "admin")
WEB_PASSWORD = os.environ.get("VISIONGUARD_PASS", "visionguard")

# RTSP credentials loaded from environment (never hardcoded)
_RTSP_USER = os.environ.get("RTSP_USER", "")
_RTSP_PASS = os.environ.get("RTSP_PASS", "")

# Camera sources configuration (Webcam + RTSP IP Cameras over PoE Cat6)
_default_video = (
    r"D:\testing videos\Security Camera Video of Fire at WLNE.mp4"
    if Path(r"D:\testing videos\Security Camera Video of Fire at WLNE.mp4").exists()
    else str(TEST_VIDEOS_DIR / "16669589_1920_1080_25fps.mp4")
)

CAMERAS = {
    "cam_01": {
        "id": "cam_01",
        "name": "Command Center Main Camera",
        "type": "webcam",
        "source": 0,
        "enabled": True
    },
    "cam_fire": {
        "id": "cam_fire",
        "name": "Incident Video: Fire & Explosion",
        "type": "video",
        "source": str(BASE_DIR / "Videos" / "fire.mp4"),
        "enabled": True
    },
    "cam_fight": {
        "id": "cam_fight",
        "name": "Incident Video: Street Brawl",
        "type": "video",
        "source": str(BASE_DIR / "Videos" / "fighting.mp4"),
        "enabled": True
    },
    "cam_gun": {
        "id": "cam_gun",
        "name": "Incident Video: Armed Robbery",
        "type": "video",
        "source": str(BASE_DIR / "Videos" / "gun.mp4"),
        "enabled": True
    },
    "cam_crowd": {
        "id": "cam_crowd",
        "name": "Incident Video: Crowd Gathering",
        "type": "video",
        "source": str(BASE_DIR / "Videos" / "crowded.mp4"),
        "enabled": True
    }
}


# ═══════════════════════════════════════════════════════
# AI PIPELINE SETTINGS
# ═══════════════════════════════════════════════════════
AI_PROCESS_EVERY_N_FRAMES = 2      # Process every 2nd frame — balanced speed vs detection sensitivity
FIRE_DETECT_EVERY_N_AI_FRAMES = 1    # Fire runs every AI frame — fire/smoke is safety-critical, no stagger
WEAPON_DETECT_EVERY_N_AI_FRAMES = 3  # Weapon model runs every 3rd AI frame
POSE_ONLY_WHEN_PERSONS = True       # Only run pose if persons detected
POSE_COOLDOWN_FRAMES = 2             # Pose runs every 2nd AI frame — needed for reliable fight detection
MAX_PERSONS_FOR_POSE = 10           # Full pose estimation capacity on GPU


# ═══════════════════════════════════════════════════════
# CONFIGURATION VALIDATION
# ═══════════════════════════════════════════════════════
def validate_config() -> list:
    """
    Validate configuration at startup.
    Returns a list of warning strings (empty = all good).
    """
    warnings = []

    # Check model paths
    yolo_path = Path(YOLO_MODEL)
    if not yolo_path.exists() and not yolo_path.suffix:
        # Ultralytics auto-downloads if not found, so just note it
        pass

    fire_path = Path(FIRE_MODEL)
    if not fire_path.exists():
        warnings.append(f"Fire model not found at {FIRE_MODEL}. "
                        "Fire detection will use color-based fallback only.")

    # Check thresholds are in valid ranges
    if not (0.0 < DETECTION_CONF_THRESHOLD < 1.0):
        warnings.append(f"DETECTION_CONF_THRESHOLD={DETECTION_CONF_THRESHOLD} "
                        "should be between 0.0 and 1.0")
    if not (0.0 < DETECTION_IOU_THRESHOLD < 1.0):
        warnings.append(f"DETECTION_IOU_THRESHOLD={DETECTION_IOU_THRESHOLD} "
                        "should be between 0.0 and 1.0")

    # Check RTSP URLs are valid format (when enabled)
    for cam_id, cam_info in CAMERAS.items():
        if cam_info.get("enabled") and cam_info["type"] == "rtsp":
            url = cam_info.get("source", "")
            if not url.startswith("rtsp://"):
                warnings.append(f"Camera '{cam_id}' has invalid RTSP URL: {url}")
            if "admin:admin" in url or "admin:1234" in url:
                warnings.append(f"Camera '{cam_id}' appears to use default credentials. "
                                "Set RTSP_USER and RTSP_PASS in .env file.")

    # Check API key for voice features
    if not GEMINI_API_KEY:
        warnings.append("GEMINI_API_KEY not set. Voice commands and AI narration "
                        "will use offline fallback mode.")

    return warnings
