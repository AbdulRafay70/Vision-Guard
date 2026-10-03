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
| Demo footage | Preview the sample clips in `prototype/Videos` (and uploaded clips) and stream them as looping cameras, each placed in an area and pinned to the wall |
| System health | CPU / memory / GPU, AI throughput, per-camera stream telemetry |
| Operators | (Super Admin) create, edit, suspend, unlock, reset password, delete |
| Audit log | (Super Admin, Supervisor) full activity trail |
| Settings | Profile, change password, voice options |

Roles: **Super Admin** (everything), **Supervisor** (cameras, locations, audit), **Tactical Operator**
(start/stop cameras, incidents), **Security Analyst** (incidents), **Viewer** (read-only).

## Connecting DVRs, NVRs and WiFi cameras

**Connect camera → Camera or DVR / NVR (auto-detect)**: choose *Standalone IP / WiFi camera* or
*DVR / NVR recorder*, enter the IP address, username and password (or press **Scan** to find devices on
the LAN), then **Detect**. In one pass the server:

1. checks which camera ports are open;
2. asks the device over **ONVIF** for its exact stream URLs (every recorder channel is listed);
3. otherwise tries the stream paths of known brands — Hikvision / HiLook / Ezviz, Dahua / CP Plus / Imou,
   Uniview, XMeye, TVT, Reolink, Tapo, V380, Yoosee, CamHi, Axis, Hanwha and generic — using a fast RTSP
   handshake that also tells a wrong password apart from a wrong path;
4. falls back to HTTP MJPEG for simple WiFi cameras;
5. grabs a live frame from every stream it found.

Tick the channels to keep, choose the city / area / street, and **Add** — all channels are saved, linked
to the recorder, started in parallel and pinned to the wall.

Streams use RTSP over TCP (falling back to UDP), with open/read timeouts, a stall watchdog and
automatic reconnects (2 s → 30 s backoff, forever). A camera that drops shows *Connecting* or *Fault*
with the reason (wrong password, path not found, unreachable) and comes back on its own.

Requirements: the server must be on the same network / VLAN as the devices (or have the RTSP port
forwarded), and RTSP or ONVIF must be enabled on the device (on many Hikvision / Dahua units ONVIF is off
by default and needs its own user).

## Voice control

Press **V** (or the mic button) and speak, or type into the command bar (`/` to focus). Turn on
**hands-free mode** in Settings to keep the microphone open; start each command with “Guard, …”.

- “Show camera 3”, “Switch to Saddar Chowk”
- “Show Clifton cameras”, “Show Abdullah Haroon Road”, “Show all cameras”
- “Grid three by three”, “Single view”, “Zoom in”, “Full screen”, “Next page”
- “Add camera 2 to dashboard”, “Remove camera 2 from dashboard”
- “Stop camera 4”, “Start Boat Basin”
- “Load demo videos” (streams every sample clip and pins it to the dashboard)
- “Open analytics”, “Go to incidents”, “Open system health”, “Log out”
- Backend: “What's going on?”, “System health”, “Confirm alert” (acknowledges the latest open incident),
  “Dismiss alert” (closes it as a false alarm)

Speech recognition uses the browser Web Speech API (Chrome / Edge) and requires microphone
permission on `localhost` or HTTPS.
