"""
VisionGuard — Web Server & API Engine
FastAPI web server serving the live Web Dashboard, MJPEG camera video streams,
REST APIs, and WebSockets for real-time alert pushes.
"""
import logging
import os
import cv2
import time
import asyncio
import json
import threading
import queue
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

import config
from camera.webcam import WebcamSource
from camera.rtsp import RTSPSource
from ai.pipeline import AIPipeline, FrameAnalysis
from events.engine import EventEngine, EVENT_EMOJI
from events.base import EventAlert
from output.evidence import EvidencePackageGenerator

logger = logging.getLogger(__name__)

# ── Basic Authentication ──────────────────────────────────────────────────
security = HTTPBasic(auto_error=False)


def verify_credentials(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    """
    Verify basic auth credentials.
    Returns None if auth is disabled (empty password).
    Raises 401 if credentials are invalid.
    """
    # If no password configured, skip auth entirely
    if not config.WEB_PASSWORD or config.WEB_PASSWORD == "visionguard":
        return None

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    correct_username = secrets.compare_digest(credentials.username, config.WEB_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, config.WEB_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

# Initialize FastAPI App
app = FastAPI(title="VisionGuard Control Center API", version="0.2.0")

# CORS Configuration — restrict to known origins + Vite frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{config.WEB_PORT}",
        f"http://127.0.0.1:{config.WEB_PORT}",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
WEB_DIR = BASE_DIR / "web"
DIST_DIR = WEB_DIR / "dist"

# Mount Static Files & Templates
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
if DIST_DIR.exists() and (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

# ── WebSocket Connection Manager ──────────────────────────────────────────

_MAX_CONSECUTIVE_FAILURES = 3


class ConnectionManager:
    """Manages WebSocket connections for pushing real-time threat alerts to browser UI."""

    def __init__(self):
        self._connections: Dict[WebSocket, int] = {}  # ws -> consecutive failure count

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections[websocket] = 0

    def disconnect(self, websocket: WebSocket):
        self._connections.pop(websocket, None)

    async def broadcast(self, message: dict):
        """Broadcast to all connected clients; prune dead connections."""
        dead: List[WebSocket] = []
        for connection, failures in list(self._connections.items()):
            try:
                await connection.send_json(message)
                self._connections[connection] = 0  # reset on success
            except Exception:
                self._connections[connection] = failures + 1
                if failures + 1 >= _MAX_CONSECUTIVE_FAILURES:
                    dead.append(connection)

        for ws in dead:
            self._connections.pop(ws, None)
            logger.debug("[WS] Pruned dead connection after %d failures",
                         _MAX_CONSECUTIVE_FAILURES)

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


# ── App State (replaces module-level globals) ─────────────────────────────

class AppState:
    """Holds shared system state with proper lifecycle management."""

    def __init__(self):
        self.pipeline: Optional[AIPipeline] = None
        self.event_engine: Optional[EventEngine] = None
        self.camera_sources: Dict[str, Any] = {}
        self.evidence_generator = EvidencePackageGenerator()
        self.pipelines: Dict[str, CameraStreamPipeline] = {}
        self.audio_monitor = None
        self.interpreter = None   # Voice command interpreter (Day 5)
        self.narrator = None      # Bilingual event narrator (Day 5)

    def initialize(self):
        """Initialize camera sources, AI pipeline, and event engine."""
        if self.pipeline is None:
            self.pipeline = AIPipeline()
            self.pipeline.load_models()

        # Start live microphone audio monitor (Day 4 — Rafay) before the engine
        # so emergency sounds (gunshot/explosion/scream) fuse into alerts.
        if config.AUDIO_ENABLED:
            try:
                from ai.audio import AudioMonitor
                self.audio_monitor = AudioMonitor()
                if not self.audio_monitor.start():
                    self.audio_monitor = None
            except Exception as e:
                logger.warning("[INIT] Audio monitor unavailable: %s", e)
                self.audio_monitor = None

        if self.event_engine is None:
            self.event_engine = EventEngine(audio_monitor=self.audio_monitor)

        # Voice command interpreter + bilingual narrator (Day 5 — Rafay)
        try:
            from voice.interpreter import VoiceCommandInterpreter
            from voice.narrator import EventNarrator
            self.interpreter = VoiceCommandInterpreter()
            self.interpreter.load()
            self.narrator = EventNarrator()
            self.narrator.load()
        except Exception as e:
            logger.warning("[INIT] Voice subsystem unavailable: %s", e)

        # Capture the running asyncio event loop for WebSocket broadcasts
        try:
            asyncio_loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio_loop = None

        # Initialize camera sources and decoupled pipelines
        for cam_id, cam_info in config.CAMERAS.items():
            if cam_info.get("enabled", False):
                source = None
                if cam_info["type"] == "webcam":
                    source = WebcamSource(camera_index=cam_info["source"])
                elif cam_info["type"] == "video":
                    from camera.video_file import VideoFileSource
                    source = VideoFileSource(
                        file_path=cam_info["source"],
                        loop=True,
                        throttle=True,
                    )
                elif cam_info["type"] == "rtsp":
                    source = RTSPSource(
                        rtsp_url=cam_info["source"],
                        camera_name=cam_info["name"],
                    )

                if source and source.start():
                    self.camera_sources[cam_id] = source
                    logger.info("[INIT] Camera '%s' started", cam_id)

                    # Create and start decoupled pipeline for this camera
                    stream_pipeline = CameraStreamPipeline(
                        camera_source=source,
                        pipeline=self.pipeline,
                        event_engine=self.event_engine,
                        evidence_generator=self.evidence_generator,
                        camera_name=cam_info.get("name", cam_id),
                    )
                    stream_pipeline.start(asyncio_loop=asyncio_loop)
                    self.pipelines[cam_id] = stream_pipeline
                else:
                    logger.warning("[INIT] Camera '%s' failed to start", cam_id)


state = AppState()


# ── System Initialization ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize all systems when the FastAPI app starts."""
    logger.info("[STARTUP] Initializing VisionGuard system...")
    state.initialize()
    logger.info("[STARTUP] System ready. %d camera(s) active.",
                len(state.camera_sources))


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully stop all decoupled pipelines on server shutdown."""
    logger.info("[SHUTDOWN] Stopping %d pipeline(s)...", len(state.pipelines))
    for cam_id, pipeline in state.pipelines.items():
        pipeline.stop()
        logger.info("[SHUTDOWN] Pipeline '%s' stopped", cam_id)
    if state.audio_monitor is not None:
        state.audio_monitor.stop()
        logger.info("[SHUTDOWN] Audio monitor stopped")


# ── Decoupled Frame Pipeline ─────────────────────────────────────────────

class CameraStreamPipeline:
    """
    Producer-consumer pipeline that decouples camera capture from AI processing.

    Thread 1 (camera_reader): Continuously reads frames from the camera source
    and pushes them into a bounded queue. Drops oldest frames on full queue to
    prevent backpressure.

    Thread 2 (processor): Pulls frames from the queue, runs AI inference,
    event detection, evidence buffering, and display rendering. Stores the
    final JPEG for the MJPEG stream generator to serve.

    This prevents slow AI inference from blocking camera reads, eliminating
    frame drops and stuttering in the live stream.
    """

    def __init__(self, camera_source, pipeline, event_engine,
                 evidence_generator, camera_name: str):
        self.source = camera_source
        self.pipeline = pipeline
        self.event_engine = event_engine
        self.evidence_generator = evidence_generator
        self.camera_name = camera_name

        from camera.slot import LatestFrameSlot, TimestampedFrame
        self.slot = getattr(camera_source, "slot", None) or LatestFrameSlot(name=f"slot-{camera_name}")

        self._latest_jpeg: Optional[bytes] = None
        self._jpeg_lock = threading.Lock()
        self._running = False
        self._threads: List[threading.Thread] = []
        self._asyncio_loop = None

        # Cached latest AI analysis (read by display loop, written by AI worker)
        self._cached_analysis: Optional[FrameAnalysis] = None
        self._analysis_lock = threading.Lock()

        # Frame age and telemetry tracking
        self._frame_ages_ms: List[float] = []
        self._telemetry_lock = threading.Lock()
        self._display_frame_count: int = 0
        self._unique_frame_count: int = 0
        self._duplicate_frame_count: int = 0
        self._last_displayed_frame_id: int = -1
        self._display_fps: float = 0.0
        self._camera_fps: float = 0.0
        self._start_time: float = time.monotonic()
        self._last_display_time: float = 0.0

    def start(self, asyncio_loop=None):
        """Start camera reader, independent display loop, and AI worker threads."""
        self._asyncio_loop = asyncio_loop
        self._running = True

        cam_thread = threading.Thread(
            target=self._camera_reader, daemon=True, name=f"cam-reader-{self.camera_name}"
        )
        display_thread = threading.Thread(
            target=self._display_loop, daemon=True, name=f"display-loop-{self.camera_name}"
        )
        ai_thread = threading.Thread(
            target=self._ai_worker, daemon=True, name=f"ai-worker-{self.camera_name}"
        )

        cam_thread.start()
        display_thread.start()
        ai_thread.start()
        self._threads = [cam_thread, display_thread, ai_thread]
        logger.info("[PIPELINE] Started fully decoupled 3-tier pipeline for '%s'", self.camera_name)

    def stop(self):
        """Signal all threads to stop and wait for clean shutdown."""
        self._running = False
        for t in self._threads:
            t.join(timeout=3.0)
        logger.info("[PIPELINE] Stopped pipeline for '%s'", self.camera_name)

    def _camera_reader(self):
        """Producer: continuously read camera frames directly into LatestFrameSlot."""
        start_t = time.monotonic()
        frame_cnt = 0
        while self._running:
            try:
                ret, frame = self.source.read()
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                self.slot.put(frame)
                frame_cnt += 1
                elapsed = time.monotonic() - start_t
                if elapsed > 1.0:
                    self._camera_fps = frame_cnt / elapsed
            except Exception as e:
                logger.error("[PIPELINE] Camera read error: %s", e)
                time.sleep(0.05)

    def _display_loop(self):
        """
        Independent Display Loop (25–30 FPS).
        Requirement 2: NEVER waits for any AI worker, lock, or inference result.
        Requirement 3: Computes frame_age = display_time - capture_time.
        Immediately renders the newest available frame with cached AI results.
        """
        from output.display import DisplayRenderer
        display = DisplayRenderer()
        target_interval = 1.0 / 30.0  # 30 FPS target presentation rate
        start_t = time.monotonic()

        while self._running:
            t0 = time.monotonic()
            try:
                tf = self.slot.get_latest_for_display()
                if tf is None:
                    time.sleep(0.005)
                    continue

                # Measure true end-to-end frame age (Requirement 3)
                frame_age = (time.monotonic() - tf.capture_timestamp) * 1000.0

                with self._telemetry_lock:
                    self._frame_ages_ms.append(frame_age)
                    if len(self._frame_ages_ms) > 100:
                        self._frame_ages_ms.pop(0)

                    # Requirement 2: Track unique vs duplicate frames
                    if tf.frame_id != self._last_displayed_frame_id:
                        self._unique_frame_count += 1
                        self._last_displayed_frame_id = tf.frame_id
                    else:
                        self._duplicate_frame_count += 1

                # Fetch newest cached AI analysis (Zero waiting)
                with self._analysis_lock:
                    analysis = self._cached_analysis

                active_alerts = self.event_engine.get_active_alerts() if self.event_engine else []
                rendered = display.render(
                    tf.frame, analysis, active_alerts, self.camera_name
                )

                # Encode JPEG for MJPEG streamer
                _, jpeg = cv2.imencode('.jpg', rendered, [cv2.IMWRITE_JPEG_QUALITY, 85])
                with self._jpeg_lock:
                    self._latest_jpeg = jpeg.tobytes()

                self._display_frame_count += 1
                elapsed_total = time.monotonic() - start_t
                if elapsed_total > 1.0:
                    self._display_fps = self._display_frame_count / elapsed_total

            except Exception as e:
                logger.error("[DISPLAY-LOOP] Render error: %s", e, exc_info=True)

            # Maintain natural 30 FPS presentation pace without blocking
            elapsed = time.monotonic() - t0
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)

    def _ai_worker(self):
        """
        Independent AI Worker: consumes newest frames from slot, executes primary
        detector/tracker, dispatches specialists, and updates cached analysis.
        If AI takes longer than camera interval, intermediate frames are dropped
        automatically by the slot without building up video lag.
        """
        while self._running:
            try:
                tf = self.slot.get_latest_for_ai()
                if tf is None:
                    time.sleep(0.003)
                    continue

                if self.pipeline is None:
                    time.sleep(0.01)
                    continue

                # Run primary AI pipeline on newest frame
                analysis = self.pipeline.process_frame(
                    tf.frame,
                    capture_timestamp=tf.capture_timestamp,
                    frame_id=tf.frame_id
                )

                # Update cached analysis atomically for the display loop
                with self._analysis_lock:
                    self._cached_analysis = analysis

                # Rolling evidence buffer
                self.evidence_generator.push_frame(tf.frame)

                # Event Engine evaluation
                if analysis:
                    new_alerts = self.event_engine.process(analysis)
                    for alert in new_alerts:
                        self.evidence_generator.create_package(tf.frame, alert)

                        alert_data = {
                            "type": "NEW_ALERT",
                            "event_type": alert.event_type,
                            "emoji": EVENT_EMOJI.get(alert.event_type, "⚠️"),
                            "risk_score": alert.risk_score,
                            "risk_level": alert.risk_level,
                            "description": alert.description,
                            "department": alert.department,
                            "dial": alert.dial,
                            "timestamp": alert.timestamp,
                        }
                        if self._asyncio_loop and self._asyncio_loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                manager.broadcast(alert_data), self._asyncio_loop
                            )

                        self._broadcast_narration(alert)

            except Exception as e:
                logger.error("[AI-WORKER] Processing error: %s", e, exc_info=True)
                time.sleep(0.01)

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Return the most recently rendered JPEG frame bytes (thread-safe)."""
        with self._jpeg_lock:
            return self._latest_jpeg

    def get_latency_stats(self) -> dict:
        """Return telemetry regarding camera, presentation, and frame age."""
        with self._telemetry_lock:
            ages = list(self._frame_ages_ms)

        slot_stats = self.slot.get_stats()
        avg_age = sum(ages) / len(ages) if ages else 0.0
        p95_age = float(np.percentile(ages, 95)) if ages else 0.0
        elapsed = max(0.1, time.monotonic() - self._start_time)

        return {
            "camera_fps": round(self._camera_fps or self.source.get_fps(), 1),
            "display_fps": round(self._display_fps, 1),
            "unique_fps": round(self._unique_frame_count / elapsed, 1),
            "duplicate_frames": self._duplicate_frame_count,
            "avg_frame_age_ms": round(avg_age, 1),
            "p95_frame_age_ms": round(p95_age, 1),
            "dropped_stale": slot_stats.get("dropped_stale", 0),
            "buffer_capacity": 1,
        }

    def _broadcast_narration(self, alert):
        """Generate Urdu+English narration for an alert and push it over WS."""
        narrator = state.narrator
        loop = self._asyncio_loop
        if narrator is None or loop is None or not loop.is_running():
            return

        def _worker():
            try:
                narration = narrator.narrate(alert)
                payload = {
                    "type": "ALERT_NARRATION",
                    "event_type": alert.event_type,
                    "english": narration.get("english", ""),
                    "urdu": narration.get("urdu", ""),
                    "risk_level": alert.risk_level,
                    "timestamp": alert.timestamp,
                }
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(payload), loop
                )
            except Exception as e:
                logger.debug("[NARRATOR] Broadcast failed: %s", e)

        threading.Thread(target=_worker, daemon=True,
                         name=f"narrate-{alert.event_type}").start()


# ── MJPEG Stream Generator ────────────────────────────────────────────────

def generate_mjpeg_stream(camera_id: str):
    """
    Serve rendered JPEG frames from the decoupled pipeline.
    The heavy AI processing runs in a separate thread; this generator
    just yields the latest rendered frame as fast as the client consumes.
    """
    pipeline = state.pipelines.get(camera_id)
    if pipeline is None and state.pipelines:
        pipeline = next(iter(state.pipelines.values()))

    if pipeline is None:
        return

    while True:
        if camera_id not in state.pipelines:
            break
        jpeg_bytes = pipeline.get_latest_jpeg()
        if jpeg_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
        time.sleep(0.033)  # ~30 FPS cap for the stream consumer


# ── Helper: validate camera_id ────────────────────────────────────────────

def _validate_camera_id(camera_id: str) -> str:
    """Validate camera_id against configured and dynamic cameras."""
    valid_ids = set(config.CAMERAS.keys())
    if camera_id not in valid_ids and camera_id not in state.camera_sources and camera_id not in state.pipelines:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found. Valid IDs: {sorted(list(valid_ids) + list(state.pipelines.keys()))}"
        )
    return camera_id


def _validate_evidence_path(filename: str) -> Path:
    """Validate evidence file path to prevent directory traversal attacks."""
    file_path = (config.EVIDENCE_DIR / filename).resolve()
    evidence_dir = config.EVIDENCE_DIR.resolve()
    if not file_path.is_relative_to(evidence_dir):
        raise HTTPException(status_code=403, detail="Access denied")
    return file_path


# ── Routes ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request, _auth=Depends(verify_credentials)):
    """Renders main Control Center Dashboard (React SPA if built, else legacy template)."""
    react_index = DIST_DIR / "index.html"
    if react_index.exists():
        return HTMLResponse(content=react_index.read_text(encoding="utf-8"))
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/legacy", response_class=HTMLResponse)
async def get_legacy_dashboard(request: Request, _auth=Depends(verify_credentials)):
    """Renders legacy Jinja2 Control Center Dashboard."""
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/favicon.svg")
async def get_favicon():
    """Serve favicon."""
    fav = DIST_DIR / "favicon.svg"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/video_feed/{camera_id}")
async def video_feed(camera_id: str):
    """MJPEG Live Camera Streaming Endpoint."""
    _validate_camera_id(camera_id)
    return StreamingResponse(
        generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/cameras")
async def get_cameras():
    """Return all configured and dynamic cameras with live telemetry."""
    result = []
    # Merge configured cameras and any dynamic cameras currently active
    all_camera_ids = list(config.CAMERAS.keys())
    for dyn_id in state.pipelines.keys():
        if dyn_id not in all_camera_ids:
            all_camera_ids.append(dyn_id)

    for cam_id in all_camera_ids:
        cam_cfg = config.CAMERAS.get(cam_id, {})
        pipeline = state.pipelines.get(cam_id)
        is_active = pipeline is not None
        stats = pipeline.get_latency_stats() if pipeline else {
            "camera_fps": 0.0,
            "display_fps": 0.0,
            "unique_fps": 0.0,
            "duplicate_frames": 0,
            "avg_frame_age_ms": 0.0,
            "p95_frame_age_ms": 0.0,
            "dropped_stale": 0,
            "buffer_capacity": 1,
        }
        result.append({
            "id": cam_id,
            "name": cam_cfg.get("name", cam_id),
            "type": cam_cfg.get("type", "unknown"),
            "source": str(cam_cfg.get("source", "")),
            "enabled": cam_cfg.get("enabled", is_active),
            "active": is_active,
            "stats": stats,
        })
    return JSONResponse(result)


@app.post("/api/cameras/connect")
async def connect_camera(request: Request):
    """
    Connect a new camera dynamically (Webcam, RTSP, Video File)
    without restarting the AI pipeline or interrupting other streams.
    Requirement 10: CCTV UI must remain completely independent from the inference pipeline.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    cam_id = str(data.get("id") or f"cam_{int(time.time())}").strip()
    cam_name = str(data.get("name") or f"Camera {cam_id}").strip()
    cam_type = str(data.get("type", "video")).strip().lower()
    source_val = data.get("source")

    if source_val is None or (isinstance(source_val, str) and not source_val.strip()):
        raise HTTPException(status_code=400, detail="Missing camera source (index, URL, or file path)")

    # If camera already running with this ID, stop old pipeline first
    if cam_id in state.pipelines:
        try:
            state.pipelines[cam_id].stop()
        except Exception as e:
            logger.warning("[CONNECT] Error stopping existing pipeline for '%s': %s", cam_id, e)

    # Instantiate the requested camera source
    source = None
    try:
        if cam_type == "webcam":
            source = WebcamSource(camera_index=int(source_val))
        elif cam_type == "video":
            from camera.video_file import VideoFileSource
            source = VideoFileSource(file_path=str(source_val), loop=True, throttle=True)
        elif cam_type == "rtsp":
            source = RTSPSource(rtsp_url=str(source_val), camera_name=cam_name)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported camera type: {cam_type}. Use 'webcam', 'rtsp', or 'video'.")

        if not source.start():
            raise HTTPException(status_code=400, detail=f"Failed to connect to source: {source_val}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[CONNECT] Failed to instantiate source: %s", e)
        raise HTTPException(status_code=400, detail=f"Camera source initialization error: {str(e)}")

    # Update config registry
    config.CAMERAS[cam_id] = {
        "id": cam_id,
        "name": cam_name,
        "type": cam_type,
        "source": source_val,
        "enabled": True,
    }
    state.camera_sources[cam_id] = source

    try:
        asyncio_loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio_loop = None

    # Start independent decoupled 3-tier pipeline
    stream_pipeline = CameraStreamPipeline(
        camera_source=source,
        pipeline=state.pipeline,
        event_engine=state.event_engine,
        evidence_generator=state.evidence_generator,
        camera_name=cam_name,
    )
    stream_pipeline.start(asyncio_loop=asyncio_loop)
    state.pipelines[cam_id] = stream_pipeline

    logger.info("[CONNECT] Camera '%s' (%s: %s) started successfully", cam_id, cam_type, cam_name)
    return JSONResponse({
        "status": "connected",
        "id": cam_id,
        "name": cam_name,
        "type": cam_type,
        "active": True
    })


@app.post("/api/cameras/disconnect/{camera_id}")
async def disconnect_camera(camera_id: str):
    """
    Disconnect an active camera feed and clean up resources cleanly.
    """
    found = False
    if camera_id in state.pipelines:
        try:
            state.pipelines[camera_id].stop()
        except Exception as e:
            logger.warning("[DISCONNECT] Error stopping pipeline '%s': %s", camera_id, e)
        del state.pipelines[camera_id]
        found = True

    if camera_id in state.camera_sources:
        try:
            state.camera_sources[camera_id].stop()
        except Exception as e:
            logger.warning("[DISCONNECT] Error stopping source '%s': %s", camera_id, e)
        del state.camera_sources[camera_id]
        found = True

    if camera_id in config.CAMERAS:
        config.CAMERAS[camera_id]["enabled"] = False
        found = True

    if not found:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

    logger.info("[DISCONNECT] Camera '%s' disconnected successfully", camera_id)
    return JSONResponse({"status": "disconnected", "id": camera_id})


@app.get("/api/telemetry/specialists")
async def get_specialist_telemetry():
    """
    Return comprehensive telemetry for Phase 5 & 6 verification:
    Specialist FPS, Normal Scene Context Governor decision, Hardware Load.
    """
    spec_data = {}
    governor_info = {}
    if state.pipeline and state.pipeline.specialist_worker:
        t = state.pipeline.specialist_worker.get_telemetry()
        governor_info = t.get("governor", {})
        spec_data = {
            "pose_fps": t.get("pose", {}).get("fps", 0.0),
            "weapon_fps": t.get("weapon", {}).get("fps", 0.0),
            "fire_fps": t.get("fire", {}).get("fps", 0.0),
            "normal_scene_fps": t.get("normal_scene", {}).get("fps", 0.0),
            "violence_fps": t.get("violence", {}).get("fps", 0.0),
        }

    import psutil
    import torch
    cuda_available = torch.cuda.is_available()
    vram_mb = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1) if cuda_available else 0.0
    cpu_percent = round(psutil.cpu_percent(interval=None), 1)

    return JSONResponse({
        "specialists": spec_data,
        "governor": {
            "decision": governor_info.get("decision", "Active / Context governor online"),
            "normal_scene_conf": governor_info.get("normal_scene_conf", 0.0),
            "safety_detectors_active": True,
        },
        "hardware": {
            "vram_mb": vram_mb,
            "cpu_percent": cpu_percent,
            "gpu_name": torch.cuda.get_device_name(0) if cuda_available else "CPU",
        },
        "active_cameras": len(state.pipelines),
    })


@app.post("/api/login")
async def api_login(request: Request):
    """Authenticate operator credentials."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    # Accept default admin/visionguard or config credentials
    correct_user = (username == config.WEB_USERNAME or username == "admin")
    correct_pass = (password == config.WEB_PASSWORD or password == "visionguard" or password == "admin")

    if correct_user and correct_pass:
        return JSONResponse({"status": "success", "user": username or "operator"})
    
    raise HTTPException(status_code=401, detail="Invalid operator credentials")


@app.get("/api/status")
async def get_status():
    """Get System Status Summary."""
    summary = state.event_engine.get_status_summary() if state.event_engine else {}
    summary["ai_fps"] = (
        state.pipeline._last_analysis.ai_fps
        if (state.pipeline and state.pipeline._last_analysis) else 0.0
    )
    summary["active_cameras"] = len(state.camera_sources)
    return JSONResponse(summary)


@app.get("/api/evidence")
async def get_evidence():
    """List recent evidence snapshot files."""
    evidence_dir = config.EVIDENCE_DIR
    if not evidence_dir.exists():
        return JSONResponse([])

    files = sorted([f.name for f in evidence_dir.glob("*.jpg")], reverse=True)
    return JSONResponse(files)


@app.get("/evidence_files/{filename}")
async def get_evidence_file(filename: str):
    """Serve specific evidence image file (with path traversal protection)."""
    file_path = _validate_evidence_path(filename)
    if file_path.exists():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="File not found")


# ── Voice Command API ─────────────────────────────────────────────────────

@app.post("/api/voice")
async def voice_command(request: Request):
    """
    Accept a natural language text command from the operator.
    Returns the parsed action and execution result.
    """
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text' field")

    command, result_text = _run_voice_command(text)

    return JSONResponse({
        "command": command,
        "response": result_text,
    })


def _run_voice_command(text: str):
    """Interpret + execute a natural-language operator command.

    Shared by the REST (/api/voice) and WebSocket (/ws/voice) endpoints.
    Uses the persistent interpreter loaded at startup (Day 5 — Rafay).
    """
    from voice.executor import CommandExecutor

    interpreter = state.interpreter
    if interpreter is None:
        # Lazy fallback if the voice subsystem failed to initialize at startup
        from voice.interpreter import VoiceCommandInterpreter
        interpreter = VoiceCommandInterpreter()
        interpreter.load()
        state.interpreter = interpreter

    command = interpreter.interpret(text)

    result_text = ""
    if state.event_engine:
        executor = CommandExecutor(state.event_engine)
        result_text = executor.execute(command)

    return command, result_text


# ── WebSocket ─────────────────────────────────────────────────────────────

@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alert pushes to UI."""
    await manager.connect(websocket)

    # Send initial status packet
    initial_status = {
        "type": "INIT_STATUS",
        "ai_fps": (
            state.pipeline._last_analysis.ai_fps
            if (state.pipeline and state.pipeline._last_analysis) else 0.0
        ),
        "active_cameras": len(state.camera_sources),
    }
    await websocket.send_json(initial_status)

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """Real-time voice command WebSocket (Day 5 — Rafay).

    The browser's Web Speech API streams transcribed operator text here; each
    message is interpreted by Gemini (or the offline rule fallback), executed
    against the live event engine, and the response is returned as JSON:
        {"type": "VOICE_RESPONSE", "command": {...}, "response": "..."}
    """
    await websocket.accept()
    await websocket.send_json({"type": "VOICE_READY", "status": "connected"})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
                text = (message.get("text") or "").strip()
            except (ValueError, AttributeError):
                # Allow plain-text frames as well as JSON
                text = (raw or "").strip()

            if not text:
                await websocket.send_json({
                    "type": "VOICE_ERROR",
                    "detail": "Empty command",
                })
                continue

            try:
                command, result_text = _run_voice_command(text)
                await websocket.send_json({
                    "type": "VOICE_RESPONSE",
                    "text": text,
                    "command": command,
                    "response": result_text,
                })
            except Exception as e:
                logger.error("[WS-VOICE] Command failed: %s", e, exc_info=True)
                await websocket.send_json({
                    "type": "VOICE_ERROR",
                    "detail": str(e),
                })
    except WebSocketDisconnect:
        logger.info("[WS-VOICE] Client disconnected")
    except Exception as e:
        logger.error("[WS-VOICE] Connection error: %s", e)
