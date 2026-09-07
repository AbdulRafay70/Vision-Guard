"""
VisionGuard — Asynchronous Decoupled Pipeline Benchmark
Measures performance of the decoupled architecture (30 FPS presentation + async specialists)
and saves async.json for direct comparison against baseline.json.
"""
import time
import json
import logging
import cv2
import torch
from pathlib import Path

import config
from ai.pipeline import AIPipeline
from events.engine import EventEngine
from output.display import DisplayRenderer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_async_benchmark():
    video_path = r"D:\testing videos\Security Camera Video of Fire at WLNE.mp4"
    if not Path(video_path).exists():
        video_path = str(config.TEST_VIDEOS_DIR / "4116863-hd_1920_1080_30fps.mp4")

    print(f"\n[BENCHMARK-ASYNC] Video: {video_path}", flush=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {video_path}", flush=True)
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    source_fps = round(cap.get(cv2.CAP_PROP_FPS), 2)
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    window_title = "VisionGuard - Phase 1 Asynchronous (~30 FPS Presentation)"
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_title, config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)

    # Show immediate splash frame while loading
    start_frame = 450 if total_video_frames > 500 else 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    ret, splash_frame = cap.read()
    if ret:
        splash_display = cv2.resize(splash_frame, (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))
        cv2.putText(splash_display, "Loading Async AI Pipeline into GPU... Please wait", (40, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)
        cv2.imshow(window_title, splash_display)
        cv2.waitKey(100)

    print("[BENCHMARK-ASYNC] Loading AI Models...", flush=True)
    pipeline = AIPipeline(async_mode=True)
    pipeline.load_models()
    engine = EventEngine()
    display = DisplayRenderer()

    # Reset position after load
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    num_frames = min(300, total_video_frames - start_frame)

    # Prepare output video writer
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    out_video_path = output_dir / "async_fire_output.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(str(out_video_path), fourcc, 30.0,
                                 (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))

    primary_latencies = []
    presentation_times = []
    dropped_presentation_frames = 0
    target_frame_time = 1.0 / 30.0  # 33.33ms

    t_benchmark_start = time.time()
    frames_processed = 0

    print(f"\n[DISPLAY] Playing frames {start_frame} to {start_frame + num_frames} ({num_frames} frames)...", flush=True)
    print(f"[RECORDER] Saving annotated output to: {out_video_path.resolve()}", flush=True)
    try:
        for i in range(num_frames):
            if (i + 1) % 25 == 0 or i == 0:
                print(f"  [Frame {i+1:>3d}/{num_frames}] Running async presentation...", flush=True)

            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            # Fast non-blocking primary path + async specialist worker
            analysis = pipeline.process_frame(frame)
            primary_latencies.append(analysis.processing_time_ms if analysis else 0.0)

            active_alerts = []
            if analysis:
                engine.process(analysis)
                active_alerts = engine.get_active_alerts()

            # Render display
            display_frame = display.render(frame, analysis, active_alerts, Path(video_path).name)
            display_frame = cv2.resize(display_frame, (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))

            # Write to output video file
            out_writer.write(display_frame)

            # Show window (for interactive terminals)
            cv2.imshow(window_title, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("\n[USER] Stopped early via 'Q'.")
                break

            t_end = time.time()
            frame_time = t_end - t0
            presentation_times.append(frame_time)
            if frame_time > target_frame_time:
                dropped_presentation_frames += max(0, int((frame_time - target_frame_time) / target_frame_time))
            frames_processed += 1

    finally:
        pipeline.stop()
        if 'out_writer' in locals() and out_writer is not None:
            out_writer.release()
        cap.release()
        cv2.destroyAllWindows()

    total_wall_time = time.time() - t_benchmark_start
    display_fps = round(frames_processed / total_wall_time, 2) if total_wall_time > 0 else 0
    avg_primary_latency = round(sum(primary_latencies) / len(primary_latencies), 2) if primary_latencies else 0

    vram_mb = 0.0
    if torch.cuda.is_available():
        vram_mb = round(torch.cuda.max_memory_allocated(0) / (1024 ** 2), 1)

    telemetry = pipeline.specialist_worker.get_telemetry()

    benchmark_data = {
        "benchmark": "phase1_async_decoupled",
        "video": Path(video_path).name,
        "resolution": f"{width}x{height}",
        "source_fps": source_fps,
        "frames_tested": frames_processed,
        "total_wall_time_sec": round(total_wall_time, 2),
        "display_fps": display_fps,
        "primary_detector_latency_ms": avg_primary_latency,
        "dropped_presentation_frames": dropped_presentation_frames,
        "specialist_telemetry": telemetry,
        "peak_vram_mb": vram_mb,
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "notes": "Decoupled asynchronous pipeline: primary YOLOv8s presentation thread + single serialized GPU specialist worker"
    }

    out_file = Path("async.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print("\n" + "=" * 50)
    print("  PHASE 1 ASYNC BENCHMARK COMPLETE")
    print("=" * 50)
    print(f"  Display FPS (Presentation): {display_fps} FPS")
    print(f"  Primary Latency:            {avg_primary_latency} ms")
    print(f"  Dropped Frames:             {dropped_presentation_frames}")
    print(f"  Specialist Worker Stats:    {telemetry}")
    print(f"  Peak VRAM:                  {vram_mb} MB")
    print(f"  Saved to:                   {out_file.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    run_async_benchmark()
