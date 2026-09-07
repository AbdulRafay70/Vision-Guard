@echo off
title VisionGuard AI — Video Testing Studio
echo ============================================================
echo   🛡️  LAUNCHING VISIONGUARD MULTI-VIDEO TESTING STUDIO
echo ============================================================
echo Opening interactive desktop application...
cd /d "%~dp0"
"..\.venv312\Scripts\python.exe" "visionguard_app.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%
    pause
)
