import sys
import time
import os
import cv2
import torch
import numpy as np
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add prototype directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from ai.pipeline import AIPipeline
from events.engine import EventEngine
from output.display import DisplayRenderer

def main():
    video_path = r"D:\testing videos\Security Camera Video of Fire at WLNE.mp4"
    if len(sys.argv) > 1:
        video_path = sys.argv[1]

    if not Path(video_path).exists():
        video_path = str(config.TEST_VIDEOS_DIR / "4116863-hd_1920_1080_30fps.mp4")

    print(f"\n{'=' * 60}", flush=True)
    print(f"  VISIONGUARD DESKTOP UI PLAYER", flush=True)
    print(f"  Video: {video_path}", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {video_path}", flush=True)
        return

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start_frame = 450 if total_frames > 500 else 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    window_title = "VisionGuard AI — Live Detection Player"
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_title, config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)

    # Bring window to front
    try:
        cv2.setWindowProperty(window_title, cv2.WND_PROP_TOPMOST, 1)
        cv2.setWindowProperty(window_title, cv2.WND_PROP_TOPMOST, 0)
    except Exception:
        pass

    # Splash screen while loading
    ret, splash = cap.read()
    if ret:
        splash_disp = cv2.resize(splash, (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))
        cv2.putText(splash_disp, "Starting VisionGuard AI Pipeline...", (50, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        cv2.imshow(window_title, splash_disp)
        cv2.waitKey(50)

    print("[PLAYER] Initializing Asynchronous AI Pipeline...", flush=True)
    pipeline = AIPipeline(async_mode=True)
    pipeline.load_models()
    engine = EventEngine()
    display = DisplayRenderer()

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frame_interval = 1.0 / source_fps

    print(f"\n[PLAYER] Playing live from frame {start_frame} at {source_fps:.1f} FPS (1.0x Real Time).")
    print("  Controls: Q=Quit | P=Pause | Space=Step frame\n", flush=True)

    # Threading for non-blocking AI
    import queue
    import threading
    ai_input_queue = queue.Queue(maxsize=1)
    latest_analysis_lock = threading.Lock()
    latest_analysis = [None]
    ai_active = [True]

    def _ai_worker():
        while ai_active[0]:
            try:
                ai_frame = ai_input_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                analysis = pipeline.process_frame(ai_frame)
                if analysis:
                    engine.process(analysis)
                with latest_analysis_lock:
                    latest_analysis[0] = analysis
            except Exception:
                pass

    ai_thread = threading.Thread(target=_ai_worker, daemon=True, name="PlayerAIWorker")
    ai_thread.start()

    paused = False
    t_wall_start = time.time()
    paused_duration = 0.0
    pause_start = 0.0

    try:
        while cap.isOpened():
            now = time.time()
            if paused:
                if pause_start == 0.0:
                    pause_start = now
                time.sleep(0.03)
            else:
                if pause_start > 0.0:
                    paused_duration += (now - pause_start)
                    pause_start = 0.0

                elapsed_real_sec = (now - t_wall_start) - paused_duration
                target_frame = start_frame + int(elapsed_real_sec * source_fps)

                if target_frame >= total_frames:
                    t_wall_start = time.time()
                    paused_duration = 0.0
                    start_frame = 450 if ("wlne" in Path(video_path).name.lower() and total_frames > 500) else 0
                    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                    continue

                curr_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                frames_behind = target_frame - curr_pos
                if frames_behind > 1:
                    for _ in range(min(frames_behind - 1, 10)):
                        cap.grab()

                ret, frame = cap.read()
                if not ret:
                    t_wall_start = time.time()
                    paused_duration = 0.0
                    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                    continue

                # Submit frame to AI worker if ready
                if ai_input_queue.empty():
                    ai_input_queue.put(frame.copy())

                # Get latest available AI analysis
                with latest_analysis_lock:
                    analysis = latest_analysis[0]

                active_alerts = engine.get_active_alerts() if analysis else []

                display_frame = display.render(frame, analysis, active_alerts, Path(video_path).name)
                display_frame = cv2.resize(display_frame, (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))
                cv2.imshow(window_title, display_frame)

                render_elapsed = time.time() - now
                time_to_sleep = frame_interval - render_elapsed
                if time_to_sleep > 0.001:
                    time.sleep(time_to_sleep)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('p') or key == ord('P'):
                paused = not paused
            elif key == ord(' ') and paused:
                ret, frame = cap.read()
                if ret:
                    analysis = pipeline.process_frame(frame)
                    active_alerts = engine.get_active_alerts() if analysis else []
                    display_frame = display.render(frame, analysis, active_alerts, Path(video_path).name)
                    display_frame = cv2.resize(display_frame, (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))
                    cv2.imshow(window_title, display_frame)

    except KeyboardInterrupt:
        print("\n[PLAYER] Stopped by user (Ctrl+C).", flush=True)
    finally:
        ai_active[0] = False
        pipeline.stop()
        cap.release()
        cv2.destroyAllWindows()
        print("[PLAYER] Playback finished cleanly.\n", flush=True)

if __name__ == "__main__":
    main()
