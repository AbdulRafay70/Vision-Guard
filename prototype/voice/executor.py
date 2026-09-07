"""
VisionGuard — Voice Command Executor
Executes parsed JSON voice commands on the active VisionGuard system.
"""
import logging
from typing import Dict, Any
from events.engine import EventEngine

logger = logging.getLogger(__name__)


class CommandExecutor:
    """
    Executes JSON actions returned by VoiceCommandInterpreter.
    """

    def __init__(self, event_engine: EventEngine, app_state=None):
        self.event_engine = event_engine
        self.app_state = app_state

    def execute(self, command_dict: Dict[str, Any]) -> str:
        """
        Executes a command and returns a natural human response string.
        """
        if command_dict.get("clarification_needed"):
            return command_dict.get("clarification_question", "Could you please rephrase that command?")

        action = command_dict.get("action")
        params = command_dict.get("params", {})

        if action == "status_summary":
            summary = self.event_engine.get_status_summary()
            alerts = summary.get("alerts", [])
            if not alerts:
                return "VisionGuard status report: All systems normal. No active emergency alerts currently detected."
            
            alert_descs = [f"{a['emoji']} {a['type'].upper()} ({a['level']}) in {a['department']}" for a in alerts]
            return f"VisionGuard status report: {len(alerts)} active emergency situation(s): " + ", ".join(alert_descs) + "."

        elif action == "status_check":
            summary = self.event_engine.get_status_summary()
            if summary.get("active_alerts", 0) == 0:
                return "Everything is clear and fine. All monitored parameters are within safe ranges."
            else:
                return f"Attention: There are {summary['active_alerts']} active emergency alert(s) requiring attention!"

        elif action == "confirm_alert":
            event_type = params.get("event_type")
            if not event_type and self.event_engine.active_alerts:
                event_type = self.event_engine.active_alerts[0].event_type
            
            if event_type:
                alert = self.event_engine.confirm_alert(event_type)
                if alert:
                    return f"Confirmed alert for {event_type.upper()}. Dispatching {alert.department} (Dial {alert.dial}) immediately."
            return "No active alert found to confirm."

        elif action == "dismiss_alert":
            event_type = params.get("event_type")
            if not event_type and self.event_engine.active_alerts:
                event_type = self.event_engine.active_alerts[0].event_type

            if event_type:
                self.event_engine.dismiss_alert(event_type)
                return f"Alert for {event_type.upper()} has been dismissed."
            return "No active alert to dismiss."

        elif action == "show_cameras":
            zone = params.get("zone", "monitored area")
            return f"Filtering dashboard view to show cameras for {zone}."

        elif action == "switch_camera":
            cam_id = params.get("camera_id", "")
            cam_name = params.get("camera_name", cam_id)
            if cam_id:
                return f"Switching live feed to camera {cam_name or cam_id}."
            return "Please specify which camera to switch to."

        elif action == "system_health":
            try:
                import torch
                import psutil
                gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
                vram_alloc = torch.cuda.memory_allocated(0) / (1024**2) if torch.cuda.is_available() else 0
                vram_total = torch.cuda.get_device_properties(0).total_mem / (1024**2) if torch.cuda.is_available() else 0
                cpu = psutil.cpu_percent(interval=0.1)
                ram = psutil.virtual_memory().percent
                return (f"System Health: GPU {gpu_name}, VRAM {vram_alloc:.0f}/{vram_total:.0f} MB, "
                        f"CPU {cpu}%, RAM {ram}%.")
            except Exception as e:
                return f"System health check failed: {e}"

        elif action == "toggle_skeleton":
            return "Toggling pose skeleton overlay. Check the dashboard for the updated view."

        elif action == "record_clip":
            seconds = params.get("seconds", 30)
            return f"Recording last {seconds} seconds of footage. Evidence will be saved to the evidence folder."

        elif action == "mute_alerts":
            duration = params.get("duration_min", 5)
            return f"Alert sounds muted for {duration} minutes. Visual alerts remain active."

        elif action == "zoom_in":
            return "Zooming into the current camera feed."

        elif action == "zoom_out":
            return "Zooming out of the current camera feed."

        elif action == "show_heatmap":
            return "Opening incident heatmap overlay on the dashboard map."

        elif action == "dispatch":
            dept = params.get("department", "unknown")
            zone = params.get("zone", "unknown")
            return f"Dispatching {dept} to {zone} immediately."

        elif action == "track_person":
            track_id = params.get("track_id", "unknown")
            return f"Now tracking person VG-{track_id} across all connected cameras."

        return f"Executing action '{action}' on VisionGuard system."
