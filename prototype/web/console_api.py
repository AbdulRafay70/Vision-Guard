"""
VisionGuard — Command Center API (auth, operators, locations, preferences,
incident workflow, voice log, audit trail).

Camera lifecycle endpoints live in web/server.py because they own the stream
pipelines; they use the same `current_user` / `require_role` helpers.
"""
import logging
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from web.console_db import (
    AuthError, CAMERA_ADMIN_ROLES, ConsoleDatabase, INCIDENT_ROLES, ROLES, USER_ADMIN_ROLES,
)

logger = logging.getLogger(__name__)

# Paths reachable without a session
PUBLIC_PATHS = {"/api/login", "/api/health"}
# Prefixes that require a session (the MJPEG <img> and WebSockets pass ?token=)
PROTECTED_PREFIXES = ("/api/", "/video_feed/", "/evidence_files/", "/ws/")


def extract_token(request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query_params.get("token", "")


def client_ip(request) -> str:
    return request.client.host if request.client else ""


def current_user(request: Request) -> Dict[str, Any]:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Sign-in required")
    return user


def require_role(request: Request, roles: Set[str]) -> Dict[str, Any]:
    user = current_user(request)
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail=f"Your role ({user['role']}) is not permitted to do this.")
    return user


def install_auth_middleware(app, db: ConsoleDatabase, enabled: bool = True):
    """Attach the signed-in operator to every request and reject unauthenticated API calls."""

    @app.middleware("http")
    async def _auth(request: Request, call_next):
        path = request.url.path
        token = extract_token(request)
        request.state.user = db.session_user(token) if token else None
        request.state.token = token
        if enabled and path.startswith(PROTECTED_PREFIXES) and path not in PUBLIC_PATHS \
                and request.method != "OPTIONS" and request.state.user is None:
            return JSONResponse({"detail": "Sign-in required"}, status_code=401)
        if not enabled and request.state.user is None:
            # Auth disabled (development): act as the built-in administrator
            request.state.user = db.get_user("admin")
        return await call_next(request)


async def _body(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_router(db: ConsoleDatabase) -> APIRouter:
    r = APIRouter(prefix="/api")

    # ── Authentication ─────────────────────────────────────────────────
    @r.post("/login")
    async def login(request: Request):
        data = await _body(request)
        try:
            result = db.authenticate(data.get("username", ""), data.get("password", ""),
                                     station=str(data.get("station", ""))[:120], ip=client_ip(request))
        except AuthError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return {"status": "success", **result}

    @r.post("/logout")
    async def logout(request: Request):
        user = current_user(request)
        db.end_session(request.state.token)
        db.audit(user["username"], "logout", ip=client_ip(request))
        return {"status": "success"}

    @r.get("/me")
    async def me(request: Request):
        user = current_user(request)
        return {"user": user, "preferences": db.get_preferences(user["username"]), "roles": ROLES}

    @r.post("/me/password")
    async def change_password(request: Request):
        user = current_user(request)
        data = await _body(request)
        if not db.check_password(user["username"], data.get("current", "")):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")
        if data.get("new") == data.get("current"):
            raise HTTPException(status_code=400, detail="New password must differ from the current one.")
        try:
            db.set_password(user["username"], data.get("new", ""))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        db.audit(user["username"], "password_changed", target=user["username"], ip=client_ip(request))
        return {"status": "success"}

    @r.get("/me/preferences")
    async def get_prefs(request: Request):
        return db.get_preferences(current_user(request)["username"])

    @r.put("/me/preferences")
    async def put_prefs(request: Request):
        user = current_user(request)
        db.set_preferences(user["username"], await _body(request))
        return db.get_preferences(user["username"])

    # ── Operator accounts ─────────────────────────────────────────────
    @r.get("/users")
    async def list_users(request: Request):
        require_role(request, USER_ADMIN_ROLES | {"Supervisor"})
        return db.list_users()

    @r.post("/users")
    async def create_user(request: Request):
        admin = require_role(request, USER_ADMIN_ROLES)
        data = await _body(request)
        try:
            user = db.create_user({**data, "must_change_password": bool(data.get("must_change_password", True))})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        db.audit(admin["username"], "user_created", target=user["username"], detail=user["role"], ip=client_ip(request))
        return JSONResponse({"status": "success", "user": user}, status_code=201)

    @r.put("/users/{username}")
    async def update_user(username: str, request: Request):
        admin = require_role(request, USER_ADMIN_ROLES)
        data = await _body(request)
        if username.lower() == admin["username"] and (data.get("status") == "Suspended" or (data.get("role") and data["role"] != admin["role"])):
            raise HTTPException(status_code=400, detail="You cannot suspend yourself or change your own role.")
        user = db.update_user(username, data)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.audit(admin["username"], "user_updated", target=username, detail=", ".join(sorted(data.keys())), ip=client_ip(request))
        return {"status": "success", "user": user}

    @r.post("/users/{username}/reset-password")
    async def reset_password(username: str, request: Request):
        admin = require_role(request, USER_ADMIN_ROLES)
        data = await _body(request)
        if not db.get_user(username):
            raise HTTPException(status_code=404, detail="User not found")
        try:
            db.set_password(username, data.get("password", ""), must_change=True)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        db.audit(admin["username"], "password_reset", target=username, ip=client_ip(request))
        return {"status": "success"}

    @r.delete("/users/{username}")
    async def delete_user(username: str, request: Request):
        admin = require_role(request, USER_ADMIN_ROLES)
        if username.lower() in ("admin", admin["username"]):
            raise HTTPException(status_code=400, detail="This account cannot be deleted.")
        if not db.delete_user(username):
            raise HTTPException(status_code=404, detail="User not found")
        db.audit(admin["username"], "user_deleted", target=username, ip=client_ip(request))
        return {"status": "success", "username": username}

    # ── Locations ─────────────────────────────────────────────────────
    @r.get("/locations")
    async def get_locations(request: Request):
        current_user(request)
        return {"cities": db.location_tree(), "placements": db.placements()}

    async def _add(request: Request, level: str, parent: Optional[str] = None):
        user = require_role(request, CAMERA_ADMIN_ROLES)
        name = (await _body(request)).get("name", "")
        try:
            node = db.add_city(name) if level == "city" else db.add_area(parent, name) if level == "area" else db.add_street(parent, name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        db.audit(user["username"], f"{level}_created", target=node["id"], detail=node["name"], ip=client_ip(request))
        return JSONResponse(node, status_code=201)

    @r.post("/locations/cities")
    async def add_city(request: Request):
        return await _add(request, "city")

    @r.post("/locations/cities/{city_id}/areas")
    async def add_area(city_id: str, request: Request):
        return await _add(request, "area", city_id)

    @r.post("/locations/areas/{area_id}/streets")
    async def add_street(area_id: str, request: Request):
        return await _add(request, "street", area_id)

    @r.put("/locations/{level}/{loc_id}")
    async def rename_location(level: str, loc_id: str, request: Request):
        user = require_role(request, CAMERA_ADMIN_ROLES)
        name = (await _body(request)).get("name", "")
        try:
            ok = db.rename_location(level, loc_id, name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not ok:
            raise HTTPException(status_code=404, detail="Location not found")
        db.audit(user["username"], f"{level}_renamed", target=loc_id, detail=name, ip=client_ip(request))
        return {"status": "success"}

    @r.delete("/locations/{level}/{loc_id}")
    async def delete_location(level: str, loc_id: str, request: Request):
        user = require_role(request, CAMERA_ADMIN_ROLES)
        try:
            ok = db.delete_location(level, loc_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not ok:
            raise HTTPException(status_code=404, detail="Location not found")
        db.audit(user["username"], f"{level}_deleted", target=loc_id, ip=client_ip(request))
        return {"status": "success"}

    @r.put("/cameras/{camera_id}/location")
    async def place_camera(camera_id: str, request: Request):
        user = require_role(request, CAMERA_ADMIN_ROLES)
        data = await _body(request)
        try:
            db.place_camera(camera_id, data.get("cityId"), data.get("areaId"), data.get("streetId"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        db.audit(user["username"], "camera_located", target=camera_id,
                 detail="/".join(filter(None, [data.get("cityId"), data.get("areaId"), data.get("streetId")])), ip=client_ip(request))
        return {"status": "success", "placements": db.placements()}

    @r.delete("/cameras/{camera_id}/location")
    async def unplace_camera(camera_id: str, request: Request):
        user = require_role(request, CAMERA_ADMIN_ROLES)
        db.unplace_camera(camera_id)
        db.audit(user["username"], "camera_unlocated", target=camera_id, ip=client_ip(request))
        return {"status": "success", "placements": db.placements()}

    # ── Incidents ─────────────────────────────────────────────────────
    @r.get("/incidents")
    async def list_incidents(request: Request, days: int = 7, status: str = "", limit: int = 500):
        current_user(request)
        return db.incidents(days=days, status=status, limit=max(1, min(limit, 5000)))

    @r.get("/incidents/stats")
    async def incident_stats(request: Request, days: int = 30):
        current_user(request)
        return db.incident_stats(days=max(1, min(days, 365)))

    @r.post("/incidents/{code}/action")
    async def incident_action(code: str, request: Request):
        user = require_role(request, INCIDENT_ROLES)
        data = await _body(request)
        action = data.get("action", "")
        try:
            row = db.update_incident(code, user["username"], action, data.get("note", ""))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")
        db.audit(user["username"], f"incident_{action}", target=code, detail=data.get("note", ""), ip=client_ip(request))
        return row

    # ── Voice log & audit ─────────────────────────────────────────────
    @r.get("/voice/log")
    async def voice_log(request: Request, limit: int = 100, scope: str = "mine"):
        user = current_user(request)
        everyone = scope == "all" and user["role"] in (USER_ADMIN_ROLES | {"Supervisor"})
        return db.voice_entries("" if everyone else user["username"], limit=max(1, min(limit, 1000)))

    @r.post("/voice/log")
    async def add_voice_log(request: Request):
        """Record a command that the console resolved locally (navigation, layout, camera focus)."""
        user = current_user(request)
        data = await _body(request)
        text = str(data.get("text", "")).strip()[:500]
        if not text:
            raise HTTPException(status_code=400, detail="Missing text")
        return db.log_voice(user["username"], text, str(data.get("action", ""))[:64],
                            str(data.get("response", ""))[:1000], "console")

    @r.get("/audit")
    async def audit(request: Request, limit: int = 200, username: str = "", action: str = ""):
        require_role(request, USER_ADMIN_ROLES | {"Supervisor"})
        return db.audit_entries(limit=limit, username=username, action=action)

    return r
