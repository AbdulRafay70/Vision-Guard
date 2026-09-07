"""
VisionGuard — SQLite Authentic Incident Database & Crime Heat Engine
Uses Python SQLite database (prototype/data/visionguard_incidents.db)
to record and compute real-time Karachi sector crime heat maps.
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import config

logger = logging.getLogger(__name__)

KARACHI_SECTORS = [
    "Saddar",
    "Lyari",
    "Clifton",
    "Gulshan",
    "DHA",
    "Orangi",
    "Shahra-e-Faisal"
]

HOUR_SLOTS = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "23:59"]


class SQLiteIncidentDatabase:
    """
    Manages authentic recorded incidents in a persistent SQLite database table.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.data_dir = config.BASE_DIR / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = db_path or (self.data_dir / "visionguard_incidents.db")
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create incidents table if it does not exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_code TEXT UNIQUE,
                    sector TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    camera_id TEXT,
                    source TEXT DEFAULT 'vision_guard_ai',
                    timestamp TEXT NOT NULL,
                    description TEXT,
                    evidence_file TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_cameras (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        logger.info("[SQLITE_DB] Initialized SQLite incident & camera database at %s", self.db_path)

    def clear(self):
        """Clear all stored incident records from SQLite database table."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM incidents")
            conn.commit()
        logger.info("[SQLITE_DB] SQLite incident database cleared completely.")

    def add_incident(
        self,
        sector: str,
        event_type: str,
        risk_score: float,
        risk_level: Optional[str] = None,
        camera_id: Optional[str] = None,
        source: str = "vision_guard_ai",
        timestamp: Optional[str] = None,
        description: Optional[str] = None,
        evidence_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Insert a new authentic incident record into SQLite database."""
        matched_sector = "Saddar"
        for sec in KARACHI_SECTORS:
            if sec.lower() in sector.lower():
                matched_sector = sec
                break
        else:
            if sector and sector.strip():
                matched_sector = sector.strip().title()

        if not risk_level:
            if risk_score >= 0.90:
                risk_level = "CRITICAL"
            elif risk_score >= 0.70:
                risk_level = "HIGH"
            elif risk_score >= 0.40:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

        now_iso = timestamp or datetime.now().isoformat()
        code = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{int(datetime.now().timestamp()*1000)%1000:03d}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO incidents (
                    incident_code, sector, event_type, risk_score, risk_level,
                    camera_id, source, timestamp, description, evidence_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                code, matched_sector, event_type, round(float(risk_score), 2),
                risk_level, camera_id or "cam_01", source, now_iso, description or "", evidence_file or ""
            ))
            conn.commit()
            row_id = cursor.lastrowid

        logger.info("[SQLITE_DB] Recorded incident #%d in SQLite: %s (%s - %s)", row_id, code, matched_sector, risk_level)
        return {
            "id": code,
            "db_id": row_id,
            "sector": matched_sector,
            "event_type": event_type,
            "risk_score": round(float(risk_score), 2),
            "risk_level": risk_level,
            "camera_id": camera_id or "cam_01",
            "source": source,
            "timestamp": now_iso
        }

    def save_camera(self, cam_id: str, name: str, sector: str, cam_type: str, source: str, enabled: int = 1) -> Dict[str, Any]:
        """Save or update a dynamic camera in the SQLite database."""
        now_iso = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO system_cameras (id, name, sector, type, source, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    sector=excluded.sector,
                    type=excluded.type,
                    source=excluded.source,
                    enabled=excluded.enabled
            """, (cam_id, name, sector, cam_type, str(source), enabled, now_iso))
            conn.commit()
        return {
            "id": cam_id,
            "name": name,
            "sector": sector,
            "type": cam_type,
            "source": str(source),
            "enabled": bool(enabled)
        }

    def get_system_cameras(self) -> List[Dict[str, Any]]:
        """Fetch all cameras stored in SQLite system_cameras table."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM system_cameras WHERE enabled = 1").fetchall()
        return [dict(r) for r in rows]

    def delete_system_camera(self, cam_id: str):
        """Remove a camera from SQLite database."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM system_cameras WHERE id = ?", (cam_id,))
            conn.commit()

    def get_incidents(self, timeframe_days: int = 30) -> List[Dict[str, Any]]:
        """Fetch incidents within the timeframe window from SQLite table."""
        cutoff = datetime.now() - timedelta(days=timeframe_days)
        cutoff_iso = cutoff.isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if timeframe_days > 0:
                cursor.execute("SELECT * FROM incidents WHERE timestamp >= ? ORDER BY timestamp DESC", (cutoff_iso,))
            else:
                cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC")
            rows = cursor.fetchall()

        return [dict(r) for r in rows]

    def compute_heatmaps(self, timeframe_days: int = 30) -> Dict[str, Any]:
        """Compute Karachi crime heat maps dynamically from SQLite records."""
        incidents = self.get_incidents(timeframe_days=timeframe_days)
        total_count = len(incidents)

        sector_counts: Dict[str, int] = {sec: 0 for sec in KARACHI_SECTORS}
        for inc in incidents:
            sec = inc.get("sector", "Saddar")
            if sec in sector_counts:
                sector_counts[sec] += 1
            else:
                sector_counts[sec] = sector_counts.get(sec, 0) + 1

        max_sec_incidents = max(sector_counts.values()) if sector_counts.values() else 0

        sectors = []
        for sec_name in KARACHI_SECTORS:
            count = sector_counts.get(sec_name, 0)
            intensity = round(count / max_sec_incidents, 2) if max_sec_incidents > 0 else 0.0

            if count == 0:
                level = "SAFE" if total_count > 0 else "LOW"
                color = "#10b981"
            elif count >= 30 or intensity >= 0.85:
                level = "CRITICAL"
                color = "#ef4444"
            elif count >= 15 or intensity >= 0.60:
                level = "HIGH"
                color = "#f59e0b"
            elif count >= 5 or intensity >= 0.30:
                level = "MEDIUM"
                color = "#6366f1"
            else:
                level = "LOW"
                color = "#10b981"

            sectors.append({
                "name": sec_name,
                "incidents": count,
                "level": level,
                "intensity": max(intensity, 0.08 if count > 0 else 0.0),
                "color": color
            })

        sectors.sort(key=lambda s: s["incidents"], reverse=True)

        hourly_counts: Dict[str, int] = {h: 0 for h in HOUR_SLOTS}
        for inc in incidents:
            ts_str = inc.get("timestamp")
            if not ts_str:
                continue
            try:
                dt = datetime.fromisoformat(ts_str)
                hour = dt.hour
                if hour < 2: slot = "00:00"
                elif hour < 5: slot = "03:00"
                elif hour < 8: slot = "06:00"
                elif hour < 11: slot = "09:00"
                elif hour < 14: slot = "12:00"
                elif hour < 17: slot = "15:00"
                elif hour < 20: slot = "18:00"
                elif hour < 23: slot = "21:00"
                else: slot = "23:59"
                hourly_counts[slot] += 1
            except Exception:
                hourly_counts["18:00"] += 1

        max_hour_count = max(hourly_counts.values()) if hourly_counts.values() else 0
        hourly_curve = []
        for slot in HOUR_SLOTS:
            cnt = hourly_counts[slot]
            if cnt == max_hour_count and max_hour_count > 0:
                pct = int((cnt / total_count) * 100) if total_count > 0 else 0
                risk_desc = f"Peak Incident Period ({pct}% of total)"
            elif cnt > 0:
                risk_desc = "Active Monitoring Window"
            else:
                risk_desc = "Baseline (Safe)"

            hourly_curve.append({
                "hour": slot,
                "incidents": cnt,
                "risk": risk_desc
            })

        top_sector = sectors[0]["name"] if sectors else "N/A"
        top_sector_cnt = sectors[0]["incidents"] if sectors else 0
        peak_slot = max(hourly_counts, key=hourly_counts.get) if total_count > 0 else "N/A"
        peak_cnt = hourly_counts.get(peak_slot, 0)
        peak_pct = int((peak_cnt / total_count) * 100) if total_count > 0 else 0

        peak_summary = {
            "primary_peak": f"{peak_slot} ({peak_pct}% of recorded incidents)" if total_count > 0 else "No Incidents Recorded",
            "highest_threat_sector": f"{top_sector} ({top_sector_cnt} incidents)" if total_count > 0 else "All Sectors Baseline Safe",
            "total_incidents": total_count,
            "period": f"Last {timeframe_days} Days"
        }

        predictions = []
        for sec in sectors[:3]:
            if sec["incidents"] > 0:
                predictions.append({
                    "sector": sec["name"],
                    "level": sec["level"],
                    "prediction": f"{sec['level']} risk based on {sec['incidents']} recorded incidents"
                })
            else:
                predictions.append({
                    "sector": sec["name"],
                    "level": "LOW",
                    "prediction": "LOW risk (Baseline normal, 0 recorded incidents)"
                })

        return {
            "city": "Karachi",
            "period": f"Last {timeframe_days} Days",
            "total_incidents": total_count,
            "sectors": sectors,
            "hourly_curve": hourly_curve,
            "peak_summary": peak_summary,
            "predictions": predictions
        }


# Alias for backward compatibility
IncidentDatabase = SQLiteIncidentDatabase
