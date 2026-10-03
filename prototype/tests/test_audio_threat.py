"""
Tests for context-aware audio threat detection.

Unit tests use hand-written YAMNet-style score dicts, so they run without
TensorFlow or Whisper:

    cd prototype && python -m pytest tests/test_audio_threat.py -q

The integration test at the bottom builds a real video with an audio track
via ffmpeg and runs it through YAMNet; it is skipped when the model or
ffmpeg is unavailable.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.audio_threat import AudioContextAnalyzer, match_distress_speech  # noqa: E402

SR = 16000


def impulse(amplitude=0.9):
    """1 s of near-silence with one sharp bang (high crest factor)."""
    w = np.random.default_rng(0).normal(0, 0.01, SR).astype(np.float32)
    w[8000:8200] = amplitude
    return w


def steady(level=0.3):
    """1 s of steady tone (low crest factor — music / engine hum)."""
    t = np.arange(SR) / SR
    return (level * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


QUIET = {"Vehicle": 0.2, "Inside, small room": 0.15}
CONCERT = {"Music": 0.8, "Singing": 0.4, "Cheering": 0.3, "Crowd": 0.3}
WEDDING = {"Music": 0.6, "Music of Bollywood": 0.4, "Crowd": 0.2}


def warm(analyzer, scores, n=5):
    for _ in range(n):
        analyzer.analyze(scores, waveform=steady(0.05))


def cats(events):
    return {e.category for e in events}


# ── Gunshots vs. fireworks ───────────────────────────────────────────

def test_gunshot_on_quiet_street_alerts():
    a = AudioContextAnalyzer()
    warm(a, QUIET)
    ev = a.analyze({**QUIET, "Gunshot, gunfire": 0.6, "Explosion": 0.5}, waveform=impulse())
    assert "gunshot" in cats(ev)


def test_bang_scoring_as_fireworks_on_quiet_street_still_alerts():
    # YAMNet often labels real gunshots "Fireworks"; without festive context
    # the bang must still be reported.
    a = AudioContextAnalyzer()
    warm(a, QUIET)
    ev = a.analyze({**QUIET, "Fireworks": 0.7, "Explosion": 0.65}, waveform=impulse())
    assert cats(ev) & {"gunshot", "explosion"}


def test_fireworks_at_wedding_suppressed():
    a = AudioContextAnalyzer()
    warm(a, WEDDING)
    ev = a.analyze({**WEDDING, "Fireworks": 0.7, "Explosion": 0.6, "Gunshot, gunfire": 0.3},
                   waveform=impulse())
    assert not ev


def test_clear_gunfire_at_concert_still_alerts():
    a = AudioContextAnalyzer()
    warm(a, CONCERT)
    ev = a.analyze({**CONCERT, "Gunshot, gunfire": 0.85, "Fireworks": 0.3}, waveform=impulse())
    assert "gunshot" in cats(ev)


def test_non_impulsive_sound_is_not_a_gunshot():
    a = AudioContextAnalyzer()
    warm(a, QUIET)
    ev = a.analyze({**QUIET, "Gunshot, gunfire": 0.6}, waveform=steady(0.5))
    assert not ev


# ── Screams ──────────────────────────────────────────────────────────

def test_sudden_scream_in_quiet_scene_alerts():
    a = AudioContextAnalyzer()
    warm(a, QUIET)
    ev = a.analyze({**QUIET, "Screaming": 0.7}, waveform=steady(0.4))
    assert "scream" in cats(ev)


def test_screaming_fans_at_concert_suppressed():
    a = AudioContextAnalyzer()
    warm(a, CONCERT)
    for _ in range(5):
        ev = a.analyze({**CONCERT, "Screaming": 0.5, "Shout": 0.5}, waveform=steady(0.4))
        assert "scream" not in cats(ev)


def test_persistent_screaming_without_music_is_baseline_not_emergency():
    # e.g. amusement-park ride: screaming is the normal soundscape
    a = AudioContextAnalyzer()
    for _ in range(10):
        a.analyze({"Screaming": 0.45}, waveform=steady(0.3))
    ev = a.analyze({"Screaming": 0.5}, waveform=steady(0.3))
    assert "scream" not in cats(ev)


def test_baby_crying_is_not_a_scream():
    a = AudioContextAnalyzer()
    warm(a, QUIET)
    ev = a.analyze({"Baby cry, infant cry": 0.67, "Crying, sobbing": 0.63}, waveform=steady(0.3))
    assert not ev


# ── Glass ────────────────────────────────────────────────────────────

def test_glass_breaking_alerts_but_cutlery_does_not():
    a = AudioContextAnalyzer()
    warm(a, QUIET)
    assert "glass" in cats(a.analyze({"Glass": 0.8, "Shatter": 0.6, "Breaking": 0.7}, waveform=impulse()))
    b = AudioContextAnalyzer()
    warm(b, QUIET)
    assert not b.analyze({"Glass": 0.45, "Chink, clink": 0.4, "Coin (dropping)": 0.7,
                          "Cutlery, silverware": 0.4}, waveform=impulse())


# ── Distress / threat speech ─────────────────────────────────────────

@pytest.mark.parametrize("text,category", [
    ("Help! Help me! Somebody help me please!", "distress_speech"),
    ("Please don't shoot! Don't hurt me!", "distress_speech"),
    ("call the police", "distress_speech"),
    ("Give me your phone right now or I will shoot you!", "threat_speech"),
    ("hands up, nobody move", "threat_speech"),
    ("he's got a gun", "weapon_speech"),
    ("bachao bachao koi madad karo", "distress_speech"),
    ("بچاؤ, بچاؤ کوئی مدد کرو", "distress_speech"),
    ("mobile do warna goli maar dunga", "threat_speech"),
])
def test_distress_phrases_detected(text, category):
    m = match_distress_speech(text)
    assert m is not None and m.category == category, (text, m)


@pytest.mark.parametrize("text", [
    "Hi, can I help you with your bags? Thanks for your help earlier.",
    "The weather is really nice today, let's go get some lunch.",
    "You killed it on stage tonight, encore!",
    "He got fired from his job last week",
    "",
])
def test_benign_speech_ignored(text):
    m = match_distress_speech(text)
    assert m is None or m.confidence < 0.5, (text, m)


def test_help_shouted_on_street_alerts_but_sung_at_concert_does_not():
    a = AudioContextAnalyzer()
    warm(a, QUIET)
    ev = a.analyze({"Speech": 0.9, "Shout": 0.4}, transcript="Help! Help me!")
    assert "distress_speech" in cats(ev)

    b = AudioContextAnalyzer()
    warm(b, CONCERT)
    ev = b.analyze({**CONCERT, "Speech": 0.2}, transcript="help me, help me, I'm falling in love")
    assert not ev


def test_transcription_only_requested_when_someone_speaks():
    a = AudioContextAnalyzer()
    assert a.wants_transcript({"Speech": 0.8})
    assert a.wants_transcript({"Screaming": 0.5})
    assert not a.wants_transcript({"Vehicle": 0.6, "Music": 0.3})


# ── Video audio monitor (playback sync, no models) ───────────────────

class _FakeClassifier:
    """Reports a gunshot for every chunk whose loudness peaks above 0.5."""
    is_loaded = True

    def load(self):
        pass

    def score_waveform(self, w, sr=SR):
        return {"Gunshot, gunfire": 0.8} if np.max(np.abs(w)) > 0.5 else {"Vehicle": 0.2}


def test_video_audio_monitor_follows_playback_position(monkeypatch):
    from ai import video_audio
    from ai.video_audio import AudioThreatProcessor, VideoAudioMonitor

    wav = np.concatenate([np.random.default_rng(1).normal(0, 0.01, SR).astype(np.float32)
                          for _ in range(6)])
    wav[3 * SR + 100: 3 * SR + 300] = 0.95                       # bang at t=3s
    monkeypatch.setattr(video_audio, "extract_audio", lambda p, sr=SR: wav)

    pos = {"t": 0.0}
    proc = AudioThreatProcessor(classifier=_FakeClassifier(), transcriber=None)
    proc.transcriber = None
    monkeypatch.setattr(proc, "load", lambda: True)
    mon = VideoAudioMonitor("fake.mp4", position_fn=lambda: pos["t"], camera_id="cam1",
                            processor=proc)
    assert mon.start()
    try:
        pos["t"] = 2.5
        time.sleep(0.5)
        assert mon.get_recent_events() == []                     # bang not reached yet
        pos["t"] = 5.5
        deadline = time.time() + 3
        while time.time() < deadline and not mon.get_recent_events():
            time.sleep(0.05)
        evs = mon.get_recent_events()
        assert evs and evs[0].category == "gunshot"
        assert evs[0].camera_id == "cam1" and 2.0 <= evs[0].media_time <= 3.0
    finally:
        mon.stop()


def test_detector_reports_speech_transcript():
    from ai.audio_threat import ThreatAudioEvent
    from events.audio_emergency import AudioEmergencyDetector

    class Mon:
        def get_recent_events(self):
            return [ThreatAudioEvent(category="threat_speech", sound_class="Threatening speech",
                                     confidence=0.9, transcript="give me your phone")]

    d = AudioEmergencyDetector(audio_monitor=Mon())
    sig = d.extract_signals(None)
    assert sig["base_risk"] == 90 and sig["transcript"] == "give me your phone"
    assert "give me your phone" in d._build_description(sig, 95, 1.0)


# ── Integration: real ffmpeg + YAMNet ────────────────────────────────

@pytest.fixture(scope="module")
def yamnet():
    pytest.importorskip("tensorflow_hub")
    from ai.audio import AudioClassifier
    c = AudioClassifier()
    c.load()
    if not c.is_loaded:
        pytest.skip("YAMNet could not be downloaded")
    return c


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_video_file_soundtrack_is_extracted_and_analyzed(tmp_path, yamnet):
    from ai.video_audio import AudioThreatProcessor, analyze_file, extract_audio

    # 8 s grey video whose soundtrack has a loud synthetic bang at 4 s
    wav = np.random.default_rng(2).normal(0, 0.005, 8 * SR).astype(np.float32)
    t = np.arange(int(0.25 * SR)) / SR
    bang = (np.random.default_rng(3).normal(0, 1, len(t)) * np.exp(-t * 30)).astype(np.float32)
    wav[4 * SR: 4 * SR + len(bang)] += np.clip(bang, -1, 1)
    raw = tmp_path / "a.f32"
    wav.tofile(raw)
    video = tmp_path / "bang.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1",
                    "-i", str(raw), "-f", "lavfi", "-i", "color=c=gray:s=160x120:r=10:d=8",
                    "-c:v", "libx264", "-c:a", "aac", "-shortest", str(video)], check=True)

    extracted = extract_audio(str(video))
    assert extracted is not None and abs(len(extracted) / SR - 8) < 0.5

    evs = analyze_file(str(video), AudioThreatProcessor(classifier=yamnet, transcriber=None))
    bangs = [e for e in evs if e.category in ("gunshot", "explosion")]
    assert bangs and all(3.0 <= e.media_time <= 5.0 for e in bangs), evs
