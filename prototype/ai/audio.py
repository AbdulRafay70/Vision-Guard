"""
VisionGuard — Audio Emergency Classifier
Uses Google's YAMNet model to classify audio streams in real-time.
Detects gunshots, explosions, screams, crashes, glass breaking, and sirens.

Day 4 (Rafay): Added AudioMonitor — a background microphone listener thread
that captures live audio, runs YAMNet classification, and maintains a rolling
window of emergency sound events for fusion into the event engine.
"""
import logging
import numpy as np
import queue
import threading
import time
from collections import deque
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import config

logger = logging.getLogger(__name__)


@dataclass
class AudioEvent:
    """A detected emergency sound event."""
    sound_class: str             # 'Gunshot', 'Explosion', 'Screaming', etc.
    confidence: float            # 0.0 - 1.0
    timestamp: float = field(default_factory=time.time)
    duration: float = 1.0        # Duration of sound window in seconds


class AudioClassifier:
    """
    YAMNet-based audio event classifier.
    Pre-trained on AudioSet (521 sound classes).
    """

    def __init__(self):
        self.yamnet_model = None
        self.class_names = []
        self.is_loaded = False

    def load(self):
        """Load YAMNet model from TensorFlow Hub."""
        logger.info("[AUDIO] Loading YAMNet sound classification model...")
        try:
            import tensorflow as tf
            import tensorflow_hub as hub

            self.yamnet_model = hub.load('https://tfhub.dev/google/yamnet/1')

            # Get class map
            class_map_path = self.yamnet_model.class_map_path().numpy()
            import csv
            with open(class_map_path) as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                self.class_names = [row[2] for row in reader]

            self.is_loaded = True
            logger.info("[AUDIO] YAMNet model loaded successfully.")
        except Exception as e:
            logger.error("[AUDIO] Failed to load YAMNet: %s. Audio detection disabled.", e)
            self.is_loaded = False

    def classify_waveform(self, waveform: np.ndarray, sample_rate: int = 16000) -> List[AudioEvent]:
        """
        Classify a 1D audio waveform array (mono, 16kHz float32 between -1.0 and 1.0).
        Returns detected emergency sound events.
        """
        if not self.is_loaded or self.yamnet_model is None:
            return []

        # Ensure correct dtype
        waveform = np.asarray(waveform, dtype=np.float32)

        # Run YAMNet model
        scores, embeddings, spectrogram = self.yamnet_model(waveform)
        scores_np = scores.numpy()

        # Average prediction across frames in this audio window
        mean_scores = scores_np.mean(axis=0)

        events = []
        for class_idx, score in enumerate(mean_scores):
            if score >= config.AUDIO_CONFIDENCE_THRESHOLD:
                name = self.class_names[class_idx]

                # Check if this class matches an emergency sound category
                for emergency_keyword in config.AUDIO_EMERGENCY_CLASSES:
                    if emergency_keyword.lower() in name.lower():
                        events.append(AudioEvent(
                            sound_class=name,
                            confidence=float(score),
                            timestamp=time.time()
                        ))
                        break

        return events


class AudioMonitor:
    """
    Live microphone listener (Day 4 — Rafay).

    Architecture:
    - A sounddevice RawInputStream callback captures mono 16kHz float32 audio
      in fixed-duration chunks and pushes them onto a bounded queue (the callback
      stays lightweight to avoid audio dropouts).
    - A background daemon worker thread pops waveforms, runs YAMNet
      classification, and appends detected emergency sounds to a rolling window.
    - get_recent_events() exposes the freshest events for fusion into the
      EventEngine (gunshot / explosion / scream / crash alerts).

    Degrades gracefully: if TensorFlow/YAMNet or sounddevice is unavailable, or
    no microphone is present, start() returns False and the monitor stays inert.
    """

    def __init__(self, classifier: Optional[AudioClassifier] = None,
                 device: Optional[int] = None,
                 chunk_seconds: Optional[float] = None,
                 sample_rate: Optional[int] = None):
        self.classifier = classifier or AudioClassifier()
        self.device = device if device is not None else config.AUDIO_DEVICE
        self.sample_rate = sample_rate or config.AUDIO_SAMPLE_RATE
        self.chunk_seconds = chunk_seconds or config.AUDIO_CHUNK_DURATION
        self._chunk_samples = int(self.sample_rate * self.chunk_seconds)

        self._events: deque = deque()
        self._lock = threading.Lock()
        self._audio_q: "queue.Queue" = queue.Queue(maxsize=config.AUDIO_QUEUE_MAXSIZE)
        self._thread: Optional[threading.Thread] = None
        self._stream = None
        self._sd = None
        self.running: bool = False

    def start(self) -> bool:
        """Load YAMNet (if needed) and open the microphone listener thread."""
        if not self.classifier.is_loaded:
            self.classifier.load()
        if not self.classifier.is_loaded:
            logger.warning("[AUDIO] YAMNet unavailable — microphone monitor not started.")
            return False

        try:
            import sounddevice as sd
            self._sd = sd
        except Exception as e:
            logger.error("[AUDIO] sounddevice not installed: %s. Microphone disabled.", e)
            return False

        try:
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self._chunk_samples,
                device=self.device,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.error("[AUDIO] Failed to open microphone: %s. Audio fusion disabled.", e)
            self._stream = None
            return False

        self.running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True,
                                        name="audio-monitor")
        self._thread.start()
        logger.info("[AUDIO] Microphone listener started (device=%s, %.1fs chunks @ %dHz)",
                    self.device, self.chunk_seconds, self.sample_rate)
        return True

    def _audio_callback(self, indata, frames, time_info, status):
        """Lightweight sounddevice callback — enqueue raw waveform for the worker."""
        if status:
            logger.debug("[AUDIO] Stream status: %s", status)
        try:
            waveform = np.copy(indata[:, 0]).astype(np.float32)
            if self._audio_q.full():
                # Drop the oldest chunk to keep latency low (real-time priority)
                try:
                    self._audio_q.get_nowait()
                except queue.Empty:
                    pass
            self._audio_q.put_nowait(waveform)
        except Exception as e:
            logger.debug("[AUDIO] Callback error: %s", e)

    def _process_loop(self):
        """Background worker: classify queued waveforms and store emergency events."""
        while self.running:
            try:
                waveform = self._audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            except Exception:
                break

            try:
                events = self.classifier.classify_waveform(waveform, self.sample_rate)
            except Exception as e:
                logger.debug("[AUDIO] Classification error: %s", e)
                continue

            if events:
                now = time.time()
                with self._lock:
                    for ev in events:
                        self._events.append(ev)
                    cutoff = now - config.AUDIO_EVENT_MEMORY_SECONDS
                    while self._events and self._events[0].timestamp < cutoff:
                        self._events.popleft()
                for ev in events:
                    logger.info("[AUDIO] 🔊 Emergency sound: %s (%.0f%%)",
                                ev.sound_class, ev.confidence * 100)

    def get_recent_events(self, within_seconds: Optional[float] = None) -> List[AudioEvent]:
        """Return emergency sound events detected within the recent window."""
        within = within_seconds if within_seconds is not None else config.AUDIO_EVENT_MEMORY_SECONDS
        cutoff = time.time() - within
        with self._lock:
            return [e for e in self._events if e.timestamp >= cutoff]

    def stop(self):
        """Stop the listener thread and close the microphone stream."""
        self.running = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception as e:
            logger.debug("[AUDIO] Stream close error: %s", e)
        self._stream = None
        logger.info("[AUDIO] Microphone listener stopped.")
