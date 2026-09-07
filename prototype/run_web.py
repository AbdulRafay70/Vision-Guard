"""
VisionGuard — Web Dashboard Entry Point
Launches the FastAPI Web Server + AI Pipeline together for browser-based monitoring.
Usage:
  python prototype/run_web.py
  python prototype/run_web.py --verbose
"""
import sys
import logging
import argparse
import uvicorn
from pathlib import Path

# Add prototype directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config


def setup_logging(verbose: bool = False):
    """Configure logging for the web server."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    # Quiet noisy third-party loggers
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="VisionGuard Web Server")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose debug logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    # Show config warnings
    warnings = config.validate_config()

    print("\n============================================================")
    print("  [+] VISIONGUARD BACKEND API SERVER")
    print("============================================================")
    print(f"  Backend API URL: http://localhost:{config.WEB_PORT}")
    print(f"  Swagger Docs:    http://localhost:{config.WEB_PORT}/docs")
    print(f"  Live Network API: http://{config.WEB_HOST}:{config.WEB_PORT}")
    if warnings:
        print(f"\n  [!] {len(warnings)} config warning(s):")
        for w in warnings:
            logger.warning(w)
            print(f"    * {w}")
    print("============================================================\n")

    uvicorn.run("web.server:app", host=config.WEB_HOST, port=config.WEB_PORT, reload=True)


if __name__ == "__main__":
    main()
