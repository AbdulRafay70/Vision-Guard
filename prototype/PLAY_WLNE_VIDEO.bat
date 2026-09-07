@echo off
title VisionGuard AI - Live Detection Window
echo ============================================================
echo   🛡️  VISIONGUARD AI — LIVE DETECTION WINDOW PLAYER
echo ============================================================
echo Playing video: "D:\testing videos\Security Camera Video of Fire at WLNE.mp4"
echo Displaying live OpenCV window on your desktop screen...
echo Press 'Q' inside the video window to quit.
echo ============================================================
cd /d "%~dp0"
"..\.venv312\Scripts\python.exe" "play_video_ui.py" "D:\testing videos\Security Camera Video of Fire at WLNE.mp4"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Player exited with code %ERRORLEVEL%
    pause
)
