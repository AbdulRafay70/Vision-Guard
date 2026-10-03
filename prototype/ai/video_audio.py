"""
VisionGuard — Audio from video files.

Until now audio came only from the microphone, so a gunshot or a cry for help
inside a recorded / streamed video was never heard. This module:

  * extracts a video's soundtrack with ffmpeg (16 kHz mono float32),
  * walks through it in 1 s chunks in sync with the VideoFileSource playback
    position (handles looping and seeking),
  * runs YAMNet + optional Whisper speech recognition on each chunk, and
  * filters the results through AudioContextAnalyzer so concerts, matches,
    weddings and other noisy-but-harmless scenes don't raise alarms.

It exposes the same ``start / stop / get_recent_events`` interface as the
microphone AudioMonitor, so the EventEngine's AudioEmergencyDetector can use
either (or both via CompositeAudioMonitor).

Offline analysis / testing:

    python -m ai.video_audio Videos/gun.mp4
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np

import config
from ai.audio_threat import AudioContextAnalyzer, ThreatAudioEvent

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# Extraction
# ═══════════════════════════════════════════════════════

def extract_audio(path: str, sample_rate: int = 16000) -> Optional[np.ndarray]:
    """Decode a media file's audio track to mono float32. None if no audio."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            logger.warning("[VIDEO-AUDIO] ffmpeg not found — cannot read video audio.")
            return None
    cmd = [ffmpeg, "-nostdin", "-v", "error", "-i", str(path), "-vn",
           "-ac", "1", "-ar", str(sample_rate), "-f", "f32le", "-"]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=600, check=False)
    except Exception as e:
        logger.warning("[VIDEO-AUDIO] ffmpeg failed for %s: %s", path, e)
        return None
    if not out.stdout:
        logger.info("[VIDEO-AUDIO] %s has no audio track.", Path(path).name)
        return None
    return np.frombuffer(out.stdout, dtype=np.float32).copy()


# ═══════════════════════════════════════════════════════
# Shared chunk processor (YAMNet + speech + context)
# ═══════════════════════════════════════════════════════

class AudioThreatProcessor:
    """Turns raw audio chunks into context-validated ThreatAudioEvents."""

    def __init__(self, classifier=None, transcriber=None,
                 sample_rate: int = config.AUDIO_SAMPLE_RATE,
                 chunk_seconds: float = config.AUDIO_CHUNK_DURATION):
        from ai.audio import AudioClassifier
        self.classifier = classifier or AudioClassifier()
        self.transcriber = transcriber
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.analyzer = AudioContextAnalyzer(history_seconds=config.AUDIO_HISTORY_SECONDS,
                                             chunk_seconds=chunk_seconds)
        self._prev_tail: Optional[np.ndarray] = None   # 0.5 s overlap for impulses on chunk edges
        self._prev_chunk: Optional[np.ndarray] = None  # pre-roll so the first word isn't clipped
        self._utterance: List[np.ndarray] = []
        self._utterance_start: Optional[float] = None
        self._clock = 0.0

    def load(self) -> bool:
        if not self.classifier.is_loaded:
            self.classifier.load()
        if self.transcriber is None and config.AUDIO_SPEECH_ENABLED:
            from ai.speech import SpeechTranscriber
            self.transcriber = SpeechTranscriber()
        if self.transcriber is not None and not self.transcriber.is_loaded:
            self.transcriber.load()
        return self.classifier.is_loaded

    @property
    def speech_ready(self) -> bool:
        return self.transcriber is not None and self.transcriber.is_loaded

    def _flush_utterance(self) -> str:
        audio = np.concatenate(self._utterance)
        self._utterance, self._utterance_start = [], None
        text = self.transcriber.transcribe(audio, self.sample_rate)
        if text:
            logger.debug("[SPEECH] %s", text)
        return text

    def process(self, chunk: np.ndarray, media_time: Optional[float] = None) -> List[ThreatAudioEvent]:
        t = media_time if media_time is not None else self._clock
        self._clock = t + self.chunk_seconds

        window = chunk if self._prev_tail is None else np.concatenate([self._prev_tail, chunk])
        self._prev_tail = chunk[-len(chunk) // 2:]
        scores = self.classifier.score_waveform(window, self.sample_rate)

        # Utterance-level speech recognition: buffer while someone is talking
        # / shouting, transcribe once they stop (or after max length).
        transcript = ""
        if self.speech_ready:
            speaking = self.analyzer.wants_transcript(scores)
            if speaking:
                if not self._utterance and self._prev_chunk is not None:
                    self._utterance.append(self._prev_chunk)
                if self._utterance_start is None:
                    self._utterance_start = t
                self._utterance.append(chunk)
                if len(self._utterance) * self.chunk_seconds >= config.AUDIO_SPEECH_MAX_UTTERANCE:
                    transcript = self._flush_utterance()
            elif self._utterance:
                self._utterance.append(chunk)        # trailing word
                transcript = self._flush_utterance()
        self._prev_chunk = chunk

        return self.analyzer.analyze(scores, waveform=window, transcript=transcript,
                                     media_time=media_time)

    def finish(self, media_time: Optional[float] = None) -> List[ThreatAudioEvent]:
        """Flush any speech still buffered at end of stream."""
        if self.speech_ready and self._utterance:
            text = self._flush_utterance()
            return self.analyzer.analyze({}, transcript=text, media_time=media_time)
        return []


# ═══════════════════════════════════════════════════════
# Live monitor bound to a VideoFileSource
# ═══════════════════════════════════════════════════════

class VideoAudioMonitor:
    """Listens to a video file's soundtrack in step with its playback."""

    def __init__(self, video_path: str,
                 position_fn: Optional[Callable[[], float]] = None,
                 camera_id: Optional[str] = None,
                 processor: Optional[AudioThreatProcessor] = None):
        self.video_path = str(video_path)
        self.position_fn = position_fn
        self.camera_id = camera_id
        self.processor = processor or AudioThreatProcessor()
        self.sample_rate = self.processor.sample_rate
        self.chunk_seconds = self.processor.chunk_seconds
        self.waveform: Optional[np.ndarray] = None
        self._events: deque = deque()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self.running = False

    @classmethod
    def for_source(cls, source, camera_id: Optional[str] = None, **kw) -> "VideoAudioMonitor":
        def pos() -> float:
            fps = getattr(source, "_fps", 0.0) or 30.0
            return getattr(source, "_frame_count", 0) / fps
        return cls(str(source.file_path), position_fn=pos, camera_id=camera_id, **kw)

    def start(self) -> bool:
        self.waveform = extract_audio(self.video_path, self.sample_rate)
        if self.waveform is None or len(self.waveform) < self.sample_rate // 2:
            return False
        if not self.processor.load():
            logger.warning("[VIDEO-AUDIO] YAMNet unavailable — video audio disabled.")
            return False
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name=f"video-audio-{self.camera_id}")
        self._thread.start()
        logger.info("[VIDEO-AUDIO] Listening to %s (%.1fs of audio, speech=%s)",
                    Path(self.video_path).name, len(self.waveform) / self.sample_rate,
                    bool(self.processor.transcriber and self.processor.transcriber.is_loaded))
        return True

    def _loop(self):
        n = int(self.sample_rate * self.chunk_seconds)
        total = len(self.waveform) / self.sample_rate
        cursor = 0.0
        start_wall = time.monotonic()
        while self.running:
            pos = self.position_fn() if self.position_fn else time.monotonic() - start_wall
            if self.position_fn is None and pos > total:
                start_wall, pos = time.monotonic(), 0.0
            if pos + 2 * self.chunk_seconds < cursor:      # video looped / seeked back
                cursor = max(0.0, np.floor(pos))
            if pos - cursor > 5.0:                          # fell behind — stay real-time
                cursor = np.floor(pos) - 1.0
            if cursor + self.chunk_seconds > pos or cursor + self.chunk_seconds > total:
                time.sleep(0.1)
                continue
            i = int(cursor * self.sample_rate)
            chunk = self.waveform[i:i + n]
            try:
                events = self.processor.process(chunk, media_time=cursor)
            except Exception as e:
                logger.debug("[VIDEO-AUDIO] chunk error: %s", e)
                events = []
            cursor += self.chunk_seconds
            if events:
                self._store(events)

    def _store(self, events: List[ThreatAudioEvent]):
        now = time.time()
        with self._lock:
            for ev in events:
                ev.timestamp = now
                ev.camera_id = self.camera_id
                self._events.append(ev)
                logger.info("[VIDEO-AUDIO] 🔊 %s at %.1fs (%.0f%%)%s", ev.sound_class,
                            ev.media_time or 0, ev.confidence * 100,
                            f' "{ev.transcript}"' if ev.transcript else "")
            cutoff = now - config.AUDIO_EVENT_MEMORY_SECONDS
            while self._events and self._events[0].timestamp < cutoff:
                self._events.popleft()

    def get_recent_events(self, within_seconds: Optional[float] = None) -> List[ThreatAudioEvent]:
        within = within_seconds if within_seconds is not None else config.AUDIO_EVENT_MEMORY_SECONDS
        cutoff = time.time() - within
        with self._lock:
            return [e for e in self._events if e.timestamp >= cutoff]

    def stop(self):
        self.running = False


class CompositeAudioMonitor:
    """Merges events from the microphone and every video-file audio monitor."""

    def __init__(self):
        self._monitors: Dict[str, object] = {}
        self._lock = threading.Lock()

    def add(self, key: str, monitor) -> None:
        with self._lock:
            old = self._monitors.pop(key, None)
            self._monitors[key] = monitor
        if old is not None:
            old.stop()

    def remove(self, key: str) -> None:
        with self._lock:
            m = self._monitors.pop(key, None)
        if m is not None:
            m.stop()

    def __len__(self):
        return len(self._monitors)

    def get_recent_events(self, within_seconds: Optional[float] = None):
        with self._lock:
            mons = list(self._monitors.values())
        out = []
        for m in mons:
            try:
                out.extend(m.get_recent_events(within_seconds))
            except Exception:
                pass
        return out

    def stop(self):
        with self._lock:
            mons = list(self._monitors.values())
            self._monitors.clear()
        for m in mons:
            m.stop()


# ═══════════════════════════════════════════════════════
# Offline analysis (CLI / tests)
# ═══════════════════════════════════════════════════════

def analyze_file(path: str, processor: Optional[AudioThreatProcessor] = None) -> List[ThreatAudioEvent]:
    """Run the full pipeline over a whole video/audio file as fast as possible."""
    proc = processor or AudioThreatProcessor()
    wav = extract_audio(path, proc.sample_rate)
    if wav is None:
        return []
    if not proc.load():
        raise RuntimeError("YAMNet could not be loaded")
    n = int(proc.sample_rate * proc.chunk_seconds)
    events: List[ThreatAudioEvent] = []
    for k, i in enumerate(range(0, len(wav) - n // 2, n)):
        chunk = wav[i:i + n]
        if len(chunk) < n:
            chunk = np.pad(chunk, (0, n - len(chunk)))
        events.extend(proc.process(chunk, media_time=k * proc.chunk_seconds))
    events.extend(proc.finish(media_time=len(wav) / proc.sample_rate))
    return events


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.WARNING)
    for p in sys.argv[1:]:
        evs = analyze_file(p)
        print(f"\n=== {p}: {len(evs)} suspicious audio events ===")
        for e in evs:
            extra = f'  "{e.transcript}"' if e.transcript else ""
            print(f"  {e.media_time:6.1f}s  {e.sound_class:<20} {e.confidence:.2f}  [{e.context}]{extra}")
