# VisionGuard Command Center (frontend)

Operator console for the VisionGuard backend (`prototype/web/server.py`).

```bash
# backend (from prototype/)
pip install -r requirements.txt
python run_web.py                # serves the API on :8000

# frontend
npm install
npm run dev                      # http://localhost:5173 — proxies /api, /ws, /video_feed, /evidence_files to :8000
npm run build
```

## First sign-in

On first start the backend creates its tables in `prototype/data/visionguard_incidents.db` and seeds
operator accounts (`admin`, plus any in `prototype/web/users.json`) with the initial password from
`VISIONGUARD_PASS` (default `visionguard`). Every seeded account must choose a new password at first
sign-in. Five wrong passwords lock an account for 15 minutes; sessions last 12 hours.

## What is stored in the database

| Data | Table | Written by |
|---|---|---|
| Operators, hashed passwords, roles | `users`, `sessions` | Operators page, sign-in |
| Cities → areas → streets | `cities`, `areas`, `streets` | Camera registry, Connect camera |
| Cameras (name, type, source, running/stopped) | `system_cameras` | Connect / edit / start / stop / delete |
| Camera locations | `camera_locations` | Registry location column, Connect camera |
| Incidents + status, who acknowledged/resolved, notes | `incidents` | AI event engine, Incidents page, voice |
| Pinned wall, layout, voice settings | `preferences` | Saved automatically per operator |
| Every voice / typed command and reply | `voice_log` | Command bar |
| Sign-ins, camera, location, incident and account changes | `audit_log` | Everything above |

Cameras are restored from the database when the server starts. Enabled cameras that fail to connect
are retried automatically (15 s backoff, up to 5 min).

## Pages

| Page | Purpose |
|---|---|
| Operations | KPIs, pinned monitoring wall, live alert feed, coverage by area, command log |
| Live view | City → Area → Street tree, 1/4/9/16 layouts, zoom, full screen |
| Incidents | Incident log from the database; acknowledge, resolve, false alarm, notes, CSV export, evidence frames |
| Analytics | Incidents per day, by type, by area, time of day |
| Camera registry | City / Area / Street columns (add, rename, delete), camera table with start / stop / edit / delete / location |
| Connect camera | Site + source (RTSP, local device, video upload), real stream test, connect |
| System health | CPU / memory / GPU, AI throughput, per-camera stream telemetry |
| Operators | (Super Admin) create, edit, suspend, unlock, reset password, delete |
| Audit log | (Super Admin, Supervisor) full activity trail |
| Settings | Profile, change password, voice options |

Roles: **Super Admin** (everything), **Supervisor** (cameras, locations, audit), **Tactical Operator**
(start/stop cameras, incidents), **Security Analyst** (incidents), **Viewer** (read-only).

## Voice control

Press **V** (or the mic button) and speak, or type into the command bar (`/` to focus). Turn on
**hands-free mode** in Settings to keep the microphone open; start each command with “Guard, …”.

- “Show camera 3”, “Switch to Saddar Chowk”
- “Show Clifton cameras”, “Show Abdullah Haroon Road”, “Show all cameras”
- “Grid three by three”, “Single view”, “Zoom in”, “Full screen”, “Next page”
- “Add camera 2 to dashboard”, “Remove camera 2 from dashboard”
- “Stop camera 4”, “Start Boat Basin”
- “Open analytics”, “Go to incidents”, “Open system health”, “Log out”
- Backend: “What's going on?”, “System health”, “Confirm alert” (acknowledges the latest open incident),
  “Dismiss alert” (closes it as a false alarm)

Speech recognition uses the browser Web Speech API (Chrome / Edge) and requires microphone
permission on `localhost` or HTTPS.
