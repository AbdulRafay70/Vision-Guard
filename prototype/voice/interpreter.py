"""
VisionGuard — Voice Command Interpreter
Uses Gemini 2.0 Flash (google.genai SDK) to convert natural language operator
commands into structured JSON system actions.
"""
import json
import logging
import os
from typing import Dict, Any, Optional

import config

logger = logging.getLogger(__name__)

VISIONGUARD_COMMAND_PROMPT = """
You are VisionGuard AI Command Interpreter.
You convert natural language commands from security operators into structured JSON commands for VisionGuard.

AVAILABLE ACTIONS:
- status_summary: Summarize active alerts and system status
- status_check: Quick check if everything is fine
- show_cameras: Filter/show cameras by zone. Params: zone, count
- confirm_alert: Confirm current alert for dispatch. Params: event_type
- dismiss_alert: Dismiss current alert. Params: event_type
- dispatch: Send department to location. Params: department, zone
- track_person: Track person by VG-ID. Params: track_id
- show_heatmap: Show crime/incident heatmap
- switch_camera: Switch to a specific camera. Params: camera_id, camera_name
- zoom_in: Zoom into current camera feed
- zoom_out: Zoom out of current camera feed
- toggle_skeleton: Toggle pose skeleton overlay on/off
- record_clip: Save last N seconds of footage. Params: seconds
- mute_alerts: Mute alert sounds temporarily. Params: duration_min
- system_health: Show system hardware health (GPU, CPU, VRAM)

KARACHI ZONES:
saddar, clifton, gulshan, nazimabad, orangi, lyari, dha, jauhar

DEPARTMENTS:
police (15), fire_brigade (16), edhi (115), rangers, traffic_police

RULES:
1. Always return ONLY valid JSON.
2. If command is vague, set "clarification_needed": true and add a question.
3. Be tolerant of Urdu-English mixed commands.

Output format:
{
  "action": "action_name",
  "params": { ... },
  "confidence": 0.95,
  "clarification_needed": false,
  "clarification_question": null
}
"""


class VoiceCommandInterpreter:
    def __init__(self):
        self._client = None
        self.available = False

    def load(self):
        """Initialize Gemini API for command parsing using google.genai SDK."""
        api_key = config.GEMINI_API_KEY
        if not api_key:
            logger.info("[VOICE] No GEMINI_API_KEY — voice command interpreter running in offline rule mode.")
            self.available = False
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self.available = True
            logger.info("[VOICE] Gemini Voice Command Interpreter connected (google.genai SDK)!")
        except Exception as e:
            logger.error("[VOICE] Gemini Voice Interpreter initialization error: %s", e)
            self.available = False

    def interpret(self, operator_speech: str) -> Dict[str, Any]:
        """
        Takes human operator speech/text and parses it into structured JSON action.
        """
        if self.available and self._client:
            return self._interpret_with_gemini(operator_speech)
        else:
            return self._interpret_offline(operator_speech)

    def _interpret_with_gemini(self, speech: str) -> Dict[str, Any]:
        try:
            response = self._client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=f"Operator command: {speech}",
                config={
                    "system_instruction": VISIONGUARD_COMMAND_PROMPT,
                    "temperature": 0.1,
                },
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            return json.loads(text)
        except Exception as e:
            logger.warning("[VOICE] Gemini interpret failed (%s), falling back to offline.", e)
            return self._interpret_offline(speech)

    def _interpret_offline(self, speech: str) -> Dict[str, Any]:
        """Offline fallback rule matcher when Gemini API key is not present."""
        s = speech.lower()

        if "status" in s or "going on" in s or "happen" in s or "report" in s:
            return {"action": "status_summary", "params": {}, "confidence": 0.9, "clarification_needed": False}
        elif "fine" in s or "okay" in s or "check" in s or "safe" in s or "clear" in s:
            return {"action": "status_check", "params": {}, "confidence": 0.9, "clarification_needed": False}
        elif "health" in s or "gpu" in s or "cpu" in s or "system" in s:
            return {"action": "system_health", "params": {}, "confidence": 0.85, "clarification_needed": False}
        elif "skeleton" in s or "pose" in s:
            return {"action": "toggle_skeleton", "params": {}, "confidence": 0.85, "clarification_needed": False}
        elif "record" in s or "save" in s or "clip" in s:
            return {"action": "record_clip", "params": {"seconds": 30}, "confidence": 0.8, "clarification_needed": False}
        elif "mute" in s or "silence" in s or "quiet" in s:
            return {"action": "mute_alerts", "params": {"duration_min": 5}, "confidence": 0.8, "clarification_needed": False}
        elif "heatmap" in s or "heat map" in s or "hotspot" in s:
            return {"action": "show_heatmap", "params": {}, "confidence": 0.85, "clarification_needed": False}
        elif "zoom in" in s:
            return {"action": "zoom_in", "params": {}, "confidence": 0.9, "clarification_needed": False}
        elif "zoom out" in s:
            return {"action": "zoom_out", "params": {}, "confidence": 0.9, "clarification_needed": False}

        # Zone-based camera commands
        zones = ["saddar", "clifton", "gulshan", "nazimabad", "orangi", "lyari", "dha", "jauhar"]
        for zone in zones:
            if zone in s:
                return {"action": "show_cameras", "params": {"zone": zone}, "confidence": 0.9, "clarification_needed": False}

        if "confirm" in s or "dispatch" in s or "send" in s:
            return {"action": "confirm_alert", "params": {}, "confidence": 0.8, "clarification_needed": False}
        elif "dismiss" in s or "ignore" in s or "cancel" in s:
            return {"action": "dismiss_alert", "params": {}, "confidence": 0.8, "clarification_needed": False}
        elif "camera" in s or "switch" in s:
            return {"action": "switch_camera", "params": {}, "confidence": 0.7, "clarification_needed": True,
                    "clarification_question": "Which camera would you like to switch to?"}

        return {
            "action": "unknown",
            "params": {},
            "confidence": 0.0,
            "clarification_needed": True,
            "clarification_question": f"Command '{speech}' not recognized. Try: 'What's going on?', 'Is everything safe?', 'Show Saddar cameras', 'System health'"
        }
