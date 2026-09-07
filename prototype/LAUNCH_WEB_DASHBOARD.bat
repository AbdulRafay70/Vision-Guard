@echo off
title VisionGuard AI — Web Command Center
echo ============================================================
echo   🛡️  LAUNCHING VISIONGUARD WEB COMMAND CENTER (REACT + FASTAPI)
echo ============================================================
echo.
echo Starting FastAPI Server at http://localhost:8000 ...
echo Press Ctrl+C to stop.
echo.
cd /d "%~dp0"
"..\.venv312\Scripts\python.exe" "run_web.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Web server stopped with error code %ERRORLEVEL%
    pause
)
