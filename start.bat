@echo off
chcp 65001 >nul
title 教育数字人 - 启动器
cd /d "%~dp0"

echo ============================================
echo   教育数字人 一键启动
echo ============================================

REM ---- 启动后端 ----
where python >nul 2>nul
if exist "backend\venv\Scripts\python.exe" (
    set "PY=backend\venv\Scripts\python.exe"
) else (
    set "PY=python"
)
echo [1/2] 启动后端 (8000)...
start "后端-8000" cmd /k "cd /d %~dp0backend && %PY% -m uvicorn app.main:app --port 8000 --log-level warning"

REM ---- 启动前端 ----
echo [2/2] 启动前端 (5173)...
start "前端-5173" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 6 /nobreak >nul
echo.
echo 后端: http://127.0.0.1:8000/docs
echo 前端: http://localhost:5173
echo.
pause
