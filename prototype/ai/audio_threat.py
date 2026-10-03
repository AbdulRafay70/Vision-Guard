"""
VisionGuard — Context-Aware Audio Threat Analysis

Raw YAMNet labels are not enough to raise a police alert: people scream on
roller-coasters, crowds shout at concerts and cricket matches, and fireworks
at a wedding sound a lot like gunfire. This module turns per-chunk YAMNet
scores (plus optional speech transcripts) into *threat* events by weighing
each emergency sound against its acoustic context:

  1. Scene context  — music / singing / cheering / applause / children playing
                      and fireworks are tracked over a rolling window.
  2. Anomaly        — a scream only counts if it stands out from the scene's
                      own recent baseline (a constantly screaming crowd is a
                      festival, a sudden scream in a quiet street is not).
  3. Impulse check  — gunshot candidates must be impulsive (high crest factor)
                      and must outscore fireworks/firecracker labels.
  4. Distress speech— transcribed speech is matched against a bilingual
                      (English + Urdu / Roman Urdu) lexicon of calls for help,
                      threats and weapon mentions. Lyrics-like or benign
                      phrasing ("can I help you", "help me with...") is damped.

Everything here is pure Python + numpy so it can be unit-tested without
TensorFlow or Whisper installed.
"""
from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import numpy as np


# ═══════════════════════════════════════════════════════
# Events
# ═══════════════════════════════════════════════════════

@dataclass
class ThreatAudioEvent:
    """A context-validated suspicious audio event."""
    category: str                 # gunshot | explosion | scream | glass | crash | distress_speech | threat_speech | weapon_speech
    sound_class: str              # Human readable label shown in alerts
    confidence: float             # 0.0 - 1.0 after context adjustment
    timestamp: float = field(default_factory=time.time)
    media_time: Optional[float] = None   # Seconds into the video (video sources only)
    duration: float = 1.0
    transcript: str = ""
    matched_phrases: List[str] = field(default_factory=list)
    context: str = ""             # e.g. "music 0.62, cheering 0.40"
    camera_id: Optional[str] = None


# Kept for backwards compatibility with code that imports AudioEvent semantics.
SUSPICIOUS_CATEGORIES = (
    "gunshot", "explosion", "scream", "glass", "crash",
    "distress_speech", "threat_speech", "weapon_speech",
)


# ═══════════════════════════════════════════════════════
# YAMNet label groups (AudioSet ontology display names)
# ═══════════════════════════════════════════════════════

LABEL_GROUPS: Dict[str, Tuple[str, ...]] = {
    "gunshot":   ("Gunshot, gunfire", "Machine gun", "Fusillade", "Artillery fire", "Cap gun"),
    "explosion": ("Explosion", "Boom"),
    "fireworks": ("Fireworks", "Firecracker"),
    "scream":    ("Screaming", "Wail, moan", "Crying, sobbing"),
    "baby":      ("Baby cry, infant cry", "Baby laughter", "Child speech, kid speaking"),
    "shout":     ("Shout", "Yell", "Bellow", "Battle cry"),
    "glass":     ("Glass", "Shatter"),
    "breaking":  ("Shatter", "Breaking"),
    "clinks":    ("Coin (dropping)", "Cash register", "Cutlery, silverware", "Dishes, pots, and pans",
                  "Keys jangling"),
    "crash":     ("Smash, crash", "Crash", "Breaking"),
    "speech":    ("Speech", "Conversation", "Narration, monologue", "Shout", "Yell"),
    # Benign / festive context
    "music":     ("Music", "Musical instrument", "Pop music", "Rock music", "Drum",
                  "Drum kit", "Bass drum", "Electronic music", "Dance music",
                  "Music of Bollywood", "Music of Asia", "Guitar", "Singing",
                  "Choir", "Song", "Rapping", "Hip hop music"),
    "crowd":     ("Cheering", "Applause", "Crowd", "Clapping", "Hubbub, speech noise, speech babble",
                  "Children shouting", "Children playing", "Laughter", "Chant", "Whoop"),
}

# Keywords that, when present in the matched YAMNet label, should not be
# counted as the group (e.g. "Glass" also matches "Chink, clink" family names).
_EXCLUDE: Dict[str, Tuple[str, ...]] = {
    "glass": ("Glass harmonica",),
}


def group_score(scores: Dict[str, float], group: str) -> float:
    """Max YAMNet score over every label belonging to ``group``."""
    names = LABEL_GROUPS[group]
    excl = _EXCLUDE.get(group, ())
    best = 0.0
    for label, s in scores.items():
        if label in excl:
            continue
        for n in names:
            if label == n or (len(n) > 4 and n.lower() in label.lower()):
                if s > best:
                    best = s
                break
    return float(best)


def crest_factor(waveform: Optional[np.ndarray]) -> float:
    """Peak / RMS ratio — gunshots and blasts are sharp impulses (> ~5)."""
    if waveform is None or len(waveform) == 0:
        return 0.0
    w = np.asarray(waveform, dtype=np.float32)
    rms = float(np.sqrt(np.mean(w * w)))
    if rms < 1e-6:
        return 0.0
    return float(np.max(np.abs(w)) / rms)


# ═══════════════════════════════════════════════════════
# Distress speech lexicon
# ═══════════════════════════════════════════════════════

# (phrase regex, category, weight). Patterns are matched on normalised text
# (lower-case, punctuation stripped). Roman Urdu + Urdu script included since
# deployment is in Pakistan.
_LEXICON: List[Tuple[str, str, float]] = [
    # Calls for help
    (r"\bhelp me\b", "distress_speech", 0.90),
    (r"\bsomebody help\b|\bsomeone help\b|\bplease help\b", "distress_speech", 0.90),
    (r"\bhelp\b", "distress_speech", 0.60),
    (r"\bcall (the )?(police|cops|911|15|1122|ambulance)\b", "distress_speech", 0.90),
    (r"\bleave me alone\b|\blet me go\b|\bget off me\b|\bstop hurting\b", "distress_speech", 0.85),
    (r"\bdon'?t hurt\b|\bdon'?t kill\b|\bdon'?t shoot\b|\bplease stop\b", "distress_speech", 0.90),
    (r"\bi'?m being (attacked|robbed|followed)\b|\bthief\b|\brobbery\b", "distress_speech", 0.80),
    (r"\bfire\b(?! (it|away))", "distress_speech", 0.45),
    (r"\brun\b(?! (it|the|a))", "distress_speech", 0.35),
    (r"\bbachao\b|\bbacha(o|lo)\b|\bmadad\b|\bmadad karo\b", "distress_speech", 0.90),
    (r"\bchor\b|\bdaku\b|\bpolice bulao\b|\bchor do\b|\bchhor do\b|\bmujhe chhor\b", "distress_speech", 0.80),
    (r"بچاؤ|بچاو|مدد|چور|ڈاکو|پولیس بلاؤ|چھوڑ دو", "distress_speech", 0.90),
    # Threats / robbery commands
    (r"\bi('?ll| will) kill (you|him|her)\b|\bkill (you|him|her)\b", "threat_speech", 0.95),
    (r"\bi('?ll| will) shoot\b|\bshoot (him|her|them|you)\b", "threat_speech", 0.95),
    (r"\bgive me (your|the) (money|phone|wallet|bag|keys)\b|\bhand it over\b", "threat_speech", 0.90),
    (r"\bhands up\b|\bget down\b|\bon the ground\b|\bnobody move\b|\bdon'?t move\b", "threat_speech", 0.80),
    (r"\bmaar (do|dunga|denge|daalo)\b|\bmaar ke\b|\bjaan se maar\b|\bgoli maar\b", "threat_speech", 0.95),
    (r"\bmobile do\b|\bpaise (do|nikalo)\b|\bwallet (do|nikalo)\b|\bhaath upar\b", "threat_speech", 0.90),
    (r"مار دو|گولی مار|جان سے مار|موبائل دو|پیسے نکالو|ہاتھ اوپر", "threat_speech", 0.95),
    # Weapon mentions
    (r"\b(he|she|they)( has|'s got| got)? (a )?(gun|knife|pistol|weapon)\b", "weapon_speech", 0.90),
    (r"\bgun\b|\bpistol\b|\bknife\b|\bbomb\b|\bshooter\b|\bshots fired\b", "weapon_speech", 0.60),
    (r"\bbandook\b|\bpistaul\b|\bchaku\b|\bchhuri\b|\bgoli\b", "weapon_speech", 0.60),
    (r"بندوق|پستول|چاقو|چھری|بم|گولی", "weapon_speech", 0.60),
]

# Benign phrasings that make an otherwise matching keyword harmless.
_BENIGN = [
    r"\bhelp (me )?(with|you|out|yourself|desk|line)\b",
    r"\b(can|may|could|how can) i help\b",
    r"\bthanks? for (the|your) help\b",
    r"\bfire (it|away|up)\b|\bfired (him|her|me|from)\b",
    r"\bkill(ing)? (it|time)\b|\byou killed it\b",
    r"\bgun show\b|\bwater gun\b|\bnerf\b|\btop gun\b",
    r"\bsing along\b|\bchorus\b|\bdance\b|\bhappy birthday\b|\bencore\b",
]

_COMPILED_LEX = [(re.compile(p, re.IGNORECASE), c, w) for p, c, w in _LEXICON]
_COMPILED_BENIGN = [re.compile(p, re.IGNORECASE) for p in _BENIGN]


def _normalise(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^\w\s'؀-ۿ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class SpeechMatch:
    category: str
    confidence: float
    phrases: List[str]


def match_distress_speech(transcript: str) -> Optional[SpeechMatch]:
    """
    Score a transcript for distress / threat / weapon content.

    Returns the strongest category, or None if nothing suspicious was said.
    Repetition ("help! help! help!") boosts confidence; benign phrasing and
    sung/lyrical context damp it.
    """
    if not transcript or not transcript.strip():
        return None
    text = _normalise(transcript)

    benign_hits = sum(1 for b in _COMPILED_BENIGN if b.search(text))

    per_cat: Dict[str, float] = {}
    phrases: Dict[str, List[str]] = {}
    for rx, cat, weight in _COMPILED_LEX:
        found = rx.findall(text)
        if not found:
            continue
        m = rx.search(text)
        hit = m.group(0) if m else str(found[0])
        reps = len(found)
        score = min(0.99, weight + 0.10 * (reps - 1))
        if score > per_cat.get(cat, 0.0):
            per_cat[cat] = score
        phrases.setdefault(cat, []).append(hit)

    if not per_cat:
        return None

    if benign_hits:
        per_cat = {c: s * (0.35 ** benign_hits) for c, s in per_cat.items()}

    # Threat speech outranks a plain "help" at equal confidence.
    priority = {"threat_speech": 0.02, "weapon_speech": 0.01, "distress_speech": 0.0}
    cat = max(per_cat, key=lambda c: per_cat[c] + priority.get(c, 0))
    conf = per_cat[cat]
    if conf < 0.30:
        return None
    return SpeechMatch(category=cat, confidence=round(conf, 3), phrases=phrases[cat])


# ═══════════════════════════════════════════════════════
# Context analyzer
# ═══════════════════════════════════════════════════════

_LABELS = {
    "gunshot": "Gunshot",
    "explosion": "Explosion",
    "scream": "Screaming",
    "glass": "Glass breaking",
    "crash": "Crash / smash",
    "distress_speech": "Distress call",
    "threat_speech": "Threatening speech",
    "weapon_speech": "Weapon mentioned",
}


class AudioContextAnalyzer:
    """
    Stateful per-stream analyzer. Feed it one chunk at a time:

        events = analyzer.analyze(scores, waveform=chunk, transcript=text)

    ``scores`` is a {yamnet_label: score} dict for the chunk (mean over frames).
    """

    def __init__(self,
                 history_seconds: float = 30.0,
                 chunk_seconds: float = 1.0,
                 gunshot_threshold: float = 0.30,
                 explosion_threshold: float = 0.35,
                 scream_threshold: float = 0.30,
                 glass_threshold: float = 0.30,
                 crash_threshold: float = 0.40,
                 festive_threshold: float = 0.30,
                 min_crest_factor: float = 4.0):
        self.chunk_seconds = chunk_seconds
        n = max(3, int(round(history_seconds / max(chunk_seconds, 1e-3))))
        self._hist: Dict[str, Deque[float]] = {
            g: deque(maxlen=n) for g in ("music", "crowd", "fireworks", "scream", "shout")
        }
        self.gunshot_threshold = gunshot_threshold
        self.explosion_threshold = explosion_threshold
        self.scream_threshold = scream_threshold
        self.glass_threshold = glass_threshold
        self.crash_threshold = crash_threshold
        self.festive_threshold = festive_threshold
        self.min_crest_factor = min_crest_factor
        self._scream_streak = 0

    # ── context helpers ──────────────────────────────────
    @staticmethod
    def _mean(d: Deque[float]) -> float:
        return float(np.mean(d)) if d else 0.0

    def festive_level(self) -> float:
        """How much the scene sounds like a concert / party / match (0-1)."""
        music = self._mean(self._hist["music"])
        crowd = self._mean(self._hist["crowd"])
        return float(max(music, crowd))

    def context_summary(self) -> str:
        parts = []
        for g in ("music", "crowd", "fireworks"):
            v = self._mean(self._hist[g])
            if v >= 0.05:
                parts.append(f"{g} {v:.2f}")
        return ", ".join(parts) or "quiet"

    # ── main entry point ─────────────────────────────────
    def analyze(self, scores: Dict[str, float],
                waveform: Optional[np.ndarray] = None,
                transcript: str = "",
                media_time: Optional[float] = None) -> List[ThreatAudioEvent]:
        g = {k: group_score(scores, k) for k in LABEL_GROUPS}

        # Baseline *before* adding this chunk so a sudden event is compared
        # against what the scene sounded like until now.
        scream_baseline = self._mean(self._hist["scream"])
        shout_baseline = self._mean(self._hist["shout"])
        festive_hist = self.festive_level()
        for k in self._hist:
            self._hist[k].append(g[k])
        # Current chunk can establish context too (first seconds of a concert).
        festive_now = max(g["music"], g["crowd"])
        festive = max(festive_hist, festive_now)
        is_festive = festive >= self.festive_threshold
        ctx = self.context_summary()
        crest = crest_factor(waveform)
        impulsive = waveform is None or crest >= self.min_crest_factor

        events: List[ThreatAudioEvent] = []

        def emit(cat: str, conf: float, **kw):
            events.append(ThreatAudioEvent(
                category=cat, sound_class=_LABELS[cat], confidence=round(float(min(conf, 0.99)), 3),
                media_time=media_time, duration=self.chunk_seconds, context=ctx, **kw))

        # ── Gunshot / explosion ("bang") ─────────────
        # YAMNet cannot reliably tell a real gunshot from a firework or
        # firecracker (real gunshots often score higher on "Fireworks"), so
        # the *scene* decides: bangs during music / cheering (wedding, mela,
        # match, New Year) are treated as celebration; a bang on an otherwise
        # quiet street is reported.
        gun = g["gunshot"]
        bang = max(gun, g["explosion"], g["fireworks"])
        if bang >= self.gunshot_threshold and impulsive:
            gun_evidence = gun >= 0.15
            conf = bang if gun_evidence else bang * 0.85
            if is_festive:
                # Only clear, explicit gunfire that beats the firework labels
                # survives a festive scene.
                if not (gun >= 0.5 and gun > g["fireworks"]):
                    conf = 0.0
                else:
                    conf = gun * 0.9
            if conf >= self.gunshot_threshold:
                cat = "gunshot" if (gun_evidence or g["explosion"] < 0.6) else "explosion"
                emit(cat, conf)

        # ── Scream (context + anomaly gated) ───────────
        scream = g["scream"]
        if scream >= self.scream_threshold:
            self._scream_streak += 1
        else:
            self._scream_streak = 0
        if scream >= self.scream_threshold:
            anomaly = scream - scream_baseline           # how unusual for this scene
            conf = scream
            if is_festive:
                # Concert / match / party — screams & shouts are normal.
                # Only a scream that rises sharply above the festive baseline
                # *and* drowns out the music is kept.
                if anomaly < 0.35 or scream < festive_now:
                    conf = 0.0
                else:
                    conf *= 0.7
            elif scream_baseline > 0.25 and anomaly < 0.15:
                # Persistent screaming with no music (e.g. amusement ride,
                # playground) — not a sudden emergency.
                conf = 0.0
            if g["crowd"] >= 0.3 and "Children" in " ".join(
                    k for k, v in scores.items() if v >= 0.2):
                conf *= 0.5                                # kids playing
            if g["baby"] >= scream:
                conf = 0.0                                 # baby / child crying, not an attack
            if conf > 0 and self._scream_streak >= 2:
                conf += 0.05                               # sustained
            if conf >= self.scream_threshold:
                emit("scream", conf)

        # ── Glass / crash ───────────────────────────────
        # Glass must actually *break* — clinking cutlery, coins or a cash
        # register also score "Glass" / "Chink, clink".
        if (g["glass"] >= self.glass_threshold and g["breaking"] >= 0.25
                and g["breaking"] >= g["clinks"] * 0.8
                and not (is_festive and g["music"] > g["glass"])):
            emit("glass", g["glass"])
        if g["crash"] >= self.crash_threshold and not (is_festive and g["music"] > g["crash"]):
            emit("crash", g["crash"])

        # ── Distress / threat speech ───────────────────
        if transcript:
            m = match_distress_speech(transcript)
            if m is not None:
                conf = m.confidence
                shouted = g["shout"] >= 0.15 or g["scream"] >= 0.15
                sung = g["music"] >= 0.35 and g["music"] > g["speech"]
                if sung:
                    conf *= 0.3            # very likely song lyrics
                elif is_festive and not shouted:
                    conf *= 0.6            # chatter at an event
                if shouted:
                    conf += 0.10           # yelled, not conversational
                if shout_baseline > 0.3 and is_festive:
                    conf *= 0.8            # whole crowd is shouting
                if conf >= 0.50:
                    emit(m.category, conf, transcript=transcript.strip(),
                         matched_phrases=m.phrases)

        return events

    def wants_transcript(self, scores: Dict[str, float]) -> bool:
        """Only run (expensive) speech recognition when someone is speaking/shouting."""
        return group_score(scores, "speech") >= 0.20 or group_score(scores, "scream") >= 0.20


def summarise(events: Iterable[ThreatAudioEvent]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in events:
        out[e.category] = out.get(e.category, 0) + 1
    return out
