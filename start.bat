@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Education Agent Start
echo ============================================

set "PY=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo [1/2] Starting backend (8000)...
start "Backend-8000" /D "%~dp0backend" cmd /k ""%PY%" -m uvicorn app.main:app --port 8000 --log-level warning"

echo [2/2] Starting frontend (5173)...
start "Frontend-5173" /D "%~dp0frontend" cmd /k "npm run dev"

echo Waiting for startup...
timeout /t 8 /nobreak >nul

echo Opening browser...
start "" "http://localhost:5173"

echo.
echo Backend : http://127.0.0.1:8000/docs
echo Frontend: http://localhost:5173
echo Stop    : run stop.bat
pause
