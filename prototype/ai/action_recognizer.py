"""
VisionGuard — Temporal Action Recognizer (clip-based fight recognition)

Why this exists
---------------
Per-frame cues (pose snapshots, single-crop classifiers) cannot reliably tell
a fight from hugging, sport, dancing or a firefighter handling a hose — a human
recognises a fight from *motion over time*. This module classifies short video
clips (~2 s, 16 frames) of the people involved with a 3D-CNN, which is the
standard approach used by professional video-analytics systems.

Models
------
1. Fine-tuned fight model (preferred): ``config.FIGHT_ACTION_MODEL``
   (``models/fight_action_best.pt``), produced by
   ``data_science/train_fight_action.py`` on CCTV fight datasets
   (e.g. RWF-2000). Binary head: [non_fight, fight].
2. Fallback: torchvision S3D pre-trained on Kinetics-400 (auto-downloads).
   Fight probability = summed probability of the violent Kinetics actions
   (punching person, slapping, headbutting, wrestling, kicks...). Works
   without any training, strongest on boxing-style exchanges; weaker on
   ground beatings, which the fine-tuned model is meant to cover.
"""
import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

import config

logger = logging.getLogger(__name__)

# Kinetics-400 classes that indicate physical violence
_VIOLENT_KINETICS = [
    "punching person (boxing)", "slapping", "headbutting", "wrestling",
    "drop kicking", "side kick", "high kick", "sword fighting",
]

_MEAN = np.array([0.43216, 0.394666, 0.37645], dtype=np.float32)
_STD = np.array([0.22803, 0.22145, 0.216989], dtype=np.float32)

CLIP_FRAMES = 16          # frames per clip
CLIP_SECONDS = 2.0        # temporal span covered by one clip
INPUT_SIZE = 224


class FrameHistory:
    """Thread-safe ring buffer of recent downscaled frames with timestamps."""

    def __init__(self, seconds: float = CLIP_SECONDS + 0.5, max_side: int = 640):
        self._buf: deque = deque()
        self._seconds = seconds
        self._max_side = max_side
        self._lock = threading.Lock()
        self.scale = 1.0

    def push(self, frame: np.ndarray, ts: float):
        h, w = frame.shape[:2]
        scale = min(1.0, self._max_side / max(h, w))
        small = cv2.resize(frame, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_AREA) if scale < 1.0 else frame.copy()
        with self._lock:
            self.scale = scale
            self._buf.append((ts, small))
            while self._buf and ts - self._buf[0][0] > self._seconds:
                self._buf.popleft()

    def sample(self, n: int = CLIP_FRAMES, span: float = CLIP_SECONDS) -> Tuple[List[np.ndarray], float]:
        """Return n frames evenly spaced over the last `span` seconds (and the scale)."""
        with self._lock:
            items = list(self._buf)
            scale = self.scale
        if len(items) < 4:
            return [], scale
        t_end = items[-1][0]
        if t_end - items[0][0] < span * 0.6:
            return [], scale  # Not enough history yet
        targets = np.linspace(t_end - span, t_end, n)
        times = np.array([t for t, _ in items])
        idx = [int(np.argmin(np.abs(times - t))) for t in targets]
        return [items[i][1] for i in idx], scale

    def clear(self):
        with self._lock:
            self._buf.clear()


class ActionRecognizer:
    def __init__(self):
        self.model = None
        self.mode = "disabled"      # "finetuned" | "kinetics" | "disabled"
        self._violent_idx: List[int] = []
        self._torch = None
        self._device = "cpu"
        self._half = False

    def load(self):
        try:
            import torch
            from torchvision.models.video import s3d, S3D_Weights
        except Exception as e:
            logger.warning("[ACTION] torch/torchvision unavailable — clip fight recognition disabled: %s", e)
            return
        self._torch = torch
        self._device = "cuda" if (config.DETECTION_DEVICE != "cpu" and torch.cuda.is_available()) else "cpu"
        self._half = self._device == "cuda" and config.USE_FP16

        ft_path = Path(getattr(config, "FIGHT_ACTION_MODEL", ""))
        try:
            if ft_path.is_file():
                model = s3d(weights=None, num_classes=2)
                state = torch.load(str(ft_path), map_location="cpu")
                model.load_state_dict(state.get("model", state))
                self.mode = "finetuned"
                logger.info("[ACTION] Loaded fine-tuned fight model: %s", ft_path.name)
            else:
                weights = S3D_Weights.KINETICS400_V1
                model = s3d(weights=weights)
                cats = weights.meta["categories"]
                self._violent_idx = [cats.index(c) for c in _VIOLENT_KINETICS if c in cats]
                self.mode = "kinetics"
                logger.info("[ACTION] Loaded Kinetics-400 S3D (zero-shot fight recognition). "
                            "Train models/fight_action_best.pt for CCTV-grade accuracy.")
            model.eval().to(self._device)
            if self._half:
                model.half()
            self.model = model
            # Warm-up
            self.predict([np.zeros((INPUT_SIZE, INPUT_SIZE, 3), np.uint8)] * CLIP_FRAMES)
        except Exception as e:
            logger.warning("[ACTION] Failed to load action model — disabled: %s", e)
            self.model = None
            self.mode = "disabled"

    @staticmethod
    def square_crop_box(boxes: List[List[float]], frame_shape, pad: float = 1.15):
        """Square region (x1, y1, x2, y2) covering all given boxes, clipped to the frame."""
        H, W = frame_shape[:2]
        x1 = min(b[0] for b in boxes); y1 = min(b[1] for b in boxes)
        x2 = max(b[2] for b in boxes); y2 = max(b[3] for b in boxes)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        side = min(max(x2 - x1, y2 - y1) * pad, max(H, W))
        sx = max(0.0, min(W - side, cx - side / 2)) if side <= W else 0.0
        sy = max(0.0, min(H - side, cy - side / 2)) if side <= H else 0.0
        return int(sx), int(sy), int(min(W, sx + side)), int(min(H, sy + side))

    def predict(self, frames: List[np.ndarray], box=None) -> Optional[float]:
        """Fight probability (0..1) for a clip; `box` crops the region of interest."""
        if self.model is None or not frames:
            return None
        torch = self._torch
        clip = []
        for f in frames:
            if box is not None:
                x1, y1, x2, y2 = box
                f = f[y1:y2, x1:x2]
                if f.size == 0:
                    return None
            f = cv2.resize(f, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)
            clip.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        x = (np.stack(clip).astype(np.float32) / 255.0 - _MEAN) / _STD     # T,H,W,C
        x = torch.from_numpy(x).permute(3, 0, 1, 2).unsqueeze(0).to(self._device)  # 1,C,T,H,W
        if self._half:
            x = x.half()
        with torch.no_grad():
            probs = self.model(x).float().softmax(-1)[0]
        if self.mode == "finetuned":
            return float(probs[1])
        return float(probs[self._violent_idx].sum())


def _selftest():  # pragma: no cover - manual check
    r = ActionRecognizer(); r.load()
    t = time.time()
    p = r.predict([np.zeros((300, 300, 3), np.uint8)] * CLIP_FRAMES)
    print(r.mode, p, f"{time.time() - t:.2f}s")


if __name__ == "__main__":
    _selftest()
