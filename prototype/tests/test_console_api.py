"""
Command Center API tests — auth, operators, locations, preferences, incidents, audit.
Runs without GPU / AI models:  python -m pytest prototype/tests -q
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.console_db import ConsoleDatabase  # noqa: E402
from web.console_api import build_router, install_auth_middleware  # noqa: E402


@pytest.fixture
def setup(tmp_path):
    db = ConsoleDatabase(tmp_path / "test.db", default_password="initial-pass")
    app = FastAPI()
    install_auth_middleware(app, db, enabled=True)
    app.include_router(build_router(db))
    return db, TestClient(app)


def login(client, username="admin", password="initial-pass"):
    res = client.post("/api/login", json={"username": username, "password": password, "station": "Test"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


def test_requires_session(setup):
    _, client = setup
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/locations").status_code == 401


def test_login_and_forced_password_change(setup):
    _, client = setup
    assert client.post("/api/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    h = login(client)
    me = client.get("/api/me", headers=h).json()
    assert me["user"]["must_change_password"] is True
    assert client.post("/api/me/password", headers=h, json={"current": "nope", "new": "new-password-1"}).status_code == 400
    assert client.post("/api/me/password", headers=h, json={"current": "initial-pass", "new": "new-password-1"}).status_code == 200
    assert client.get("/api/me", headers=h).json()["user"]["must_change_password"] is False
    login(client, password="new-password-1")


def test_lockout_after_failed_attempts(setup):
    _, client = setup
    for _ in range(5):
        client.post("/api/login", json={"username": "admin", "password": "bad"})
    res = client.post("/api/login", json={"username": "admin", "password": "initial-pass"})
    assert res.status_code == 401 and "locked" in res.json()["detail"]


def test_logout_revokes_token(setup):
    _, client = setup
    h = login(client)
    assert client.post("/api/logout", headers=h).status_code == 200
    assert client.get("/api/me", headers=h).status_code == 401


def test_location_hierarchy_and_camera_placement(setup):
    db, client = setup
    h = login(client)
    tree = client.get("/api/locations", headers=h).json()
    assert tree["cities"][0]["name"] == "Karachi"
    city = client.post("/api/locations/cities", headers=h, json={"name": "Lahore"}).json()
    area = client.post(f"/api/locations/cities/{city['id']}/areas", headers=h, json={"name": "Gulberg"}).json()
    street = client.post(f"/api/locations/areas/{area['id']}/streets", headers=h, json={"name": "MM Alam Road"}).json()
    res = client.put("/api/cameras/cam_9/location", headers=h,
                     json={"cityId": city["id"], "areaId": area["id"], "streetId": street["id"]})
    assert res.status_code == 200
    assert res.json()["placements"]["cam_9"]["streetId"] == street["id"]
    # Mismatched hierarchy is rejected
    bad = client.put("/api/cameras/cam_9/location", headers=h, json={"cityId": "karachi", "areaId": area["id"]})
    assert bad.status_code == 400
    # Deleting the area cascades to its streets and camera placement
    assert client.delete(f"/api/locations/area/{area['id']}", headers=h).status_code == 200
    assert "cam_9" not in client.get("/api/locations", headers=h).json()["placements"]


def test_user_management_and_roles(setup):
    _, client = setup
    h = login(client)
    res = client.post("/api/users", headers=h, json={"username": "op_one", "full_name": "Op One",
                                                      "role": "Viewer", "password": "viewer-pass-1"})
    assert res.status_code == 201
    v = login(client, "op_one", "viewer-pass-1")
    assert client.post("/api/locations/cities", headers=v, json={"name": "X"}).status_code == 403
    assert client.get("/api/audit", headers=v).status_code == 403
    assert client.put("/api/users/op_one", headers=h, json={"status": "Suspended"}).status_code == 200
    assert client.get("/api/me", headers=v).status_code == 401  # sessions revoked on suspension
    assert client.delete("/api/users/admin", headers=h).status_code == 400


def test_preferences_persist(setup):
    _, client = setup
    h = login(client)
    client.put("/api/me/preferences", headers=h, json={"pinned": ["cam_1", "cam_2"], "layout": 9})
    assert client.get("/api/me/preferences", headers=h).json() == {"pinned": ["cam_1", "cam_2"], "layout": 9}


def test_incident_workflow_and_audit(setup):
    db, client = setup
    h = login(client)
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        conn.execute("""INSERT INTO incidents (incident_code, sector, event_type, risk_score, risk_level, timestamp)
                        VALUES ('INC-1', 'Saddar', 'fight', 0.8, 'HIGH', datetime('now', 'localtime'))""")
    assert client.get("/api/incidents", headers=h).json()[0]["status"] == "open"
    row = client.post("/api/incidents/INC-1/action", headers=h, json={"action": "acknowledge", "note": "Unit sent"}).json()
    assert row["status"] == "acknowledged" and row["acknowledged_by"] == "admin" and "Unit sent" in row["notes"]
    stats = client.get("/api/incidents/stats?days=7", headers=h).json()
    assert stats["total"] == 1 and stats["by_type"][0]["name"] == "fight"
    actions = [a["action"] for a in client.get("/api/audit", headers=h).json()]
    assert "incident_acknowledge" in actions and "login" in actions


def test_voice_log(setup):
    _, client = setup
    h = login(client)
    client.post("/api/voice/log", headers=h, json={"text": "show camera 2", "action": "focus", "response": "Showing."})
    log = client.get("/api/voice/log", headers=h).json()
    assert log[0]["text"] == "show camera 2" and log[0]["source"] == "console"


def test_access_grant_required_and_validated(setup):
    db, _ = setup
    # Basis is mandatory
    import pytest as _pt
    with _pt.raises(ValueError):
        db.validate_access({})
    # Consent needs owner + reference
    with _pt.raises(ValueError):
        db.validate_access({"basis": "consent", "owner_name": "Shop"})
    with _pt.raises(ValueError):
        db.validate_access({"basis": "consent", "reference": "CF-1"})
    ok = db.validate_access({"basis": "consent", "owner_name": "Shop", "reference": "CF-1"})
    assert ok["basis"] == "consent"
    # Owned / public need neither
    assert db.validate_access({"basis": "public"})["basis"] == "public"


def test_access_set_revoke_and_restore(setup):
    db, _ = setup
    db.set_access("cam_x", {"basis": "consent", "owner_name": "Bank", "owner_contact": "021-111", "reference": "MOU-9"}, "admin")
    g = db.get_access("cam_x")
    assert g["basis"] == "consent" and g["owner_name"] == "Bank" and not g["revoked"]
    assert g["basis_label"] == "Owner consent on file"
    assert db.revoke_access("cam_x", "admin") is True
    assert db.get_access("cam_x")["revoked"] is True
    # Re-granting clears the revocation
    db.set_access("cam_x", {"basis": "owned"}, "admin")
    assert db.get_access("cam_x")["revoked"] is False
    assert "cam_x" in db.grants()

