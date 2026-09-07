"""
Launcher for VisionGuard Desktop UI Player with interactive console window
"""
import sys
import os
import subprocess
from pathlib import Path

def launch():
    py_script = Path(__file__).parent / "play_video_ui.py"
    venv_py = Path(__file__).parent.parent / ".venv312" / "Scripts" / "python.exe"
    if not venv_py.exists():
        venv_py = Path(sys.executable)

    video_arg = r"D:\testing videos\Security Camera Video of Fire at WLNE.mp4"
    if len(sys.argv) > 1:
        video_arg = sys.argv[1]

    # Use Windows 'start cmd /k ...' to keep the console window open on screen
    cmd_str = f'start "VisionGuard AI UI Player" cmd /k ""{venv_py}" "{py_script}" "{video_arg}""'
    print(f"Launching interactive UI console on user desktop:\n{cmd_str}")
    os.system(cmd_str)

if __name__ == "__main__":
    launch()
