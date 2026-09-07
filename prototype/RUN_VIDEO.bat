@echo off
title VisionGuard AI — Video Detection & Analysis Player
echo ============================================================
echo   [VISIONGUARD] REAL-TIME DETECTION & ANALYSIS PLAYER
echo ============================================================
cd /d "%~dp0"

set VIDEO_FILE=%1
if "%VIDEO_FILE%"=="" (
    set VIDEO_FILE=Videos\fire.mp4
)

echo Processing Video: %VIDEO_FILE%
echo Keyboard Controls:
echo   [Q] - Quit Player
echo   [P] - Pause / Resume
echo   [Space] - Step Frame
echo   [D] - Toggle Bounding Boxes
echo   [T] - Toggle Person Tracking IDs
echo   [K] - Toggle Pose Skeletons
echo   [S] - Save Screenshot
echo.

if exist "..\.venv312\Scripts\python.exe" (
    "..\.venv312\Scripts\python.exe" run.py --source video --file "%VIDEO_FILE%"
) else (
    python run.py --source video --file "%VIDEO_FILE%"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Player exited with code %ERRORLEVEL%
    pause
)
