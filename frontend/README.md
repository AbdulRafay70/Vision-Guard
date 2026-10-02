# VisionGuard Command Center (frontend)

Operator console for the VisionGuard backend (`prototype/web/server.py`).

```bash
npm install
npm run dev      # http://localhost:5173 — proxies /api, /ws, /video_feed, /evidence_files to :8000
npm run build
```

## Pages

| Page | Purpose | Backend |
|---|---|---|
| Sign-in | Operator authentication | `POST /api/login` |
| Operations | KPIs, pinned monitoring wall, alert feed, coverage by area, command log | `/api/status`, `/api/cameras`, `ws /ws/alerts` |
| Live view | City → Area → Street tree, 1/4/9/16 layouts, zoom, full screen | `/video_feed/{id}` |
| Camera registry | City / Area / Street columns, camera table, location assignment, disconnect | `/api/cameras`, `/api/cameras/disconnect/{id}` |
| Connect camera | Site + source (RTSP, local device, video upload), test, connect | `/api/cameras/test-connection`, `/api/cameras/upload-test-video`, `/api/cameras/connect` |
| Incidents | Alert log with risk filter, evidence frames | `ws /ws/alerts`, `/api/evidence` |

The location hierarchy (cities, areas, streets and where each camera is installed) is kept in the
browser's local storage and joined to the backend camera list by camera id; the area name is sent
as the camera `sector` when connecting.

## Voice control

Press **V** (or the mic button) and speak, or type into the command bar (`/` to focus).
Console commands are handled locally; anything else goes to `POST /api/voice`, and the backend's
structured command (e.g. `switch_camera`, `show_cameras`, `zoom_in`) is applied to the console.

- “Show camera 3”, “Switch to Saddar Chowk”
- “Show Clifton cameras”, “Show Abdullah Haroon Road”, “Show all cameras”
- “Grid three by three”, “Single view”, “Zoom in”, “Full screen”
- “Add camera 2 to dashboard”, “Remove camera 2 from dashboard”
- “Open camera registry”, “Go to incidents”, “Log out”
- Backend: “What's going on?”, “System health”, “Confirm alert”

Speech recognition uses the browser Web Speech API (Chrome / Edge).
