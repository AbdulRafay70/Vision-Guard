"""
VisionGuard User Management & Authentication Database
Persists user accounts, roles, departments, and access controls in JSON.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent / "users.json"

DEFAULT_USERS: List[Dict[str, Any]] = [
    {
        "username": "admin",
        "full_name": "Executive Command Operator",
        "email": "admin@visionguard.gov.pk",
        "role": "Super Admin",
        "department": "Central Command & Control",
        "access_level": "Full Control",
        "status": "Active",
        "sector": "All Sectors (Karachi Grid)",
        "created_at": "2026-01-15T08:00:00Z",
        "last_login": "2026-09-07T22:00:00Z"
    },
    {
        "username": "operator_saddar",
        "full_name": "Tariq Mahmood",
        "email": "tariq.m@visionguard.gov.pk",
        "role": "Tactical Operator",
        "department": "Sector 1 - Saddar Command",
        "access_level": "Live Monitor & Patrol Control",
        "status": "Active",
        "sector": "Sector 1 - Saddar",
        "created_at": "2026-02-10T10:30:00Z",
        "last_login": "2026-09-07T21:15:00Z"
    },
    {
        "username": "analyst_clifton",
        "full_name": "Dr. Sarah Khan",
        "email": "sarah.k@visionguard.gov.pk",
        "role": "Security Analyst",
        "department": "Forensic Intelligence Unit",
        "access_level": "Evidence Export & Analytics",
        "status": "Active",
        "sector": "Sector 2 - Clifton & DHA",
        "created_at": "2026-03-01T14:20:00Z",
        "last_login": "2026-09-06T18:45:00Z"
    }
]


class UserManager:
    """Manages persistent user records for VisionGuard Command Center."""

    def __init__(self, filepath: Path = DB_FILE):
        self.filepath = filepath
        self._ensure_db()

    def _ensure_db(self):
        """Initialize database file with default users if not present."""
        if not self.filepath.exists():
            try:
                self.filepath.write_text(json.dumps(DEFAULT_USERS, indent=2), encoding="utf-8")
                logger.info("[UserManager] Created initial user database at %s", self.filepath)
            except Exception as e:
                logger.error("[UserManager] Error creating user database: %s", e)

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieve all registered system users."""
        if not self.filepath.exists():
            return DEFAULT_USERS
        try:
            data = json.loads(self.filepath.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error("[UserManager] Failed to read users file: %s", e)
            return DEFAULT_USERS

    def add_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user account with proper details."""
        users = self.get_all_users()
        
        username = user_data.get("username", "").strip().lower()
        if not username:
            raise ValueError("Username is required")

        if any(u["username"].lower() == username for u in users):
            raise ValueError(f"User with username '{username}' already exists")

        new_user = {
            "username": username,
            "full_name": user_data.get("full_name", "").strip() or username.title(),
            "email": user_data.get("email", "").strip() or f"{username}@visionguard.gov.pk",
            "role": user_data.get("role", "Tactical Operator"),
            "department": user_data.get("department", "General Surveillance"),
            "access_level": user_data.get("access_level", "Live Monitor Only"),
            "status": user_data.get("status", "Active"),
            "sector": user_data.get("sector", "Sector 1 - Saddar"),
            "created_at": user_data.get("created_at", "2026-09-07T22:30:00Z"),
            "last_login": "Never"
        }

        users.append(new_user)
        self._save(users)
        return new_user

    def update_user(self, username: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing user record."""
        users = self.get_all_users()
        for u in users:
            if u["username"].lower() == username.lower():
                for key in ["full_name", "email", "role", "department", "access_level", "status", "sector"]:
                    if key in updates:
                        u[key] = updates[key]
                self._save(users)
                return u
        return None

    def delete_user(self, username: str) -> bool:
        """Delete a user from the system."""
        users = self.get_all_users()
        initial_len = len(users)
        users = [u for u in users if u["username"].lower() != username.lower()]
        if len(users) < initial_len:
            self._save(users)
            return True
        return False

    def _save(self, users: List[Dict[str, Any]]):
        """Save users list to disk."""
        try:
            self.filepath.write_text(json.dumps(users, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("[UserManager] Error saving users: %s", e)
