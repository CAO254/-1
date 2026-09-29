@echo off
chcp 65001 >nul
title Education Agent - Stop
echo Stopping backend (8000) and frontend (5173)...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Kill backend PID=%%a
    taskkill /F /PID %%a >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo Kill frontend PID=%%a
    taskkill /F /PID %%a >nul 2>nul
)

echo.
echo Done. Also close the Backend/Frontend console windows if open.
echo.
pause
