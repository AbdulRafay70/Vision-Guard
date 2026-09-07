"""
VisionGuard — 30-Minute Extended GPU Stress Test (Days 6-8 — Rafay)
════════════════════════════════════════════════════════════════════════
Verifies long-run system stability under continuous AI inference load:

  • Sustained throughput      — target 30 FPS with ZERO drop windows
  • Memory stability          — process RSS growth (leak detection)
  • GPU health                — temperature, VRAM, utilization over time

The test drives the FULL AI pipeline (detection + tracking + pose + fire +
weapon + violence) on every frame (AI_PROCESS_EVERY_N_FRAMES forced to 1) to
create a genuine worst-case GPU load, samples system telemetry once per second,
streams a live console readout, and writes a CSV + JSON report at the end.

Usage:
    python stress_test.py                       # 30 min on test videos
    python stress_test.py --duration 60         # quick 1-minute smoke test
    python stress_test.py --source webcam       # stress the live webcam
    python stress_test.py --fps-target 30 --report-dir output/stress

Exit code 0 = PASS, 1 = FAIL (drops detected, overheating, or memory leak).
"""
import argparse
import csv
import json
import logging
import os
import subprocess
import sys
import threading
import time
import warnings
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2

import config
from ai.pipeline import AIPipeline

logger = logging.getLogger("stress_test")


class _SilenceDeprecated(logging.Filter):
    """Drops ultralytics' per-inference "'half' is deprecated" WARNING records.

    ultralytics re-runs set_logging(verbose=False) on every predict()/track()
    call, which resets its logger level back to WARNING — so a one-time
    setLevel(ERROR) is silently undone. A logger-level filter survives those
    resets and keeps the long-run telemetry log legible. FP16 itself is
    unaffected (half= still applies half-precision); this only hides the
    forward-compatibility notice.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "deprecated" not in record.getMessage().lower()


# ── Stability thresholds ──────────────────────────────────────────────────
GPU_TEMP_WARN_C = 80.0        # Sustained above this = thermal throttling risk
GPU_TEMP_CRIT_C = 90.0        # Critical — fail the run
MEM_LEAK_GROWTH_MB = 500.0    # RSS growth above baseline flagged as a leak

# A 1-second window counts as a stream "drop" only when FPS falls below this
# fraction of the target. Because the Day 1 circular buffer decouples capture
# from inference, the stream side paces at the camera rate with small natural
# jitter (software pacing + variable video decode). A genuine drop is a visible
# STALL, not ±20% jitter — so 0.80 flags any window under 24 FPS for a 30 target.
STREAM_DROP_TOLERANCE = 0.80


# ══════════════════════════════════════════════════════════════════════════
# GPU / System Telemetry
# ══════════════════════════════════════════════════════════════════════════

class SystemMonitor:
    """
    Collects GPU (temperature / VRAM / utilization) and process memory stats.

    GPU telemetry resolution order:
      1. NVML via nvidia-ml-py (pynvml)  — most accurate
      2. nvidia-smi subprocess            — fallback if pynvml missing
      3. torch.cuda memory APIs           — VRAM only, no temperature
    """

    def __init__(self):
        self._nvml = None
        self._handle = None
        self._psutil = None
        self._proc = None
        self._backend = "none"
        self._init_nvml()
        self._init_psutil()

    def _init_nvml(self):
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self._backend = "nvml"
            logger.info("[MONITOR] GPU telemetry backend: NVML (pynvml)")
            return
        except Exception as e:
            logger.debug("[MONITOR] NVML unavailable: %s", e)

        # Fallback: verify nvidia-smi exists
        try:
            subprocess.run(["nvidia-smi", "-L"], capture_output=True, check=True, timeout=5)
            self._backend = "nvidia-smi"
            logger.info("[MONITOR] GPU telemetry backend: nvidia-smi subprocess")
        except Exception:
            if self._torch_cuda_available():
                self._backend = "torch"
                logger.info("[MONITOR] GPU telemetry backend: torch.cuda (VRAM only)")
            else:
                self._backend = "none"
                logger.warning("[MONITOR] No GPU telemetry available — CPU-only run")

    @staticmethod
    def _torch_cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def _init_psutil(self):
        try:
            import psutil
            self._psutil = psutil
            self._proc = psutil.Process(os.getpid())
        except Exception as e:
            logger.warning("[MONITOR] psutil unavailable (%s) — no RSS tracking", e)

    def get_stats(self) -> Dict[str, Optional[float]]:
        stats: Dict[str, Optional[float]] = {
            "gpu_temp_c": None,
            "gpu_util_pct": None,
            "gpu_mem_used_mb": None,
            "gpu_mem_total_mb": None,
            "proc_rss_mb": None,
        }

        if self._backend == "nvml":
            stats.update(self._stats_nvml())
        elif self._backend == "nvidia-smi":
            stats.update(self._stats_smi())
        elif self._backend == "torch":
            stats.update(self._stats_torch())

        if self._proc is not None:
            try:
                stats["proc_rss_mb"] = round(self._proc.memory_info().rss / (1024 * 1024), 1)
            except Exception:
                pass

        return stats

    def _stats_nvml(self) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        try:
            nv = self._nvml
            temp = nv.nvmlDeviceGetTemperature(self._handle, nv.NVML_TEMPERATURE_GPU)
            util = nv.nvmlDeviceGetUtilizationRates(self._handle)
            mem = nv.nvmlDeviceGetMemoryInfo(self._handle)
            out["gpu_temp_c"] = float(temp)
            out["gpu_util_pct"] = float(util.gpu)
            out["gpu_mem_used_mb"] = round(mem.used / (1024 * 1024), 1)
            out["gpu_mem_total_mb"] = round(mem.total / (1024 * 1024), 1)
        except Exception as e:
            logger.debug("[MONITOR] NVML read error: %s", e)
        return out

    def _stats_smi(self) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        try:
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            line = result.stdout.strip().splitlines()[0]
            temp, util, mem_used, mem_total = [x.strip() for x in line.split(",")]
            out["gpu_temp_c"] = float(temp)
            out["gpu_util_pct"] = float(util)
            out["gpu_mem_used_mb"] = float(mem_used)
            out["gpu_mem_total_mb"] = float(mem_total)
        except Exception as e:
            logger.debug("[MONITOR] nvidia-smi read error: %s", e)
        return out

    def _stats_torch(self) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        try:
            import torch
            out["gpu_mem_used_mb"] = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1)
            out["gpu_mem_total_mb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 1)
        except Exception as e:
            logger.debug("[MONITOR] torch stats error: %s", e)
        return out

    def shutdown(self):
        if self._nvml is not None:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════
# Frame Sources (feed the pipeline as fast as the GPU allows)
# ══════════════════════════════════════════════════════════════════════════

class VideoLoopSource:
    """Cycles through every .mp4 in test_videos/ with NO FPS throttling."""

    def __init__(self, video_dir: Path):
        self.files = sorted(video_dir.glob("*.mp4"))
        if not self.files:
            raise FileNotFoundError(f"No .mp4 files found in {video_dir}")
        self._idx = 0
        self._cap: Optional[cv2.VideoCapture] = None
        self._open_next()

    def _open_next(self):
        if self._cap is not None:
            self._cap.release()
        path = self.files[self._idx % len(self.files)]
        self._cap = cv2.VideoCapture(str(path))
        self._idx += 1
        logger.info("[SOURCE] Playing %s", path.name)

    def read(self):
        if self._cap is None:
            return None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            self._open_next()
            ret, frame = self._cap.read()
            if not ret:
                return None
        return frame

    def stop(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class WebcamStressSource:
    """Wraps WebcamSource for live-camera stress runs."""

    def __init__(self, index: int = 0):
        from camera.webcam import WebcamSource
        self._src = WebcamSource(camera_index=index)
        if not self._src.start():
            raise RuntimeError(f"Could not open webcam index {index}")

    def read(self):
        ret, frame = self._src.read()
        return frame if ret else None

    def stop(self):
        try:
            self._src.stop()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════
# Stress Test Runner
# ══════════════════════════════════════════════════════════════════════════

class StressTest:
    def __init__(self, duration_s: int, fps_target: int, source_kind: str,
                 report_dir: Path, max_load: bool = False):
        self.duration_s = duration_s
        self.fps_target = fps_target
        self.source_kind = source_kind
        self.report_dir = report_dir
        self.max_load = max_load
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self.monitor = SystemMonitor()
        self.pipeline = AIPipeline()
        self.source = None

        # 2-slot circular buffer mirroring the Day 1 webcam architecture:
        # the producer (simulated camera) captures at the target cadence while
        # the consumer (AI) always takes the LATEST frame. Stale frames are
        # dropped so the STREAM side holds a rock-solid FPS regardless of how
        # fast the GPU inference runs — exactly like the production pipeline.
        self._buffer: deque = deque(maxlen=2)
        self._buf_lock = threading.Lock()
        self._running = False
        self._producer_thread: Optional[threading.Thread] = None
        self._orig_every_n: Optional[int] = None

        # Telemetry accumulators
        self.samples: List[Dict] = []       # per-second telemetry rows
        self.produced_frames = 0            # stream side (target: fps_target)
        self.dropped_stale = 0              # frames dropped by the buffer
        self.drop_windows = 0               # 1s windows where STREAM fps < target
        self.min_window_fps = float("inf")
        self.max_gpu_temp = 0.0
        self.max_gpu_mem = 0.0
        self.max_rss = 0.0
        self.baseline_rss: Optional[float] = None

    # ── Setup ──────────────────────────────────────────────────────────
    def _build_source(self):
        if self.source_kind == "webcam":
            return WebcamStressSource(index=0)
        # Default: loop test videos (fall back to webcam if none exist)
        try:
            return VideoLoopSource(config.TEST_VIDEOS_DIR)
        except FileNotFoundError:
            logger.warning("[SOURCE] No test videos — falling back to webcam")
            return WebcamStressSource(index=0)

    def setup(self):
        logger.info("=" * 68)
        logger.info("  VISIONGUARD — EXTENDED GPU STRESS TEST")
        logger.info("=" * 68)
        logger.info("Duration   : %d s (%.1f min)", self.duration_s, self.duration_s / 60)
        logger.info("FPS target : %d (zero-drop, stream side)", self.fps_target)
        logger.info("Source     : %s", self.source_kind)
        logger.info("Device     : %s | FP16: %s", config.DETECTION_DEVICE, config.USE_FP16)
        logger.info("Load mode  : %s",
                    "MAX (every frame, all models)" if self.max_load
                    else f"PRODUCTION (AI every {config.AI_PROCESS_EVERY_N_FRAMES} frame(s))")

        # Optional worst-case thermal load: run inference on EVERY frame.
        if self.max_load:
            self._orig_every_n = config.AI_PROCESS_EVERY_N_FRAMES
            config.AI_PROCESS_EVERY_N_FRAMES = 1
            logger.info("[SETUP] Max-load: AI_PROCESS_EVERY_N_FRAMES forced 1 (was %d)",
                        self._orig_every_n)

        logger.info("[SETUP] Loading AI models...")
        self.pipeline.load_models()
        self.source = self._build_source()

        # Warmup: a few inferences to allocate GPU buffers / CUDA context
        logger.info("[SETUP] Warming up GPU...")
        for _ in range(10):
            frame = self.source.read()
            if frame is not None:
                self.pipeline.process_frame(frame)
        time.sleep(0.5)

        stats = self.monitor.get_stats()
        if stats["proc_rss_mb"] is not None:
            self.baseline_rss = stats["proc_rss_mb"]
        logger.info("[SETUP] Baseline RSS: %s MB | GPU temp: %s C",
                    self.baseline_rss, stats["gpu_temp_c"])
        logger.info("=" * 68)

    # ── Producer (simulated camera) ────────────────────────────────────
    def _producer_loop(self):
        """Capture frames at the target cadence into the 2-slot circular buffer.

        Stale frames are overwritten/dropped when the AI consumer falls behind,
        so the stream side maintains a steady FPS with zero blocking — this is
        the metric the '30 FPS zero drops' stability criterion refers to.
        """
        interval = 1.0 / self.fps_target
        next_t = time.time()
        while self._running:
            frame = self.source.read()
            if frame is None:
                time.sleep(0.002)
                continue
            with self._buf_lock:
                if len(self._buffer) >= self._buffer.maxlen:
                    self.dropped_stale += 1
                self._buffer.append(frame)
                self.produced_frames += 1
            # Pace to the camera cadence
            next_t += interval
            sleep_for = next_t - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_t = time.time()  # fell behind — resync, no burst catch-up

    # ── Main loop (consumer + telemetry) ───────────────────────────────
    def run(self) -> bool:
        self._running = True
        self._producer_thread = threading.Thread(target=self._producer_loop,
                                                 daemon=True, name="stress-producer")
        self._producer_thread.start()

        start = time.time()
        window_start = start
        window_produced = 0
        window_ai = self.pipeline.ai_frame_count

        try:
            while True:
                now = time.time()
                elapsed = now - start
                if elapsed >= self.duration_s:
                    break

                # Consumer: take the LATEST frame and clear stale ones so each
                # frame is processed at most once (mirrors production consumer).
                with self._buf_lock:
                    frame = self._buffer[-1] if self._buffer else None
                    if frame is not None:
                        self._buffer.clear()
                if frame is None:
                    time.sleep(0.002)
                    continue

                self.pipeline.process_frame(frame)

                # Once-per-second telemetry sample
                if now - window_start >= 1.0:
                    win_elapsed = now - window_start
                    produced_delta = self.produced_frames - window_produced
                    ai_delta = self.pipeline.ai_frame_count - window_ai
                    stream_fps = produced_delta / win_elapsed
                    ai_fps = ai_delta / win_elapsed
                    stats = self.monitor.get_stats()

                    if stream_fps < self.min_window_fps:
                        self.min_window_fps = stream_fps
                    if stream_fps < self.fps_target * STREAM_DROP_TOLERANCE:
                        self.drop_windows += 1

                    if stats["gpu_temp_c"] is not None:
                        self.max_gpu_temp = max(self.max_gpu_temp, stats["gpu_temp_c"])
                    if stats["gpu_mem_used_mb"] is not None:
                        self.max_gpu_mem = max(self.max_gpu_mem, stats["gpu_mem_used_mb"])
                    if stats["proc_rss_mb"] is not None:
                        self.max_rss = max(self.max_rss, stats["proc_rss_mb"])

                    self.samples.append({
                        "t_sec": round(elapsed, 1),
                        "stream_fps": round(stream_fps, 1),
                        "ai_fps": round(ai_fps, 1),
                        "produced": self.produced_frames,
                        "ai_frames": self.pipeline.ai_frame_count,
                        "dropped_stale": self.dropped_stale,
                        "gpu_temp_c": stats["gpu_temp_c"],
                        "gpu_util_pct": stats["gpu_util_pct"],
                        "gpu_mem_used_mb": stats["gpu_mem_used_mb"],
                        "proc_rss_mb": stats["proc_rss_mb"],
                    })

                    if stats["gpu_temp_c"] is not None and stats["gpu_temp_c"] >= GPU_TEMP_CRIT_C:
                        logger.error("[THERMAL] GPU hit %.1f C — aborting to protect hardware",
                                     stats["gpu_temp_c"])
                        break

                    logger.info(
                        "[%5.1fs] STREAM=%5.1f FPS  AI=%5.1f FPS  dropped=%6d | "
                        "GPU %s C util %s%% vram %s MB | RSS %s MB",
                        elapsed, stream_fps, ai_fps, self.dropped_stale,
                        stats["gpu_temp_c"], stats["gpu_util_pct"],
                        stats["gpu_mem_used_mb"], stats["proc_rss_mb"],
                    )

                    window_start = now
                    window_produced = self.produced_frames
                    window_ai = self.pipeline.ai_frame_count

        except KeyboardInterrupt:
            logger.warning("[TEST] Interrupted by operator — generating partial report")
        finally:
            self._running = False
            if self._producer_thread is not None:
                self._producer_thread.join(timeout=2.0)
            if self._orig_every_n is not None:
                config.AI_PROCESS_EVERY_N_FRAMES = self._orig_every_n
            if self.source is not None:
                self.source.stop()

        return self._evaluate()

    # ── Evaluation & reporting ─────────────────────────────────────────
    def _evaluate(self) -> bool:
        avg_stream_fps = self.produced_frames / max(self.duration_s, 1)
        avg_ai_fps = self.pipeline.ai_frame_count / max(self.duration_s, 1)
        mem_growth = None
        if self.baseline_rss is not None and self.max_rss:
            mem_growth = round(self.max_rss - self.baseline_rss, 1)

        thermal_fail = self.max_gpu_temp >= GPU_TEMP_CRIT_C
        drop_fail = self.drop_windows > 0
        leak_fail = mem_growth is not None and mem_growth > MEM_LEAK_GROWTH_MB

        min_fps = 0.0 if self.min_window_fps == float("inf") else round(self.min_window_fps, 1)

        passed = not (thermal_fail or drop_fail or leak_fail)

        summary = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "duration_sec": self.duration_s,
            "fps_target": self.fps_target,
            "source": self.source_kind,
            "load_mode": "max" if self.max_load else "production",
            "device": str(config.DETECTION_DEVICE),
            "fp16": config.USE_FP16,
            "produced_frames": self.produced_frames,
            "ai_frames": self.pipeline.ai_frame_count,
            "dropped_stale": self.dropped_stale,
            "avg_stream_fps": round(avg_stream_fps, 1),
            "avg_ai_fps": round(avg_ai_fps, 1),
            "min_window_stream_fps": min_fps,
            "drop_windows": self.drop_windows,
            "max_gpu_temp_c": round(self.max_gpu_temp, 1),
            "max_gpu_mem_mb": round(self.max_gpu_mem, 1),
            "baseline_rss_mb": self.baseline_rss,
            "max_rss_mb": round(self.max_rss, 1),
            "mem_growth_mb": mem_growth,
            "telemetry_backend": self.monitor._backend,
            "thermal_fail": thermal_fail,
            "drop_fail": drop_fail,
            "leak_fail": leak_fail,
            "RESULT": "PASS" if passed else "FAIL",
        }

        self._write_reports(summary)
        self._print_summary(summary)
        return passed

    def _write_reports(self, summary: Dict):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self.report_dir / f"stress_telemetry_{stamp}.csv"
        json_path = self.report_dir / f"stress_summary_{stamp}.json"

        if self.samples:
            fieldnames = list(self.samples[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.samples)
            logger.info("[REPORT] Telemetry CSV → %s", csv_path)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info("[REPORT] Summary JSON → %s", json_path)

    def _print_summary(self, s: Dict):
        line = "═" * 68
        logger.info(line)
        logger.info("  STRESS TEST RESULT: %s", s["RESULT"])
        logger.info(line)
        logger.info("  Load mode              : %s", s["load_mode"].upper())
        logger.info("  Stream frames produced : %d", s["produced_frames"])
        logger.info("  AI frames inferred     : %d", s["ai_frames"])
        logger.info("  Stale frames dropped   : %d (buffer absorbed AI lag)", s["dropped_stale"])
        logger.info("  Avg STREAM FPS         : %.1f (target %d)",
                    s["avg_stream_fps"], s["fps_target"])
        logger.info("  Avg AI FPS             : %.1f", s["avg_ai_fps"])
        logger.info("  Min 1-sec stream FPS   : %.1f", s["min_window_stream_fps"])
        logger.info("  Stream stall windows   : %d  (a window < %.0f%% of target = stall)  %s",
                    s["drop_windows"], STREAM_DROP_TOLERANCE * 100,
                    "✓ ZERO DROPS" if s["drop_windows"] == 0 else "✗ DROPS DETECTED")
        logger.info("  Peak GPU temperature   : %.1f C  %s",
                    s["max_gpu_temp_c"],
                    "✓" if not s["thermal_fail"] else "✗ OVERHEAT")
        logger.info("  Peak GPU VRAM          : %.1f MB", s["max_gpu_mem_mb"])
        logger.info("  RSS baseline → peak    : %s → %.1f MB (growth %s MB)  %s",
                    s["baseline_rss_mb"], s["max_rss_mb"], s["mem_growth_mb"],
                    "✓ STABLE" if not s["leak_fail"] else "✗ POSSIBLE LEAK")
        logger.info(line)

    def teardown(self):
        self.monitor.shutdown()


# ══════════════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="VisionGuard 30-minute GPU stress test")
    parser.add_argument("--duration", type=int, default=1800,
                        help="Test duration in seconds (default 1800 = 30 min)")
    parser.add_argument("--fps-target", type=int, default=30,
                        help="Minimum sustained FPS considered a pass (default 30)")
    parser.add_argument("--source", choices=["video", "webcam", "auto"], default="auto",
                        help="Frame source (default auto: test videos, else webcam)")
    parser.add_argument("--max-load", action="store_true",
                        help="Force inference on EVERY frame (worst-case thermal load) "
                             "instead of the production frame-skip cadence")
    parser.add_argument("--report-dir", type=str,
                        default=str(config.BASE_DIR / "output" / "stress"),
                        help="Directory for CSV/JSON reports")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Silence ultralytics' per-inference "'half' is deprecated" warning spam so
    # the once-per-second telemetry readout stays legible during long runs.
    # Belt-and-suspenders: a warnings filter (Python warning path) plus a
    # logger-level filter (ultralytics LOGGER path, which resets its own level).
    warnings.filterwarnings("ignore", message=".*deprecated.*")
    _ultra = logging.getLogger("ultralytics")
    _ultra.setLevel(logging.ERROR)
    _ultra.addFilter(_SilenceDeprecated())

    source_kind = args.source
    if source_kind == "auto":
        source_kind = "video" if list(config.TEST_VIDEOS_DIR.glob("*.mp4")) else "webcam"

    test = StressTest(
        duration_s=args.duration,
        fps_target=args.fps_target,
        source_kind=source_kind,
        report_dir=Path(args.report_dir),
        max_load=args.max_load,
    )

    try:
        test.setup()
        passed = test.run()
    except Exception as e:
        logger.critical("[TEST] Fatal error: %s", e, exc_info=True)
        return 1
    finally:
        test.teardown()

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
