"""
VisionGuard Prototype — Main Entry Point
Run: python run.py --source webcam
Run: python run.py --source video --file test_videos/fire_test.mp4
Run: python run.py --source webcam --voice
Run: python run.py --test-all
"""
import argparse
import cv2
import logging
import sys
import time
import os
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Back, Style

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
from camera.webcam import WebcamSource
from camera.video_file import VideoFileSource
from ai.pipeline import AIPipeline, FrameAnalysis
from events.engine import EventEngine, EVENT_EMOJI
from events.base import EventAlert
from output.display import DisplayRenderer
from output.evidence import EvidencePackageGenerator

# Initialize colorama for Windows color support
init()


def setup_logging(verbose: bool = False):
    """Configure logging for the entire application."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    # Quiet noisy third-party loggers.
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def print_banner():
    """Print the VisionGuard startup banner."""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"  VISIONGUARD PROTOTYPE v0.2")
    print(f"  Pakistan's AI City Protection System")
    print(f"{'=' * 60}{Style.RESET_ALL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python: {sys.version.split()[0]}")
    print()


def print_config_warnings():
    """Display configuration validation warnings."""
    warnings = config.validate_config()
    if warnings:
        print(f"\n{Fore.YELLOW}  ⚠️  Configuration Warnings:{Style.RESET_ALL}")
        for w in warnings:
            logger.warning("  %s", w)
            print(f"    • {w}")
        print()


def print_event_alert(alert: EventAlert):
    """Print a formatted event alert to the console."""
    emoji = EVENT_EMOJI.get(alert.event_type, "⚠️")

    # Color based on risk level
    if alert.risk_level == "CRITICAL":
        color = Fore.RED + Style.BRIGHT
    elif alert.risk_level == "HIGH":
        color = Fore.YELLOW + Style.BRIGHT
    elif alert.risk_level == "MEDIUM":
        color = Fore.CYAN
    else:
        color = Fore.GREEN

    print(f"\n{color}{'=' * 60}")
    print(f"  {emoji}{emoji}{emoji} EVENT DETECTED: {alert.event_type.upper()} {emoji}{emoji}{emoji}")
    print(f"{'=' * 60}{Style.RESET_ALL}")
    print(f"  {color}Event Type:     {alert.event_type.upper()}{Style.RESET_ALL}")
    print(f"  {color}Risk Score:     {alert.risk_score} / 100  ->  {alert.risk_level}{Style.RESET_ALL}")
    print(f"  Duration:       {alert.duration_seconds:.1f} seconds")
    print(f"  Description:    {alert.description}")
    print()
    print(f"  {Fore.BLUE}Department:     {alert.department} ({alert.dial}){Style.RESET_ALL}")
    print(f"  {Fore.BLUE}Action:         {alert.action}{Style.RESET_ALL}")

    if alert.action == "AUTO_DISPATCH":
        print(f"  {Fore.RED + Style.BRIGHT}>>> AUTO-DISPATCHING {alert.department} <<<{Style.RESET_ALL}")
    elif alert.action == "TEAM_REVIEW":
        print(f"  {Fore.YELLOW}>>> TEAM REVIEW REQUIRED <<<{Style.RESET_ALL}")

    print(f"{color}{'=' * 60}{Style.RESET_ALL}\n")


def print_frame_summary(analysis: FrameAnalysis, frame_num: int):
    """Print compact frame summary to console (periodically)."""
    if frame_num % 30 != 0:  # Only print every 30th processed frame
        return

    summary = analysis.get_summary()
    if summary == "No detections":
        return

    tracks = analysis.tracks
    track_info = []
    for t in tracks[:5]:  # Show first 5 tracks
        vel = f" v={t.avg_velocity:.1f}" if t.avg_velocity > 1 else ""
        track_info.append(f"{t.vg_id}({t.class_name}{vel})")

    print(f"  {Fore.GREEN}[Frame {frame_num:>5d}]{Style.RESET_ALL} "
          f"{summary} | "
          f"Tracks: {', '.join(track_info) if track_info else 'none'}")


def save_evidence(frame, alert: EventAlert):
    """Save evidence screenshot when an event is detected."""
    config.EVIDENCE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{alert.event_type}_{timestamp}.jpg"
    filepath = config.EVIDENCE_DIR / filename
    cv2.imwrite(str(filepath), frame)
    alert.evidence_path = str(filepath)
    logger.info("Evidence saved: %s", filepath)
    print(f"  📸 Evidence saved: {filepath}")


class BackgroundAI:
    """
    Runs the AI pipeline + event engine on a background thread using
    latest-frame semantics, so video presentation never waits for inference.

    Previously the display loop ran AI on every frame before showing it: when
    inference took longer than one frame interval, playback stuttered and
    showed visible gaps. Now the video plays at its natural speed and overlays
    the most recent AI result.
    """

    def __init__(self, pipeline, event_engine, evidence_gen):
        import threading, queue
        self.pipeline = pipeline
        self.event_engine = event_engine
        self.evidence_gen = evidence_gen
        self._lock = threading.Lock()
        self._frame = None
        self._frame_seq = 0
        self._analysis = None
        self.alerts = queue.Queue()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="run-ai")
        self._thread.start()

    def submit(self, frame):
        with self._lock:
            self._frame = frame
            self._frame_seq += 1

    def latest(self):
        with self._lock:
            return self._analysis

    def _loop(self):
        last_seq = 0
        while self._running:
            with self._lock:
                frame, seq = self._frame, self._frame_seq
            if frame is None or seq == last_seq:
                time.sleep(0.002)
                continue
            last_seq = seq
            try:
                analysis = self.pipeline.process_frame(frame)
                self.evidence_gen.push_frame(frame)
                if analysis:
                    for alert in self.event_engine.process(analysis):
                        self.alerts.put((alert, frame))
                    print_frame_summary(analysis, self.pipeline.frame_count)
                with self._lock:
                    self._analysis = analysis
            except Exception as e:
                logging.getLogger(__name__).error("[AI] Processing error: %s", e, exc_info=True)

    def drain_alerts(self):
        out = []
        while not self.alerts.empty():
            out.append(self.alerts.get_nowait())
        return out

    def stop(self):
        self._running = False
        self._thread.join(timeout=2.0)


def fit_to_window(img, max_w=None, max_h=None):
    """Resize preserving aspect ratio (portrait videos were being squashed)."""
    max_w = max_w or config.DISPLAY_WIDTH
    max_h = max_h or config.DISPLAY_HEIGHT
    h, w = img.shape[:2]
    scale = min(max_w / w, max_h / h)
    if abs(scale - 1.0) < 1e-3:
        return img
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=interp)


def run_webcam(args):
    """Run VisionGuard with laptop webcam."""
    print(f"\n{Fore.CYAN}[MODE] Webcam — Live Detection{Style.RESET_ALL}")
    print(f"  Controls: Q=Quit P=Pause D=Detections T=Tracks K=Skeleton S=Screenshot\n")

    # Initialize components
    source = WebcamSource(camera_index=0)
    pipeline = AIPipeline()
    event_engine = EventEngine()
    display = DisplayRenderer()
    evidence_gen = EvidencePackageGenerator()

    if not source.start():
        print(f"{Fore.RED}[ERROR] Cannot open webcam!{Style.RESET_ALL}")
        return

    pipeline.load_models()
    ai = BackgroundAI(pipeline, event_engine, evidence_gen)

    print(f"\n{Fore.GREEN}[READY] VisionGuard is running. Press 'Q' to quit.{Style.RESET_ALL}\n")

    try:
        while True:
            ret, frame = source.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Hand the newest frame to the background AI (never blocks playback)
            ai.submit(frame)
            analysis = ai.latest()

            # Print any new alerts
            for alert, alert_frame in ai.drain_alerts():
                print_event_alert(alert)
                save_evidence(alert_frame, alert)

            # Render display
            active_alerts = event_engine.get_active_alerts()
            display_frame = display.render(frame, analysis, active_alerts, source.source_name)

            # Resize to fit display window
            display_frame = fit_to_window(display_frame)

            # Show frame
            cv2.imshow("VisionGuard", display_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('d') or key == ord('D'):
                display.toggle_detections()
            elif key == ord('t') or key == ord('T'):
                display.toggle_tracks()
            elif key == ord('k') or key == ord('K'):
                display.toggle_skeletons()
            elif key == ord('s') or key == ord('S'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(str(config.EVIDENCE_DIR / f"screenshot_{timestamp}.jpg"), display_frame)
                print(f"  📸 Screenshot saved!")
            elif key == ord('r') or key == ord('R'):
                pipeline.reset_tracks()

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[STOP] Interrupted by user.{Style.RESET_ALL}")
    finally:
        ai.stop()
        pipeline.stop()
        source.stop()
        cv2.destroyAllWindows()
        _print_session_summary(event_engine)


def run_video(args):
    """Run VisionGuard on a video file."""
    file_path = args.file
    if not file_path:
        print(f"{Fore.RED}[ERROR] No video file specified. Use --file path/to/video.mp4{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}[MODE] Video File — {file_path}{Style.RESET_ALL}\n")

    source = VideoFileSource(file_path)
    pipeline = AIPipeline()
    event_engine = EventEngine()
    display = DisplayRenderer()
    evidence_gen = EvidencePackageGenerator()

    if not source.start():
        return

    pipeline.load_models()
    ai = BackgroundAI(pipeline, event_engine, evidence_gen)

    print(f"\n{Fore.GREEN}[READY] Processing video...{Style.RESET_ALL}\n")

    try:
        while source.is_opened():
            ret, frame = source.read()
            if not ret:
                break

            # Hand the newest frame to the background AI (never blocks playback)
            ai.submit(frame)
            analysis = ai.latest()

            for alert, alert_frame in ai.drain_alerts():
                print_event_alert(alert)
                save_evidence(alert_frame, alert)

            # Render display
            active_alerts = event_engine.get_active_alerts()
            display_frame = display.render(frame, analysis, active_alerts, source.source_name)

            # Draw progress bar
            current, total = source.get_progress()
            if total > 0:
                progress = current / total
                h, w = display_frame.shape[:2]
                bar_width = int(w * progress)
                cv2.rectangle(display_frame, (0, h - 5), (bar_width, h), (0, 255, 0), -1)
                cv2.rectangle(display_frame, (bar_width, h - 5), (w, h), (50, 50, 50), -1)

            # Resize to fit display window
            display_frame = fit_to_window(display_frame)

            cv2.imshow("VisionGuard", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('p') or key == ord('P'):
                source.toggle_pause()
            elif key == ord(' '):
                source.step_frame()
            elif key == ord('d') or key == ord('D'):
                display.toggle_detections()
            elif key == ord('t') or key == ord('T'):
                display.toggle_tracks()
            elif key == ord('k') or key == ord('K'):
                display.toggle_skeletons()
            elif key == ord('s') or key == ord('S'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(str(config.EVIDENCE_DIR / f"screenshot_{timestamp}.jpg"), display_frame)
                print(f"  📸 Screenshot saved!")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[STOP] Interrupted.{Style.RESET_ALL}")
    finally:
        ai.stop()
        pipeline.stop()
        source.stop()
        cv2.destroyAllWindows()
        _print_session_summary(event_engine)


def run_test_all(args):
    """Run all test videos and generate pass/fail report."""
    print(f"\n{Fore.CYAN}{'═' * 60}")
    print(f"  VISIONGUARD — BATCH TEST MODE")
    print(f"{'═' * 60}{Style.RESET_ALL}\n")

    test_dir = config.TEST_VIDEOS_DIR

    if not test_dir.exists() or not list(test_dir.glob("*.mp4")):
        print(f"{Fore.RED}[ERROR] No test videos found in {test_dir}{Style.RESET_ALL}")
        print(f"  Place .mp4 test videos in: {test_dir}")
        return

    video_files = sorted(test_dir.glob("*.mp4"))
    results = []

    pipeline = AIPipeline()
    pipeline.load_models()

    try:
        for i, video_file in enumerate(video_files):
            print(f"\n{Fore.CYAN}[{i+1}/{len(video_files)}] Testing: {video_file.name}{Style.RESET_ALL}")

            source = VideoFileSource(str(video_file), throttle=False)
            event_engine = EventEngine()

            if not source.start():
                results.append({"file": video_file.name, "status": "ERROR", "events": []})
                continue

            pipeline.reset()  # Full reset: tracker + stagger counters + cached state
            detected_events = []
            start_time = time.time()

            while source.is_opened():
                ret, frame = source.read()
                if not ret:
                    break

                analysis = pipeline.process_frame(frame)
                if analysis:
                    new_alerts = event_engine.process(analysis)
                    for alert in new_alerts:
                        detected_events.append({
                            "type": alert.event_type,
                            "risk": alert.risk_score,
                            "level": alert.risk_level,
                            "description": alert.description,
                        })

            elapsed = time.time() - start_time
            source.stop()

            # Report
            if detected_events:
                for evt in detected_events:
                    emoji = EVENT_EMOJI.get(evt["type"], "⚠️")
                    print(f"  {Fore.GREEN}Detected: {emoji} {evt['type'].upper()} "
                          f"(risk={evt['risk']}%, {evt['level']}){Style.RESET_ALL}")
            else:
                print(f"  {Fore.YELLOW}No events detected.{Style.RESET_ALL}")

            print(f"  Processing time: {elapsed:.1f}s")

            results.append({
                "file": video_file.name,
                "status": "PASS" if detected_events else "NO_EVENTS",
                "events": detected_events,
                "time": elapsed,
            })
    finally:
        pipeline.stop()

    # Print final report
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"  BATCH TEST RESULTS")
    print(f"{'=' * 60}{Style.RESET_ALL}\n")

    for r in results:
        status_color = Fore.GREEN if r["events"] else Fore.YELLOW
        events_str = ", ".join(e["type"] for e in r["events"]) if r["events"] else "none"
        print(f"  {status_color}{r['file']:40s} -> {events_str}{Style.RESET_ALL}")


def _print_session_summary(event_engine: EventEngine):
    """Print session summary when stopping."""
    summary = event_engine.get_status_summary()
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"  SESSION SUMMARY")
    print(f"{'=' * 60}{Style.RESET_ALL}")
    print(f"  Total alerts generated: {summary['total_alerts_today']}")
    print(f"  Active alerts at end:   {summary['active_alerts']}")

    if summary['alerts']:
        print(f"\n  Active Alerts:")
        for a in summary['alerts']:
            print(f"    {a['emoji']} {a['type']:20s} risk={a['risk']:3d}%  {a['level']:10s}  → {a['department']}")

    print(f"{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="VisionGuard Prototype")
    parser.add_argument("--source", choices=["webcam", "video"], default="webcam",
                       help="Input source: webcam or video file")
    parser.add_argument("--file", type=str, default=None,
                       help="Path to video file (when --source video)")
    parser.add_argument("--test-all", action="store_true",
                       help="Run all test videos in batch mode")
    parser.add_argument("--voice", action="store_true",
                       help="Enable voice commands (requires Gemini API key)")
    parser.add_argument("--device", type=str, default="auto",
                       help="Device for inference: '0' for GPU, 'cpu' for CPU, 'auto' for automatic selection")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose debug logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    # Update device setting
    if args.device == "cpu":
        config.DETECTION_DEVICE = "cpu"
    elif args.device == "auto":
        import torch
        config.DETECTION_DEVICE = 0 if torch.cuda.is_available() else "cpu"
    else:
        try:
            config.DETECTION_DEVICE = int(args.device)
        except ValueError:
            config.DETECTION_DEVICE = args.device

    print_banner()
    print_config_warnings()

    if args.test_all:
        run_test_all(args)
    elif args.source == "video":
        run_video(args)
    else:
        run_webcam(args)


if __name__ == "__main__":
    main()
