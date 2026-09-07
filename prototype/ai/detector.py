"""
VisionGuard — YOLOv8 Object Detector
Detects persons, vehicles, objects, fire, and smoke using YOLOv8.
"""
import cv2
import logging
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import config

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single detection result."""
    bbox: List[float]           # [x1, y1, x2, y2]
    confidence: float           # 0.0 - 1.0
    class_id: int               # COCO class ID
    class_name: str             # Human-readable class name
    category: str               # 'person', 'vehicle', 'object', 'fire', 'smoke'
    center: tuple = field(default_factory=tuple)  # (cx, cy)
    area: float = 0.0           # Bbox area in pixels
    frame_percent: float = 0.0  # % of frame covered

    def __post_init__(self):
        x1, y1, x2, y2 = self.bbox
        self.center = ((x1 + x2) / 2, (y1 + y2) / 2)
        self.area = (x2 - x1) * (y2 - y1)


def _categorize_class(class_name: str) -> str:
    """Map class name to a high-level category."""
    if class_name == "person":
        return "person"
    elif class_name in ("car", "truck", "bus", "motorcycle", "bicycle"):
        return "vehicle"
    elif class_name in ("fire",):
        return "fire"
    elif class_name in ("smoke",):
        return "smoke"
    elif class_name in config.WEAPON_CLASSES:
        return "weapon"
    else:
        return "object"


class ObjectDetector:
    """
    YOLOv8s-based object detector.
    Loads COCO model and optionally a fire/smoke model.
    """

    def __init__(self):
        self.model: Optional[YOLO] = None
        self.fire_model: Optional[YOLO] = None
        self.violence_model: Optional[YOLO] = None
        self.weapon_model: Optional[YOLO] = None
        self._frame_area: float = 1.0

    @property
    def device(self):
        return config.DETECTION_DEVICE

    def load(self):
        """Load the YOLO models with error handling and CPU fallback."""
        try:
            logger.info("[DETECTOR] Loading YOLOv8s (COCO)...")
            from ultralytics import YOLO
            self.model = YOLO(config.YOLO_MODEL)
            # Warm up with a dummy inference to catch GPU issues early
            logger.info("[DETECTOR] COCO model loaded on device: %s", config.DETECTION_DEVICE)
        except Exception as e:
            logger.error("[DETECTOR] Failed to load COCO model: %s", e)
            if config.DETECTION_DEVICE != 'cpu':
                logger.warning("[DETECTOR] Falling back to CPU...")
                config.DETECTION_DEVICE = 'cpu'
                try:
                    from ultralytics import YOLO
                    self.model = YOLO(config.YOLO_MODEL)
                    logger.info("[DETECTOR] COCO model loaded on CPU fallback")
                except Exception as e2:
                    logger.critical("[DETECTOR] CPU fallback also failed: %s", e2)
                    raise
            else:
                raise

        # Try to load fire model if it exists
        fire_model_path = Path(config.FIRE_MODEL)
        if fire_model_path.exists():
            try:
                from ultralytics import YOLO
                logger.info("[DETECTOR] Loading fire/smoke model: %s", fire_model_path.name)
                self.fire_model = YOLO(str(fire_model_path))
                logger.info("[DETECTOR] Fire/smoke model loaded.")
            except Exception as e:
                logger.warning("[DETECTOR] Failed to load fire model: %s. Fire detection via color analysis only.", e)
        else:
            logger.info("[DETECTOR] No fire/smoke model found — fire detection via color analysis only.")

        # Try to load violence classifier model if it exists
        violence_model_path = Path(config.VIOLENCE_MODEL)
        if violence_model_path.exists():
            try:
                from ultralytics import YOLO
                logger.info("[DETECTOR] Loading violence classifier model: %s", violence_model_path.name)
                self.violence_model = YOLO(str(violence_model_path))
                logger.info("[DETECTOR] Violence classifier model loaded successfully.")
            except Exception as e:
                logger.warning("[DETECTOR] Failed to load violence model: %s", e)
                self.violence_model = None
        else:
            self.violence_model = None
            logger.info("[DETECTOR] No violence classifier model found — neural fight verification disabled.")

        # Try to load weapon detection model (Day 4)
        weapon_model_path = Path(config.WEAPON_MODEL)
        if weapon_model_path.exists():
            try:
                from ultralytics import YOLO
                logger.info("[DETECTOR] Loading weapon detection model: %s", weapon_model_path.name)
                self.weapon_model = YOLO(str(weapon_model_path))
                logger.info("[DETECTOR] Weapon detection model loaded successfully.")
            except Exception as e:
                logger.warning("[DETECTOR] Failed to load weapon model: %s", e)
                self.weapon_model = None
        else:
            self.weapon_model = None
            logger.info("[DETECTOR] No weapon detection model found — using COCO knife class only.")

        # Prefer Fire v2 when available; retain the loaded v1 model if v2 fails.
        fire_v2_path = Path(config.FIRE_MODEL_V2)
        if fire_v2_path.exists():
            try:
                from ultralytics import YOLO
                logger.info("[DETECTOR] Loading Fire/Smoke v2 model: %s", fire_v2_path.name)
                self.fire_model = YOLO(str(fire_v2_path))
                logger.info("[DETECTOR] Fire/Smoke v2 model loaded (replaces v1).")
            except Exception as e:
                logger.warning("[DETECTOR] Failed to load Fire v2 model: %s", e)

        # Load Normal Scene Verifier model (context governor)
        normal_scene_path = Path(config.NORMAL_SCENE_MODEL)
        if normal_scene_path.exists():
            try:
                from ultralytics import YOLO
                logger.info("[DETECTOR] Loading Normal Scene Verifier model: %s", normal_scene_path.name)
                self.normal_scene_model = YOLO(str(normal_scene_path))
                logger.info("[DETECTOR] Normal Scene Verifier model loaded successfully.")
            except Exception as e:
                logger.warning("[DETECTOR] Failed to load Normal Scene Verifier model: %s", e)
                self.normal_scene_model = None
        else:
            self.normal_scene_model = None
            logger.info("[DETECTOR] No Normal Scene Verifier model found.")

        logger.info("[DETECTOR] All models loaded successfully.")

    def detect_normal_scene(self, frame: np.ndarray) -> Tuple[bool, float, List[Detection]]:
        """
        Run the Normal Scene Verifier model on the frame.
        Identifies normal street activity to govern specialist workload.
        Returns (is_normal, max_confidence, detections).
        """
        if self.normal_scene_model is None:
            return False, 0.0, []

        h, w = frame.shape[:2]
        frame_area = h * w
        detections = []
        max_conf = 0.0

        try:
            results = self.normal_scene_model.predict(
                frame,
                conf=config.NORMAL_SCENE_CONF_THRESHOLD,
                imgsz=config.NORMAL_SCENE_IMG_SIZE,
                device=self.device,
                half=config.USE_FP16,
                verbose=False
            )
            for res in results:
                if res.boxes is None:
                    continue
                for box in res.boxes:
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    if conf > max_conf:
                        max_conf = conf

                    det = Detection(
                        bbox=[x1, y1, x2, y2],
                        confidence=conf,
                        class_id=0,
                        class_name="normal_street_activity",
                        category="normal_scene"
                    )
                    det.frame_percent = (det.area / frame_area) * 100.0
                    detections.append(det)

            is_normal = (max_conf >= config.NORMAL_SCENE_CONF_THRESHOLD)
            return is_normal, max_conf, detections
        except Exception as e:
            logger.error("[DETECTOR] Error in detect_normal_scene: %s", e)
            return False, 0.0, []

    def detect_fire(self, frame: np.ndarray) -> List[Detection]:
        """
        Run ONLY the fire/smoke model (or color fallback) on a frame.
        Called separately from the main tracking pass since fire uses
        a different YOLO model.
        """
        if self.model is None:
            return []

        h, w = frame.shape[:2]
        self._frame_area = h * w
        detections = []

        if self.fire_model is not None:
            # Predict at the lower of fire / smoke confidence thresholds
            min_thresh = min(config.FIRE_MIN_CONFIDENCE, config.FIRE_SMOKE_MIN_CONFIDENCE)
            fire_results = self.fire_model.predict(
                frame,
                conf=min_thresh,
                iou=config.DETECTION_IOU_THRESHOLD,
                imgsz=config.FIRE_IMG_SIZE,
                device=self.device,
                half=config.USE_FP16,  # FP16 GPU acceleration
                verbose=False,
            )

            for result in fire_results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    class_name = config.FIRE_CLASSES.get(class_id, f"fire_class_{class_id}")
                    category = _categorize_class(class_name)

                    # Class-specific confidence filtering
                    required_conf = (
                        config.FIRE_MIN_CONFIDENCE
                        if category == "fire"
                        else config.FIRE_SMOKE_MIN_CONFIDENCE
                    )
                    if confidence < required_conf:
                        continue

                    det = Detection(
                        bbox=[x1, y1, x2, y2],
                        confidence=confidence,
                        class_id=class_id + 1000,
                        class_name=class_name,
                        category=category,
                    )
                    det.frame_percent = (det.area / self._frame_area) * 100

                    # Reject implausibly large full-frame glitches (>65% frame)
                    if det.frame_percent > config.FIRE_MAX_AREA_PERCENT:
                        continue

                    # Reject vertical pillarbox borders on portrait/mobile videos
                    box_h_pct = (y2 - y1) / h
                    is_left_pillar = (x1 <= 5 and box_h_pct > 0.80)
                    is_right_pillar = (x2 >= w - 5 and box_h_pct > 0.80)
                    if is_left_pillar or is_right_pillar:
                        continue

                    detections.append(det)
        else:
            # Fallback: basic fire detection via color analysis
            fire_dets = self._detect_fire_by_color(frame)
            detections.extend(fire_dets)

        return detections

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run full detection on a frame (COCO + fire model).
        NOTE: For the main pipeline, use tracker.update() instead which
        combines detection + tracking in a single model.track() pass.
        This method is kept for backward compatibility and standalone use.
        """
        if self.model is None:
            return []

        h, w = frame.shape[:2]
        self._frame_area = h * w

        detections = []

        # Run COCO model
        results = self.model.predict(
            frame,
            conf=config.DETECTION_CONF_THRESHOLD,
            iou=config.DETECTION_IOU_THRESHOLD,
            imgsz=config.DETECTION_IMG_SIZE,
            device=self.device,
            half=config.USE_FP16,  # FP16 GPU acceleration
            verbose=False,
        )

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                if class_id in config.COCO_CLASSES_OF_INTEREST:
                    class_name = config.COCO_CLASSES_OF_INTEREST[class_id]
                    category = _categorize_class(class_name)

                    det = Detection(
                        bbox=[x1, y1, x2, y2],
                        confidence=confidence,
                        class_id=class_id,
                        class_name=class_name,
                        category=category,
                    )
                    det.frame_percent = (det.area / self._frame_area) * 100
                    detections.append(det)

        # Add fire/smoke detections
        detections.extend(self.detect_fire(frame))
        return detections

    def _detect_fire_by_color(self, frame: np.ndarray) -> List[Detection]:
        """
        Basic fire detection using color thresholds (HSV).
        This is a FALLBACK when no fire YOLO model is available.
        Not as accurate as a trained model, but catches obvious flames.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, w = frame.shape[:2]

        # Fire color range in HSV
        lower_fire = np.array([0, 120, 200])
        upper_fire = np.array([40, 255, 255])
        mask = cv2.inRange(hsv, lower_fire, upper_fire)

        # Remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        fire_dets = []
        for contour in contours:
            area = cv2.contourArea(contour)
            frame_percent = (area / self._frame_area) * 100

            # Only consider significant fire regions
            if frame_percent >= config.FIRE_MIN_AREA_PERCENT:
                x, y, cw, ch = cv2.boundingRect(contour)
                det = Detection(
                    bbox=[float(x), float(y), float(x + cw), float(y + ch)],
                    confidence=min(0.5 + frame_percent * 0.05, 0.85),  # Estimated confidence
                    class_id=1000,
                    class_name="fire",
                    category="fire",
                )
                det.frame_percent = frame_percent
                fire_dets.append(det)

        return fire_dets

    def get_persons(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to persons only."""
        return [d for d in detections if d.category == "person"]

    def get_vehicles(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to vehicles only."""
        return [d for d in detections if d.category == "vehicle"]

    def get_fire_smoke(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to fire/smoke only."""
        return [d for d in detections if d.category in ("fire", "smoke")]

    def get_objects(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to general objects."""
        return [d for d in detections if d.category == "object"]

    # ── Violence Classifier (Day 2 — Neural Fight Verification) ─────────────

    def classify_violence(self, frame: np.ndarray, bbox: List[float]) -> Dict[str, Any]:
        """
        Classify a person crop using the violence_classifier_best.pt model.
        Returns {'is_violent': bool, 'confidence': float, 'class_name': str}.

        This provides neural verification for fight detection — reduces false
        positives by confirming aggressive poses with a trained classifier.
        """
        if not hasattr(self, 'violence_model') or self.violence_model is None:
            return {"is_violent": False, "confidence": 0.0, "class_name": "unknown", "available": False}

        try:
            # Crop person region from frame
            x1, y1, x2, y2 = [int(v) for v in bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 <= x1 or y2 <= y1:
                return {"is_violent": False, "confidence": 0.0, "class_name": "invalid_crop", "available": True}

            crop = frame[y1:y2, x1:x2]

            # Resize to classifier input size (224x224)
            crop_resized = cv2.resize(crop, (224, 224))

            # Run violence classifier
            results = self.violence_model.predict(
                crop_resized,
                device=self.device,
                half=config.USE_FP16,
                verbose=False,
            )

            if results and len(results) > 0:
                result = results[0]
                # Classification model returns probs
                if hasattr(result, 'probs') and result.probs is not None:
                    top_idx = int(result.probs.top1)
                    top_conf = float(result.probs.top1conf)
                    class_name = result.names.get(top_idx, f"class_{top_idx}")

                    # Classes: 0=non_violent, 1=violent (typical for binary classifier)
                    # Apply calibrated confidence gate (Day 2) to suppress false positives.
                    is_violent = (
                        "violen" in class_name.lower()
                        and "non" not in class_name.lower()
                        and top_conf >= config.VIOLENCE_CONF_THRESHOLD
                    )
                    return {
                        "is_violent": is_violent,
                        "confidence": top_conf,
                        "class_name": class_name,
                        "available": True,
                    }

            return {"is_violent": False, "confidence": 0.0, "class_name": "unknown", "available": True}

        except Exception as e:
            logger.debug("[VIOLENCE] Classification error: %s", e)
            return {"is_violent": False, "confidence": 0.0, "class_name": "error", "available": False}

    def classify_violence_batch(self, frame: np.ndarray, bboxes: List[List[float]]) -> List[Dict[str, Any]]:
        """
        Batch violence classification — processes multiple person crops in a single
        model.predict() call to eliminate per-crop YOLO launch overhead.
        """
        if not hasattr(self, 'violence_model') or self.violence_model is None:
            return [{"is_violent": False, "confidence": 0.0, "class_name": "unknown", "available": False}
                    for _ in bboxes]

        if not bboxes:
            return []

        try:
            h, w = frame.shape[:2]
            crops = []
            valid_indices = []

            for i, bbox in enumerate(bboxes):
                x1, y1, x2, y2 = [int(v) for v in bbox]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                if x2 <= x1 or y2 <= y1:
                    continue

                crop = frame[y1:y2, x1:x2]
                crop_resized = cv2.resize(crop, (224, 224))
                crops.append(crop_resized)
                valid_indices.append(i)

            if not crops:
                return [{"is_violent": False, "confidence": 0.0, "class_name": "invalid_crop", "available": True}
                        for _ in bboxes]

            # Single batched inference call
            results = self.violence_model.predict(
                crops,
                device=self.device,
                half=config.USE_FP16,
                verbose=False,
            )

            # Build results for all bboxes
            all_results = [{"is_violent": False, "confidence": 0.0, "class_name": "invalid_crop", "available": True}
                           for _ in bboxes]

            for result_idx, bbox_idx in enumerate(valid_indices):
                if result_idx < len(results):
                    result = results[result_idx]
                    if hasattr(result, 'probs') and result.probs is not None:
                        top_idx = int(result.probs.top1)
                        top_conf = float(result.probs.top1conf)
                        class_name = result.names.get(top_idx, f"class_{top_idx}")

                        is_violent = (
                            "violen" in class_name.lower()
                            and "non" not in class_name.lower()
                            and top_conf >= config.VIOLENCE_CONF_THRESHOLD
                        )
                        all_results[bbox_idx] = {
                            "is_violent": is_violent,
                            "confidence": top_conf,
                            "class_name": class_name,
                            "available": True,
                        }

            return all_results

        except Exception as e:
            logger.debug("[VIOLENCE] Batch classification error: %s", e)
            return [{"is_violent": False, "confidence": 0.0, "class_name": "error", "available": False}
                    for _ in bboxes]

    def detect_weapons(self, frame: np.ndarray) -> List[Detection]:
        """
        Run the weapon detection model (weapon_detection_best.pt) on a frame.
        Detects knives, pistols, rifles, and other firearms.
        """
        if not hasattr(self, 'weapon_model') or self.weapon_model is None:
            return []

        try:
            results = self.weapon_model.predict(
                frame,
                conf=config.DETECTION_CONF_THRESHOLD,
                iou=config.DETECTION_IOU_THRESHOLD,
                imgsz=config.WEAPON_IMG_SIZE,
                device=self.device,
                half=config.USE_FP16,
                verbose=False,
            )

            detections = []
            h, w = frame.shape[:2]
            frame_area = h * w

            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    class_name = result.names.get(class_id, f"weapon_{class_id}")
                    det = Detection(
                        bbox=[x1, y1, x2, y2],
                        confidence=confidence,
                        class_id=class_id + 2000,  # Offset to avoid COCO collision
                        class_name=class_name,
                        category="weapon",
                    )
                    det.frame_percent = (det.area / frame_area) * 100
                    detections.append(det)

            return detections
        except Exception as e:
            logger.debug("[WEAPON] Detection error: %s", e)
            return []
