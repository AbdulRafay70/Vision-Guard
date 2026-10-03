"""
VisionGuard — Command Center persistence layer.

Everything the operator console creates or changes is stored here, in the same
SQLite database as the incident log (data/visionguard_incidents.db):

  users / sessions        operator accounts, hashed passwords, bearer tokens
  cities / areas / streets  the location hierarchy cameras are installed in
  camera_locations        which street/area each camera belongs to
  preferences             per-operator console state (pinned wall, layout, voice)
  voice_log               every voice/typed command and the system's reply
  audit_log               who did what, when (logins, camera changes, etc.)
  incidents (extended)    status / acknowledged / resolved workflow columns
"""
import hashlib
import json
import logging
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SESSION_HOURS = 12
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
PBKDF2_ROUNDS = 200_000

ROLES = ["Super Admin", "Supervisor", "Tactical Operator", "Security Analyst", "Viewer"]
# Roles allowed to change cameras and locations
CAMERA_ADMIN_ROLES = {"Super Admin", "Supervisor"}
# Roles allowed to manage operator accounts
USER_ADMIN_ROLES = {"Super Admin"}
# Roles allowed to acknowledge / resolve incidents
INCIDENT_ROLES = {"Super Admin", "Supervisor", "Tactical Operator", "Security Analyst"}

# Lawful basis on which a camera's feed may be accessed. Every camera must carry one.
ACCESS_BASES = {
    "owned": "Agency-owned camera",
    "consent": "Owner consent on file",
    "mou": "Agreement / MoU with operator",
    "warrant": "Court order / legal authorisation",
    "public": "Publicly broadcast / open stream",
    "demo": "Demo / test footage",
}
BASES_NEEDING_OWNER = {"consent", "mou"}
BASES_NEEDING_REFERENCE = {"consent", "mou", "warrant"}

DEFAULT_AREAS = ["Saddar", "Clifton", "Gulshan", "Nazimabad", "Orangi", "Lyari", "DHA", "Jauhar"]

USER_FIELDS = ["username", "full_name", "email", "role", "department", "access_level", "status",
               "sector", "created_at", "last_login", "must_change_password"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "x"


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split("$")
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(rounds))
        return secrets.compare_digest(check.hex(), digest)
    except (ValueError, AttributeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthError(Exception):
    pass


class ConsoleDatabase:
    def __init__(self, db_path: Path, default_password: str = "visionguard",
                 legacy_users_file: Optional[Path] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()
        self._seed(default_password, legacy_users_file)

    # ── plumbing ───────────────────────────────────────────────────────
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock, self._conn() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur

    def _all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def _one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def _init_schema(self):
        with self._lock, self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    role TEXT NOT NULL,
                    department TEXT,
                    access_level TEXT,
                    status TEXT NOT NULL DEFAULT 'Active',
                    sector TEXT,
                    password_hash TEXT NOT NULL,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                    station TEXT,
                    ip TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS areas (
                    id TEXT PRIMARY KEY,
                    city_id TEXT NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS streets (
                    id TEXT PRIMARY KEY,
                    area_id TEXT NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS camera_locations (
                    camera_id TEXT PRIMARY KEY,
                    city_id TEXT NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
                    area_id TEXT NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
                    street_id TEXT REFERENCES streets(id) ON DELETE SET NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS preferences (
                    username TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (username, key)
                );
                CREATE TABLE IF NOT EXISTS voice_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    text TEXT NOT NULL,
                    action TEXT,
                    response TEXT,
                    source TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    action TEXT NOT NULL,
                    target TEXT,
                    detail TEXT,
                    ip TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    ip TEXT NOT NULL,
                    username TEXT,
                    channels INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS device_cameras (
                    camera_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                    channel INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS access_grants (
                    camera_id TEXT PRIMARY KEY,
                    basis TEXT NOT NULL,
                    owner_name TEXT,
                    owner_contact TEXT,
                    reference TEXT,
                    note TEXT,
                    granted_by TEXT,
                    granted_at TEXT NOT NULL,
                    revoked_by TEXT,
                    revoked_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
                CREATE INDEX IF NOT EXISTS idx_voice_created ON voice_log(created_at);
            """)
            # Incident workflow columns on the existing incidents table
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
            cols = {r[1] for r in conn.execute("PRAGMA table_info(incidents)").fetchall()}
            for col, ddl in [
                ("status", "TEXT NOT NULL DEFAULT 'open'"),
                ("assigned_to", "TEXT"),
                ("acknowledged_by", "TEXT"),
                ("acknowledged_at", "TEXT"),
                ("resolved_by", "TEXT"),
                ("resolved_at", "TEXT"),
                ("notes", "TEXT"),
            ]:
                if col not in cols:
                    conn.execute(f"ALTER TABLE incidents ADD COLUMN {col} {ddl}")
            conn.commit()

    def _seed(self, default_password: str, legacy_users_file: Optional[Path]):
        if not self._one("SELECT 1 AS x FROM users LIMIT 1"):
            legacy = []
            if legacy_users_file and Path(legacy_users_file).exists():
                try:
                    legacy = json.loads(Path(legacy_users_file).read_text(encoding="utf-8"))
                except (ValueError, OSError) as e:
                    logger.warning("[CONSOLE_DB] Could not read legacy users file: %s", e)
            if not any(u.get("username") == "admin" for u in legacy):
                legacy.insert(0, {"username": "admin", "full_name": "System Administrator", "role": "Super Admin"})
            for u in legacy:
                self.create_user({**u, "password": default_password, "must_change_password": True},
                                 created_at=u.get("created_at"))
            logger.info("[CONSOLE_DB] Seeded %d operator account(s)", len(legacy))

        if not self._one("SELECT 1 AS x FROM cities LIMIT 1"):
            city = self.add_city("Karachi")
            for a in DEFAULT_AREAS:
                self.add_area(city["id"], a)

    # ── users & auth ───────────────────────────────────────────────────
    def _public_user(self, row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        out = {k: row.get(k) for k in USER_FIELDS}
        out["must_change_password"] = bool(row.get("must_change_password"))
        out["locked"] = bool(row.get("locked_until") and row["locked_until"] > _now())
        return out

    def list_users(self) -> List[Dict[str, Any]]:
        return [self._public_user(r) for r in self._all("SELECT * FROM users ORDER BY created_at")]

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        return self._public_user(self._one("SELECT * FROM users WHERE username = ?", (username.lower(),)))

    def create_user(self, data: Dict[str, Any], created_at: Optional[str] = None) -> Dict[str, Any]:
        username = str(data.get("username", "")).strip().lower()
        if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
            raise ValueError("Username must be 3–32 characters: letters, digits, dot, dash or underscore.")
        if self._one("SELECT 1 AS x FROM users WHERE username = ?", (username,)):
            raise ValueError(f"User '{username}' already exists.")
        password = str(data.get("password") or "")
        if len(password) < 8 and not data.get("must_change_password"):
            raise ValueError("Password must be at least 8 characters.")
        role = data.get("role") if data.get("role") in ROLES else "Tactical Operator"
        self._exec("""
            INSERT INTO users (username, full_name, email, role, department, access_level, status, sector,
                               password_hash, must_change_password, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            (data.get("full_name") or username.title()).strip(),
            (data.get("email") or "").strip(),
            role,
            (data.get("department") or "").strip(),
            (data.get("access_level") or "").strip(),
            data.get("status") if data.get("status") in ("Active", "Suspended") else "Active",
            (data.get("sector") or "").strip(),
            hash_password(password or secrets.token_urlsafe(12)),
            1 if data.get("must_change_password") else 0,
            created_at or _now(),
        ))
        return self.get_user(username)

    def update_user(self, username: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.get_user(username):
            return None
        sets, params = [], []
        for key in ["full_name", "email", "department", "access_level", "sector"]:
            if key in data:
                sets.append(f"{key} = ?")
                params.append(str(data[key] or "").strip())
        if data.get("role") in ROLES:
            sets.append("role = ?")
            params.append(data["role"])
        if data.get("status") in ("Active", "Suspended"):
            sets.append("status = ?")
            params.append(data["status"])
            if data["status"] == "Suspended":
                self._exec("DELETE FROM sessions WHERE username = ?", (username.lower(),))
        if data.get("unlock"):
            sets += ["failed_attempts = 0", "locked_until = NULL"]
        if sets:
            self._exec(f"UPDATE users SET {', '.join(sets)} WHERE username = ?", (*params, username.lower()))
        return self.get_user(username)

    def set_password(self, username: str, password: str, must_change: bool = False):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        self._exec("UPDATE users SET password_hash = ?, must_change_password = ?, failed_attempts = 0, locked_until = NULL WHERE username = ?",
                   (hash_password(password), 1 if must_change else 0, username.lower()))

    def delete_user(self, username: str) -> bool:
        return self._exec("DELETE FROM users WHERE username = ?", (username.lower(),)).rowcount > 0

    def check_password(self, username: str, password: str) -> bool:
        row = self._one("SELECT password_hash FROM users WHERE username = ?", ((username or "").lower(),))
        return bool(row) and verify_password(password or "", row["password_hash"])

    def authenticate(self, username: str, password: str, station: str = "", ip: str = "") -> Dict[str, Any]:
        username = (username or "").strip().lower()
        row = self._one("SELECT * FROM users WHERE username = ?", (username,))
        if not row:
            raise AuthError("Operator ID or password is incorrect.")
        if row.get("locked_until") and row["locked_until"] > _now():
            raise AuthError("Account temporarily locked after repeated failed sign-ins. Try again later or contact an administrator.")
        if row["status"] != "Active":
            raise AuthError("This account is suspended.")
        if not verify_password(password or "", row["password_hash"]):
            fails = row["failed_attempts"] + 1
            locked = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat(timespec="seconds") if fails >= MAX_FAILED_LOGINS else None
            self._exec("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?",
                       (0 if locked else fails, locked, username))
            self.audit(username, "login_failed", detail="Wrong password", ip=ip)
            raise AuthError("Operator ID or password is incorrect.")

        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
        self._exec("INSERT INTO sessions (token_hash, username, station, ip, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (_token_hash(token), username, station, ip, _now(), expires))
        self._exec("UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ? WHERE username = ?", (_now(), username))
        self._exec("DELETE FROM sessions WHERE expires_at < ?", (_now(),))
        self.audit(username, "login", detail=station, ip=ip)
        return {"token": token, "expires_at": expires, "user": self.get_user(username)}

    def session_user(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        row = self._one("""
            SELECT u.*, s.station AS session_station, s.expires_at FROM sessions s
            JOIN users u ON u.username = s.username
            WHERE s.token_hash = ? AND s.expires_at > ?
        """, (_token_hash(token), _now()))
        if not row or row["status"] != "Active":
            return None
        user = self._public_user(row)
        user["station"] = row.get("session_station")
        return user

    def end_session(self, token: str):
        self._exec("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))

    # ── locations ──────────────────────────────────────────────────────
    def _new_id(self, table: str, name: str) -> str:
        base = _slug(name)
        candidate = base
        while self._one(f"SELECT 1 AS x FROM {table} WHERE id = ?", (candidate,)):
            candidate = f"{base}-{secrets.token_hex(2)}"
        return candidate

    def add_city(self, name: str) -> Dict[str, Any]:
        name = (name or "").strip()
        if not name:
            raise ValueError("City name is required.")
        cid = self._new_id("cities", name)
        self._exec("INSERT INTO cities (id, name, created_at) VALUES (?, ?, ?)", (cid, name, _now()))
        return {"id": cid, "name": name}

    def add_area(self, city_id: str, name: str) -> Dict[str, Any]:
        name = (name or "").strip()
        if not name:
            raise ValueError("Area name is required.")
        if not self._one("SELECT 1 AS x FROM cities WHERE id = ?", (city_id,)):
            raise ValueError("City not found.")
        aid = self._new_id("areas", name)
        self._exec("INSERT INTO areas (id, city_id, name, created_at) VALUES (?, ?, ?, ?)", (aid, city_id, name, _now()))
        return {"id": aid, "name": name, "city_id": city_id}

    def add_street(self, area_id: str, name: str) -> Dict[str, Any]:
        name = (name or "").strip()
        if not name:
            raise ValueError("Street name is required.")
        if not self._one("SELECT 1 AS x FROM areas WHERE id = ?", (area_id,)):
            raise ValueError("Area not found.")
        sid = self._new_id("streets", name)
        self._exec("INSERT INTO streets (id, area_id, name, created_at) VALUES (?, ?, ?, ?)", (sid, area_id, name, _now()))
        return {"id": sid, "name": name, "area_id": area_id}

    def rename_location(self, level: str, loc_id: str, name: str) -> bool:
        table = {"city": "cities", "area": "areas", "street": "streets"}.get(level)
        if not table or not (name or "").strip():
            raise ValueError("Invalid rename request.")
        return self._exec(f"UPDATE {table} SET name = ? WHERE id = ?", (name.strip(), loc_id)).rowcount > 0

    def delete_location(self, level: str, loc_id: str) -> bool:
        table = {"city": "cities", "area": "areas", "street": "streets"}.get(level)
        if not table:
            raise ValueError("Invalid level.")
        return self._exec(f"DELETE FROM {table} WHERE id = ?", (loc_id,)).rowcount > 0

    def location_tree(self) -> List[Dict[str, Any]]:
        cities = self._all("SELECT id, name FROM cities ORDER BY created_at, name")
        areas = self._all("SELECT id, city_id, name FROM areas ORDER BY created_at, name")
        streets = self._all("SELECT id, area_id, name FROM streets ORDER BY created_at, name")
        for a in areas:
            a["streets"] = [{"id": s["id"], "name": s["name"]} for s in streets if s["area_id"] == a["id"]]
        for c in cities:
            c["areas"] = [{"id": a["id"], "name": a["name"], "streets": a["streets"]} for a in areas if a["city_id"] == c["id"]]
        return cities

    def placements(self) -> Dict[str, Dict[str, Any]]:
        rows = self._all("SELECT camera_id, city_id, area_id, street_id FROM camera_locations")
        return {r["camera_id"]: {"cityId": r["city_id"], "areaId": r["area_id"], "streetId": r["street_id"]} for r in rows}

    def place_camera(self, camera_id: str, city_id: str, area_id: str, street_id: Optional[str] = None):
        area = self._one("SELECT city_id FROM areas WHERE id = ?", (area_id,))
        if not area or area["city_id"] != city_id:
            raise ValueError("Area does not belong to the selected city.")
        if street_id:
            st = self._one("SELECT area_id FROM streets WHERE id = ?", (street_id,))
            if not st or st["area_id"] != area_id:
                raise ValueError("Street does not belong to the selected area.")
        self._exec("""
            INSERT INTO camera_locations (camera_id, city_id, area_id, street_id, updated_at) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(camera_id) DO UPDATE SET city_id = excluded.city_id, area_id = excluded.area_id,
                street_id = excluded.street_id, updated_at = excluded.updated_at
        """, (camera_id, city_id, area_id, street_id or None, _now()))

    def unplace_camera(self, camera_id: str):
        self._exec("DELETE FROM camera_locations WHERE camera_id = ?", (camera_id,))

    def area_name(self, area_id: str) -> Optional[str]:
        row = self._one("SELECT name FROM areas WHERE id = ?", (area_id,))
        return row["name"] if row else None

    # ── recorders & devices ────────────────────────────────────────────
    def save_device(self, name: str, kind: str, brand: str, model: str, ip: str, username: str, channels: int) -> Dict[str, Any]:
        existing = self._one("SELECT id FROM devices WHERE ip = ? AND kind = ?", (ip, kind))
        if existing:
            self._exec("UPDATE devices SET name = ?, brand = ?, model = ?, username = ?, channels = ? WHERE id = ?",
                       (name, brand, model, username, channels, existing["id"]))
            dev_id = existing["id"]
        else:
            dev_id = self._new_id("devices", f"{kind}-{ip.replace('.', '-')}")
            self._exec("INSERT INTO devices (id, name, kind, brand, model, ip, username, channels, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (dev_id, name, kind, brand, model, ip, username, channels, _now()))
        return self._one("SELECT * FROM devices WHERE id = ?", (dev_id,))

    def link_camera(self, camera_id: str, device_id: str, channel: int):
        self._exec("""INSERT INTO device_cameras (camera_id, device_id, channel) VALUES (?, ?, ?)
                      ON CONFLICT(camera_id) DO UPDATE SET device_id = excluded.device_id, channel = excluded.channel""",
                   (camera_id, device_id, channel))

    def unlink_camera(self, camera_id: str):
        self._exec("DELETE FROM device_cameras WHERE camera_id = ?", (camera_id,))

    def devices(self) -> List[Dict[str, Any]]:
        devs = self._all("SELECT * FROM devices ORDER BY created_at")
        links = self._all("SELECT * FROM device_cameras ORDER BY channel")
        for d in devs:
            d["cameras"] = [{"camera_id": l["camera_id"], "channel": l["channel"]} for l in links if l["device_id"] == d["id"]]
        return devs

    def camera_devices(self) -> Dict[str, Dict[str, Any]]:
        rows = self._all("""SELECT dc.camera_id, dc.channel, d.id, d.name, d.kind FROM device_cameras dc
                             JOIN devices d ON d.id = dc.device_id""")
        return {r["camera_id"]: {"device_id": r["id"], "device_name": r["name"], "device_kind": r["kind"], "channel": r["channel"]} for r in rows}

    def delete_device(self, device_id: str) -> List[str]:
        cams = [r["camera_id"] for r in self._all("SELECT camera_id FROM device_cameras WHERE device_id = ?", (device_id,))]
        self._exec("DELETE FROM devices WHERE id = ?", (device_id,))
        return cams

    # ── access grants (lawful basis for each camera) ───────────────────
    def validate_access(self, access: Dict[str, Any]) -> Dict[str, Any]:
        basis = str((access or {}).get("basis") or "").strip()
        if basis not in ACCESS_BASES:
            raise ValueError("Select the lawful basis for accessing this camera.")
        owner = str((access or {}).get("owner_name") or "").strip()
        ref = str((access or {}).get("reference") or "").strip()
        if basis in BASES_NEEDING_OWNER and not owner:
            raise ValueError("Record the camera owner's name for a consent / agreement basis.")
        if basis in BASES_NEEDING_REFERENCE and not ref:
            raise ValueError("Record the authorisation reference (consent form, MoU or order number).")
        return {
            "basis": basis,
            "owner_name": owner,
            "owner_contact": str((access or {}).get("owner_contact") or "").strip(),
            "reference": ref,
            "note": str((access or {}).get("note") or "").strip(),
        }

    def set_access(self, camera_id: str, access: Dict[str, Any], granted_by: str):
        a = self.validate_access(access)
        self._exec("""INSERT INTO access_grants (camera_id, basis, owner_name, owner_contact, reference, note, granted_by, granted_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                      ON CONFLICT(camera_id) DO UPDATE SET basis=excluded.basis, owner_name=excluded.owner_name,
                        owner_contact=excluded.owner_contact, reference=excluded.reference, note=excluded.note,
                        granted_by=excluded.granted_by, granted_at=excluded.granted_at, revoked_by=NULL, revoked_at=NULL""",
                   (camera_id, a["basis"], a["owner_name"], a["owner_contact"], a["reference"], a["note"], granted_by, _now()))
        return self.get_access(camera_id)

    def get_access(self, camera_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT * FROM access_grants WHERE camera_id = ?", (camera_id,))
        if row:
            row["basis_label"] = ACCESS_BASES.get(row["basis"], row["basis"])
            row["revoked"] = bool(row.get("revoked_at"))
        return row

    def grants(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for r in self._all("SELECT * FROM access_grants"):
            r["basis_label"] = ACCESS_BASES.get(r["basis"], r["basis"])
            r["revoked"] = bool(r.get("revoked_at"))
            out[r["camera_id"]] = r
        return out

    def revoke_access(self, camera_id: str, revoked_by: str) -> bool:
        return self._exec("UPDATE access_grants SET revoked_by = ?, revoked_at = ? WHERE camera_id = ? AND revoked_at IS NULL",
                          (revoked_by, _now(), camera_id)).rowcount > 0

    def clear_access(self, camera_id: str):
        self._exec("DELETE FROM access_grants WHERE camera_id = ?", (camera_id,))

    # ── preferences ────────────────────────────────────────────────────
    def get_preferences(self, username: str) -> Dict[str, Any]:
        out = {}
        for r in self._all("SELECT key, value FROM preferences WHERE username = ?", (username,)):
            try:
                out[r["key"]] = json.loads(r["value"])
            except ValueError:
                pass
        return out

    def set_preferences(self, username: str, values: Dict[str, Any]):
        for key, value in values.items():
            if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,64}", key):
                continue
            self._exec("""
                INSERT INTO preferences (username, key, value, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(username, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (username, key, json.dumps(value), _now()))

    # ── logs ───────────────────────────────────────────────────────────
    def audit(self, username: Optional[str], action: str, target: str = "", detail: str = "", ip: str = ""):
        self._exec("INSERT INTO audit_log (username, action, target, detail, ip, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (username, action, target, str(detail)[:1000], ip, _now()))

    def audit_entries(self, limit: int = 200, username: str = "", action: str = "") -> List[Dict[str, Any]]:
        sql, params = "SELECT * FROM audit_log WHERE 1=1", []
        if username:
            sql += " AND username = ?"
            params.append(username)
        if action:
            sql += " AND action LIKE ?"
            params.append(f"{action}%")
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 1000)))
        return self._all(sql, tuple(params))

    def log_voice(self, username: str, text: str, action: str, response: str, source: str) -> Dict[str, Any]:
        cur = self._exec("INSERT INTO voice_log (username, text, action, response, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         (username, text, action, response, source, _now()))
        return {"id": cur.lastrowid}

    def voice_entries(self, username: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        if username:
            return self._all("SELECT * FROM voice_log WHERE username = ? ORDER BY id DESC LIMIT ?", (username, limit))
        return self._all("SELECT * FROM voice_log ORDER BY id DESC LIMIT ?", (limit,))

    # ── incidents workflow ─────────────────────────────────────────────
    def incidents(self, days: int = 7, status: str = "", limit: int = 500) -> List[Dict[str, Any]]:
        sql, params = "SELECT * FROM incidents WHERE 1=1", []
        if days > 0:
            sql += " AND timestamp >= ?"
            params.append((datetime.now() - timedelta(days=days)).isoformat())
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        return self._all(sql, tuple(params))

    def update_incident(self, code: str, username: str, action: str, note: str = "") -> Optional[Dict[str, Any]]:
        row = self._one("SELECT * FROM incidents WHERE incident_code = ?", (code,))
        if not row:
            return None
        now = _now()
        if action == "acknowledge":
            self._exec("UPDATE incidents SET status = 'acknowledged', acknowledged_by = ?, acknowledged_at = ? WHERE incident_code = ?",
                       (username, now, code))
        elif action == "resolve":
            self._exec("UPDATE incidents SET status = 'resolved', resolved_by = ?, resolved_at = ? WHERE incident_code = ?",
                       (username, now, code))
        elif action == "false_alarm":
            self._exec("UPDATE incidents SET status = 'false_alarm', resolved_by = ?, resolved_at = ? WHERE incident_code = ?",
                       (username, now, code))
        elif action == "reopen":
            self._exec("UPDATE incidents SET status = 'open', resolved_by = NULL, resolved_at = NULL WHERE incident_code = ?", (code,))
        elif action != "note":
            raise ValueError("Unknown incident action.")
        if note:
            stamp = f"[{now} {username}] {note.strip()}"
            notes = f"{row['notes']}\n{stamp}" if row.get("notes") else stamp
            self._exec("UPDATE incidents SET notes = ? WHERE incident_code = ?", (notes, code))
        return self._one("SELECT * FROM incidents WHERE incident_code = ?", (code,))

    def latest_open_incident(self) -> Optional[Dict[str, Any]]:
        return self._one("SELECT * FROM incidents WHERE status = 'open' ORDER BY timestamp DESC LIMIT 1")

    def incident_stats(self, days: int = 30) -> Dict[str, Any]:
        rows = self.incidents(days=days, limit=100000)
        by = lambda key: sorted(
            ({"name": k, "count": sum(1 for r in rows if (r.get(key) or "—") == k)} for k in {(r.get(key) or "—") for r in rows}),
            key=lambda x: -x["count"])
        hours = [0] * 24
        days_map: Dict[str, int] = {}
        for r in rows:
            try:
                dt = datetime.fromisoformat(r["timestamp"])
            except (TypeError, ValueError):
                continue
            hours[dt.hour] += 1
            day = dt.date().isoformat()
            days_map[day] = days_map.get(day, 0) + 1
        start = datetime.now().date() - timedelta(days=max(days, 1) - 1)
        daily = [{"date": (start + timedelta(days=i)).isoformat(),
                  "count": days_map.get((start + timedelta(days=i)).isoformat(), 0)} for i in range(max(days, 1))]
        return {
            "total": len(rows),
            "open": sum(1 for r in rows if r.get("status") == "open"),
            "by_type": by("event_type"),
            "by_sector": by("sector"),
            "by_level": by("risk_level"),
            "by_status": by("status"),
            "by_hour": [{"hour": h, "count": c} for h, c in enumerate(hours)],
            "daily": daily,
        }
