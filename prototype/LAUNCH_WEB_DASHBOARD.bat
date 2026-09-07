@echo off
title VisionGuard AI — Backend API Server
echo ============================================================
echo   🛡️  LAUNCHING VISIONGUARD BACKEND API SERVER (FASTAPI)
echo ============================================================
echo.
echo Starting FastAPI API Server at http://localhost:8000 ...
echo Press Ctrl+C to stop.
echo.
cd /d "%~dp0"
"..\.venv312\Scripts\python.exe" "run_web.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Web server stopped with error code %ERRORLEVEL%
    pause
)
