"""
VisionGuard — Interactive Video Detection Testing Studio (Tkinter Desktop UI)
Provides an interactive desktop application where the user can:
- Select and switch between all videos in 'D:\\testing videos' and 'prototype\\test_videos'
- Browse and select any custom video file from their PC
- Start, Pause, Resume, Stop, and Change videos on the fly
- View real-time AI detections (Fire/Smoke, Weapons, Violence, Poses, Tracks) at smooth presentation FPS
- View real-time risk scores, department dispatch actions, and system telemetry
"""
import sys
import os
import time
import queue
import threading
import glob
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure stdout/stderr don't crash on Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add prototype directory to path
PROTOTYPE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROTOTYPE_DIR))

import cv2
import torch
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

import config
from ai.pipeline import AIPipeline, FrameAnalysis
from events.engine import EventEngine, EVENT_EMOJI
from events.base import EventAlert
from output.display import DisplayRenderer


class VisionGuardStudio(tk.Tk):
    """Modern Desktop UI for VisionGuard Multi-Video Testing."""

    def __init__(self):
        super().__init__()
        self.title("VisionGuard AI — Multi-Video Testing Studio")
        self.geometry("1280x820")
        self.minsize(1050, 700)
        self.configure(bg="#12141a")

        # Application state
        self.pipeline: Optional[AIPipeline] = None
        self.engine: Optional[EventEngine] = None
        self.display_renderer = DisplayRenderer()

        self.video_cap: Optional[cv2.VideoCapture] = None
        self.current_video_path: Optional[str] = None
        self.is_running = False
        self.is_paused = False

        self.worker_thread: Optional[threading.Thread] = None
        self.frame_queue = queue.Queue(maxsize=2)
        self.alert_queue = queue.Queue()

        self.current_frame_id = 0
        self.total_frames = 0
        self.source_fps = 30.0

        # UI Styling
        self._init_styles()
        self._build_layout()
        self._populate_video_list()

        # Handle window close cleanly
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start periodic GUI refresh timer
        self.after(20, self._gui_update_loop)

        # Lazy load AI models in background so GUI appears instantly
        self.after(100, self._start_model_loader)

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Custom dark colors
        self.bg_dark = "#12141a"
        self.bg_panel = "#1a1d24"
        self.bg_card = "#222733"
        self.accent_cyan = "#00d2ff"
        self.accent_green = "#00e676"
        self.accent_red = "#ff3d00"
        self.text_main = "#f0f2f5"
        self.text_dim = "#9aa0a6"

        style.configure("TFrame", background=self.bg_dark)
        style.configure("Panel.TFrame", background=self.bg_panel)
        style.configure("Card.TFrame", background=self.bg_card)

        style.configure("TLabel", background=self.bg_panel, foreground=self.text_main, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.bg_dark, foreground=self.accent_cyan, font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", background=self.bg_panel, foreground=self.text_dim, font=("Segoe UI", 9))
        style.configure("Alert.TLabel", background=self.bg_card, foreground=self.accent_red, font=("Segoe UI", 10, "bold"))

    def _build_layout(self):
        # ── Top Header ───────────────────────────────────────────
        header = tk.Frame(self, bg=self.bg_dark, height=50)
        header.pack(fill=tk.X, padx=15, pady=(10, 5))

        title = tk.Label(header, text="🛡️ VISIONGUARD AI — MULTI-VIDEO DETECTION STUDIO",
                         bg=self.bg_dark, fg=self.accent_cyan, font=("Segoe UI", 13, "bold"))
        title.pack(side=tk.LEFT)

        self.lbl_model_status = tk.Label(header, text="⏳ Loading AI Models into GPU...",
                                         bg=self.bg_dark, fg="#ffb300", font=("Segoe UI", 9, "bold"))
        self.lbl_model_status.pack(side=tk.RIGHT)

        # ── Main Body (Split into Left Sidebar + Video Canvas) ──
        body = tk.Frame(self, bg=self.bg_dark)
        body.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # Left Sidebar (Video Selector & Controls)
        sidebar = tk.Frame(body, bg=self.bg_panel, width=360)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)

        # Sidebar Title
        lbl_vids = tk.Label(sidebar, text="SELECT VIDEO TO TEST", bg=self.bg_panel,
                            fg=self.text_main, font=("Segoe UI", 10, "bold"))
        lbl_vids.pack(anchor="w", padx=12, pady=(12, 4))

        # Video Listbox with Scrollbar
        list_frame = tk.Frame(sidebar, bg=self.bg_panel)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.video_listbox = tk.Listbox(
            list_frame, bg="#0d0f14", fg=self.text_main,
            selectbackground="#005577", selectforeground="#ffffff",
            font=("Segoe UI", 9), activestyle="none",
            highlightthickness=1, highlightbackground="#333842",
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.video_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.video_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.video_listbox.bind("<<ListboxSelect>>", self._on_video_selected_from_list)

        # Browse Custom File Button
        btn_browse = tk.Button(sidebar, text="📂 Browse Custom Video File...", bg=self.bg_card,
                               fg=self.text_main, activebackground="#2c3240", activeforeground="#ffffff",
                               relief=tk.FLAT, font=("Segoe UI", 9), command=self._browse_custom_video)
        btn_browse.pack(fill=tk.X, padx=12, pady=(0, 10))

        # Selected File Indicator
        self.lbl_selected = tk.Label(sidebar, text="Selected: None", bg=self.bg_panel,
                                     fg=self.text_dim, font=("Segoe UI", 8), wraplength=330, justify="left")
        self.lbl_selected.pack(anchor="w", padx=12, pady=(0, 10))

        # Control Buttons
        ctrl_frame = tk.Frame(sidebar, bg=self.bg_panel)
        ctrl_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        self.btn_play = tk.Button(ctrl_frame, text="▶ Start Detection", bg="#00897b", fg="#ffffff",
                                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                                  command=self.start_detection)
        self.btn_play.pack(fill=tk.X, pady=3)

        row2 = tk.Frame(ctrl_frame, bg=self.bg_panel)
        row2.pack(fill=tk.X, pady=3)

        self.btn_pause = tk.Button(row2, text="⏸ Pause", bg=self.bg_card, fg=self.text_main,
                                   font=("Segoe UI", 9, "bold"), relief=tk.FLAT, width=15,
                                   state=tk.DISABLED, command=self.toggle_pause)
        self.btn_pause.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))

        self.btn_stop = tk.Button(row2, text="⏹ Stop", bg="#c62828", fg="#ffffff",
                                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, width=15,
                                  state=tk.DISABLED, command=self.stop_detection)
        self.btn_stop.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(3, 0))

        # Loop checkbox
        self.loop_var = tk.BooleanVar(value=True)
        chk_loop = tk.Checkbutton(sidebar, text="🔁 Loop playback continuously", variable=self.loop_var,
                                  bg=self.bg_panel, fg=self.text_main, selectcolor="#0d0f14",
                                  activebackground=self.bg_panel, font=("Segoe UI", 9))
        chk_loop.pack(anchor="w", padx=12, pady=(0, 10))

        # Alert Feed Box
        lbl_alerts_title = tk.Label(sidebar, text="LIVE EVENT ALERTS", bg=self.bg_panel,
                                    fg=self.accent_cyan, font=("Segoe UI", 9, "bold"))
        lbl_alerts_title.pack(anchor="w", padx=12, pady=(5, 2))

        self.alert_text = tk.Text(sidebar, bg="#0d0f14", fg="#ff5252", height=8,
                                  font=("Consolas", 8), highlightthickness=1,
                                  highlightbackground="#333842", relief=tk.FLAT)
        self.alert_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # ── Right Main Area (Video Screen + Telemetry) ───────────
        right_panel = tk.Frame(body, bg=self.bg_dark)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Video Canvas
        self.canvas_frame = tk.Frame(right_panel, bg="#000000", highlightthickness=1, highlightbackground="#2a2d36")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.video_canvas = tk.Label(self.canvas_frame, bg="#000000", text="Select a video and click '▶ Start Detection'")
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        # ── Bottom Telemetry Bar ─────────────────────────────────
        bottom_bar = tk.Frame(self, bg=self.bg_panel, height=35)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=(5, 10))

        self.lbl_telemetry_left = tk.Label(bottom_bar, text="Status: Ready | Presentation: 0 FPS | Primary AI: 0ms",
                                           bg=self.bg_panel, fg=self.text_main, font=("Segoe UI", 9))
        self.lbl_telemetry_left.pack(side=tk.LEFT, padx=10, pady=5)

        self.lbl_telemetry_right = tk.Label(bottom_bar, text="Device: GPU (Quadro T1000) | Mode: Asynchronous Decoupled",
                                            bg=self.bg_panel, fg=self.accent_green, font=("Segoe UI", 9))
        self.lbl_telemetry_right.pack(side=tk.RIGHT, padx=10, pady=5)

    def _populate_video_list(self):
        """Scans D:\\testing videos and prototype\\test_videos and lists all videos."""
        self.video_dict = {}  # display_name -> full_path

        paths_to_scan = [
            Path(r"D:\testing videos"),
            PROTOTYPE_DIR / "test_videos",
        ]

        for folder in paths_to_scan:
            if folder.exists():
                for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv"):
                    for file_path in folder.glob(ext):
                        try:
                            clean_name = f"[{folder.name}] {file_path.name}"
                            self.video_dict[clean_name] = str(file_path.resolve())
                        except Exception:
                            pass

        self.video_listbox.delete(0, tk.END)
        for name in sorted(self.video_dict.keys()):
            self.video_listbox.insert(tk.END, name)

        # Default select WLNE fire if present
        for i, name in enumerate(sorted(self.video_dict.keys())):
            if "wlne" in name.lower() or "fire" in name.lower():
                self.video_listbox.selection_set(i)
                self.current_video_path = self.video_dict[name]
                self.lbl_selected.config(text=f"Selected: {name}")
                break

    def _on_video_selected_from_list(self, event):
        sel = self.video_listbox.curselection()
        if not sel:
            return
        name = self.video_listbox.get(sel[0])
        full_path = self.video_dict.get(name)
        if full_path:
            self.current_video_path = full_path
            self.lbl_selected.config(text=f"Selected: {name}")

            # If already running, switch video automatically
            if self.is_running:
                self.start_detection()

    def _browse_custom_video(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv *.wmv"), ("All Files", "*.*")]
        )
        if file_path:
            name = f"[Custom] {Path(file_path).name}"
            self.video_dict[name] = file_path
            self.video_listbox.insert(0, name)
            self.video_listbox.selection_clear(0, tk.END)
            self.video_listbox.selection_set(0)
            self.current_video_path = file_path
            self.lbl_selected.config(text=f"Selected: {name}")

            if self.is_running:
                self.start_detection()

    def _start_model_loader(self):
        """Loads AI models in a background thread so the GUI does not freeze on startup."""
        def _loader():
            try:
                self.pipeline = AIPipeline(async_mode=True)
                self.pipeline.load_models()
                self.engine = EventEngine()
                self.lbl_model_status.config(text="✅ AI Models Ready (Async GPU)", fg=self.accent_green)
            except Exception as e:
                self.lbl_model_status.config(text=f"❌ Load Error: {e}", fg=self.accent_red)

        threading.Thread(target=_loader, daemon=True, name="ModelLoader").start()

    def start_detection(self):
        """Starts or restarts detection on the currently selected video."""
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            messagebox.showwarning("No Video Selected", "Please select a valid video from the list or browse for one.")
            return

        if self.pipeline is None:
            messagebox.showinfo("Please Wait", "AI Models are still loading into the GPU. Please wait a few seconds...")
            return

        # Stop existing run cleanly
        self.stop_detection()
        time.sleep(0.1)

        self.is_running = True
        self.is_paused = False

        self.btn_play.config(text="🔄 Restart Video", bg="#00897b")
        self.btn_pause.config(state=tk.NORMAL, text="⏸ Pause")
        self.btn_stop.config(state=tk.NORMAL)

        # Clear alerts
        self.alert_text.delete(1.0, tk.END)

        # Start worker thread for video decoding and processing
        self.worker_thread = threading.Thread(target=self._video_processing_worker,
                                              args=(self.current_video_path,),
                                              daemon=True, name="VideoWorker")
        self.worker_thread.start()

    def toggle_pause(self):
        """Pauses or resumes video playback."""
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.config(text="▶ Resume", bg=self.accent_green, fg="#000000")
        else:
            self.btn_pause.config(text="⏸ Pause", bg=self.bg_card, fg=self.text_main)

    def stop_detection(self):
        """Stops video playback and inference cleanly."""
        self.is_running = False
        self.is_paused = False

        self.btn_play.config(text="▶ Start Detection", bg="#00897b")
        self.btn_pause.config(state=tk.DISABLED, text="⏸ Pause", bg=self.bg_card, fg=self.text_main)
        self.btn_stop.config(state=tk.DISABLED)

        if self.video_cap:
            try:
                self.video_cap.release()
            except Exception:
                pass
            self.video_cap = None

        if self.pipeline:
            self.pipeline.reset()

        self.lbl_telemetry_left.config(text="Status: Stopped")

    def _video_processing_worker(self, video_path: str):
        """
        Decoupled real-time video player:
        1. Presentation runs strictly on a wall-clock timer (1.0x real video speed).
           A 19-second video will play in exactly 19 seconds — zero slow motion!
        2. AI inference processes frames non-blockingly, updating cached detections and tracks.
        """
        cap = cv2.VideoCapture(video_path)
        self.video_cap = cap
        if not cap.isOpened():
            return

        self.source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = 1.0 / self.source_fps

        # Start at frame 450 for WLNE fire if long video, else 0
        start_frame = 450 if ("wlne" in Path(video_path).name.lower() and self.total_frames > 500) else 0
        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # Threading for non-blocking AI
        ai_input_queue = queue.Queue(maxsize=1)
        latest_analysis_lock = threading.Lock()
        latest_analysis = [None]
        ai_active = [True]

        def _ai_worker():
            """Runs AI inference on latest frames without blocking video presentation."""
            while ai_active[0] and self.is_running:
                try:
                    ai_frame = ai_input_queue.get(timeout=0.05)
                except queue.Empty:
                    continue

                try:
                    analysis = self.pipeline.process_frame(ai_frame)
                    if analysis and self.engine:
                        new_alerts = self.engine.process(analysis)
                        for a in new_alerts:
                            self.alert_queue.put(a)

                    with latest_analysis_lock:
                        latest_analysis[0] = analysis
                except Exception as err:
                    pass

        ai_thread = threading.Thread(target=_ai_worker, daemon=True, name="AppAIWorker")
        ai_thread.start()

        # Wall-clock presentation pacing loop
        t_wall_start = time.time()
        paused_duration = 0.0
        pause_start = 0.0

        try:
            while self.is_running and cap.isOpened():
                if self.is_paused:
                    if pause_start == 0.0:
                        pause_start = time.time()
                    time.sleep(0.03)
                    continue
                elif pause_start > 0.0:
                    paused_duration += (time.time() - pause_start)
                    pause_start = 0.0

                # Compute target frame based on real elapsed wall time
                now = time.time()
                elapsed_real_sec = (now - t_wall_start) - paused_duration
                target_frame = start_frame + int(elapsed_real_sec * self.source_fps)

                if target_frame >= self.total_frames:
                    if self.loop_var.get():
                        t_wall_start = time.time()
                        paused_duration = 0.0
                        pause_start = 0.0
                        start_frame = 450 if ("wlne" in Path(video_path).name.lower() and self.total_frames > 500) else 0
                        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                        continue
                    else:
                        break

                current_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                frames_behind = target_frame - current_pos

                # Fast forward if AI or decoding lagged behind real-time clock
                if frames_behind > 1:
                    # Skip grab frames to catch up instantly
                    for _ in range(min(frames_behind - 1, 10)):
                        cap.grab()

                ret, frame = cap.read()
                if not ret:
                    if self.loop_var.get():
                        t_wall_start = time.time()
                        paused_duration = 0.0
                        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                        continue
                    else:
                        break

                # Submit frame to AI worker if ready (drop-oldest, non-blocking)
                if ai_input_queue.empty():
                    ai_input_queue.put(frame.copy())

                # Get latest available analysis
                with latest_analysis_lock:
                    analysis = latest_analysis[0]

                active_alerts = self.engine.get_active_alerts() if self.engine else []

                # Render display overlay with current frame
                rendered = self.display_renderer.render(frame, analysis, active_alerts, Path(video_path).name)

                # Send rendered frame to GUI presentation queue
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_queue.put((rendered, analysis))

                # Sleep precise remainder of frame interval to hit exact native FPS
                render_elapsed = time.time() - now
                time_to_sleep = frame_interval - render_elapsed
                if time_to_sleep > 0.001:
                    time.sleep(time_to_sleep)

        finally:
            ai_active[0] = False
            cap.release()

    def _gui_update_loop(self):
        """Runs on Tkinter main thread every 20ms to display frames and update HUD."""
        # 1. Check for new video frames to render
        try:
            rendered, analysis = self.frame_queue.get_nowait()
            if rendered is not None:
                # Resize frame to fit canvas
                canvas_w = self.video_canvas.winfo_width()
                canvas_h = self.video_canvas.winfo_height()
                if canvas_w > 100 and canvas_h > 100:
                    h, w = rendered.shape[:2]
                    scale = min(canvas_w / w, canvas_h / h)
                    nw, nh = int(w * scale), int(h * scale)
                    resized = cv2.resize(rendered, (nw, nh))

                    # Convert BGR (OpenCV) to RGB (Tkinter / PIL)
                    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(rgb)
                    imgtk = ImageTk.PhotoImage(image=img)

                    self.video_canvas.imgtk = imgtk
                    self.video_canvas.config(image=imgtk, text="")

                # Update Telemetry Bar
                if analysis:
                    ai_ms = int(analysis.processing_time_ms)
                    telemetry = analysis.specialist_telemetry
                    fire_fps = telemetry.get("fire", {}).get("fps", 0)
                    fire_age = int(telemetry.get("fire", {}).get("age_ms", 0))
                    state_text = "PAUSED" if self.is_paused else "PLAYING"
                    self.lbl_telemetry_left.config(
                        text=f"[{state_text}] Frame: #{analysis.frame_number} | Presentation: ~30 FPS | Primary AI: {ai_ms}ms | Specialists: Fire {fire_fps} FPS ({fire_age}ms)"
                    )
        except queue.Empty:
            pass

        # 2. Check for alerts to print into Alert Box
        while not self.alert_queue.empty():
            try:
                alert: EventAlert = self.alert_queue.get_nowait()
                emoji = EVENT_EMOJI.get(alert.event_type, "⚠️")
                timestamp = time.strftime("%H:%M:%S")
                msg = f"[{timestamp}] {emoji} {alert.event_type.upper()} ({alert.risk_score}% {alert.risk_level})\n  -> Action: {alert.action} | {alert.department}\n\n"
                self.alert_text.insert(tk.END, msg)
                self.alert_text.see(tk.END)
            except queue.Empty:
                break

        # Schedule next tick
        self.after(15, self._gui_update_loop)

    def on_close(self):
        """Cleanup on window close."""
        self.stop_detection()
        if self.pipeline:
            self.pipeline.stop()
        self.destroy()


def main():
    app = VisionGuardStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
