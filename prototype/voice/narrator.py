"""
VisionGuard — AI Event Narrator
Uses Gemini API (google.genai SDK) to generate human-readable event
descriptions in English and Urdu.
"""
import json
import logging
import os
from typing import Optional, Dict
from events.base import EventAlert

import config

logger = logging.getLogger(__name__)


class EventNarrator:
    """
    Generates human-readable event narratives using Gemini API.
    Falls back to template-based descriptions if API is unavailable.
    """

    def __init__(self):
        self._client = None
        self.available = False

    def load(self):
        """Initialize Gemini API using google.genai SDK."""
        api_key = config.GEMINI_API_KEY
        if not api_key:
            logger.info("[NARRATOR] No GEMINI_API_KEY set — using template-based narration.")
            self.available = False
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self.available = True
            logger.info("[NARRATOR] Gemini API connected — AI narration enabled (google.genai SDK).")
        except Exception as e:
            logger.error("[NARRATOR] Gemini API error: %s — using templates.", e)
            self.available = False

    def narrate(self, alert: EventAlert) -> Dict[str, str]:
        """
        Generate English + Urdu narrative for an event alert.
        Returns {"english": "...", "urdu": "..."}.
        """
        if self.available and self._client:
            return self._narrate_with_gemini(alert)
        else:
            return self._narrate_with_template(alert)

    def _narrate_with_gemini(self, alert: EventAlert) -> Dict[str, str]:
        """Use Gemini API for narration."""
        try:
            prompt = f"""You are VisionGuard AI Narrator. Generate a clear, professional security alert 
narrative for BOTH English and Urdu (in Urdu script اردو).

Event Data:
- Event Type: {alert.event_type}
- Risk Score: {alert.risk_score}%
- Risk Level: {alert.risk_level}
- Duration: {alert.duration_seconds} seconds
- Description: {alert.description}
- Department: {alert.department} (Dial: {alert.dial})
- Action: {alert.action}

Rules:
- Be factual and precise
- Keep each narrative under 3 sentences
- Use "suspected" for crime events — do NOT accuse anyone
- State what was detected, what action was taken

Respond in this exact JSON format:
{{"english": "...", "urdu": "..."}}"""

            response = self._client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.3},
            )
            text = response.text.strip()

            # Clean up response — extract JSON
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)
            return {
                "english": result.get("english", alert.description),
                "urdu": result.get("urdu", "تفصیل دستیاب نہیں"),
            }
        except Exception as e:
            logger.warning("[NARRATOR] Gemini narration failed (%s), using template.", e)
            return self._narrate_with_template(alert)

    def _narrate_with_template(self, alert: EventAlert) -> Dict[str, str]:
        """Template-based fallback narration."""
        templates = {
            "fire": {
                "english": f"Fire detected with {alert.risk_score}% risk. {alert.department} has been notified. Duration: {alert.duration_seconds:.0f} seconds.",
                "urdu": f"آگ کا پتہ چلا ہے۔ خطرے کی سطح {alert.risk_score} فیصد۔ {alert.department} کو مطلع کر دیا گیا ہے۔",
            },
            "car_accident": {
                "english": f"Vehicle accident detected with {alert.risk_score}% risk. {alert.department} dispatched.",
                "urdu": f"گاڑی کا حادثہ پکڑا گیا۔ {alert.department} کو بھیج دیا گیا ہے۔",
            },
            "fight": {
                "english": f"Suspected street fight detected. {alert.risk_score}% risk. Awaiting review for {alert.department}.",
                "urdu": f"مشتبہ لڑائی کا پتہ چلا۔ {alert.department} کے جائزے کا انتظار۔",
            },
            "robbery": {
                "english": f"Suspected robbery detected. Risk: {alert.risk_score}%. {alert.department} notified.",
                "urdu": f"مشتبہ ڈکیتی کا پتہ چلا۔ {alert.department} کو مطلع کیا گیا۔",
            },
            "kidnapping": {
                "english": f"Suspected abduction detected. Risk: {alert.risk_score}%. {alert.department} alerted.",
                "urdu": f"مشتبہ اغوا کا پتہ چلا۔ {alert.department} کو آگاہ کیا گیا۔",
            },
            "crowd_crush": {
                "english": f"Crowd density alert. Risk: {alert.risk_score}%. {alert.department} notified.",
                "urdu": f"ہجوم کی کثافت خطرناک ہے۔ {alert.department} کو مطلع کیا گیا۔",
            },
            "weapon": {
                "english": f"Suspected weapon detected. Risk: {alert.risk_score}%. {alert.department} dispatched immediately.",
                "urdu": f"مشتبہ ہتھیار کا پتہ چلا۔ {alert.department} کو فوری طور پر بھیجا گیا۔",
            },
        }

        default = {
            "english": f"{alert.event_type.replace('_', ' ').title()} detected. Risk: {alert.risk_score}%. {alert.department} notified.",
            "urdu": f"واقعہ کا پتہ چلا۔ خطرے کی سطح: {alert.risk_score} فیصد۔",
        }

        return templates.get(alert.event_type, default)
