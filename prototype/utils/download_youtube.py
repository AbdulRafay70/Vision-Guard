"""
VisionGuard Test Video Downloader
Utility to download benchmark & test footage from YouTube directly into prototype/test_videos/.
Supports age-restricted bypass via Netscape cookies, remote JavaScript challenge solver, and Node.js.
"""

import sys
import os
import argparse
from pathlib import Path

def download_youtube_video(url: str, output_dir: str = None, filename: str = None, cookies_path: str = None):
    """
    Downloads a video from YouTube in MP4 format.
    """
    try:
        import yt_dlp
    except ImportError:
        print("[!] yt-dlp is not installed. Please run: pip install yt-dlp")
        sys.exit(1)

    base_dir = Path(__file__).resolve().parent.parent
    if output_dir is None:
        output_dir = base_dir / "test_videos"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        if not filename.endswith(".mp4"):
            filename += ".%(ext)s"
        outtmpl = str(output_dir / filename)
    else:
        outtmpl = str(output_dir / "%(title)s [%(id)s].%(ext)s")

    # Default cookie file location
    if cookies_path is None:
        default_cookie_file = base_dir / "cookies.txt"
        if default_cookie_file.is_file():
            cookies_path = str(default_cookie_file)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'js_runtimes': {'node': {}},
        'remote_components': {'ejs': 'github'},
    }

    if cookies_path and os.path.isfile(cookies_path):
        ydl_opts['cookiefile'] = cookies_path

    print(f"\n[VisionGuard] Initializing download...")
    print(f"  URL: {url}")
    print(f"  Destination: {output_dir}")
    print(f"  Cookie File: {cookies_path if cookies_path else 'None'}\n")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'video')
            saved_file = ydl.prepare_filename(info)
            if not saved_file.endswith('.mp4'):
                saved_file = str(Path(saved_file).with_suffix('.mp4'))
            print(f"\n[SUCCESS] Video downloaded successfully!")
            print(f"  Title: {video_title}")
            print(f"  File Path: {saved_file}")
            return saved_file
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download YouTube video for VisionGuard testing")
    parser.add_argument(
        "url", 
        nargs="?", 
        default="https://youtu.be/p_P5HMy26dw?si=qcCFslOCPfKBRm9j",
        help="YouTube Video URL"
    )
    parser.add_argument(
        "--output-dir", 
        "-o", 
        default=None, 
        help="Directory to save the video (default: prototype/test_videos)"
    )
    parser.add_argument(
        "--name", 
        "-n", 
        default="violence_group_of_thugs_beating_someone.mp4", 
        help="Custom output filename"
    )
    parser.add_argument(
        "--cookies",
        "-c",
        default=None,
        help="Path to Netscape cookies.txt file"
    )

    args = parser.parse_args()
    download_youtube_video(args.url, args.output_dir, args.name, cookies_path=args.cookies)
