"""
VisionGuard — Speech transcription for distress-word spotting.

Wraps faster-whisper (CTranslate2) so suspicious words such as "help",
"bachao", "don't shoot" or "give me your phone" can be detected in a video's
audio track or the live microphone. The model is multilingual, so English,
Urdu and Roman-Urdu speech are all transcribed.

Optional dependency: ``pip install faster-whisper``. When it is missing the
transcriber stays disabled and the rest of the audio system keeps working on
sound classes only.
"""
import logging
from typing import Optional

import numpy as np

import config

logger = logging.getLogger(__name__)


class SpeechTranscriber:
    def __init__(self, model_size: Optional[str] = None, device: str = "auto"):
        self.model_size = model_size or config.AUDIO_SPEECH_MODEL
        self.device = device
        self.model = None
        self.is_loaded = False

    def load(self) -> bool:
        if self.is_loaded:
            return True
        try:
            from faster_whisper import WhisperModel
            compute = "int8"
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=compute)
            self.is_loaded = True
            logger.info("[SPEECH] Whisper '%s' loaded for distress-word spotting.", self.model_size)
        except Exception as e:
            logger.warning("[SPEECH] Speech recognition unavailable (%s). "
                           "Keyword spotting disabled.", e)
            self.is_loaded = False
        return self.is_loaded

    def transcribe(self, waveform: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe a mono float32 16 kHz waveform. Returns '' on failure."""
        if not self.is_loaded or self.model is None:
            return ""
        try:
            audio = np.asarray(waveform, dtype=np.float32)
            segments, _info = self.model.transcribe(
                audio,
                beam_size=1,
                vad_filter=False,
                condition_on_previous_text=False,
                language=config.AUDIO_SPEECH_LANGUAGE,
            )
            return " ".join(s.text.strip() for s in segments if s.no_speech_prob < 0.6).strip()
        except Exception as e:
            logger.debug("[SPEECH] Transcription error: %s", e)
            return ""
