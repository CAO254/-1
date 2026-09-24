@echo off
chcp 65001 >nul
title 教育数字人 - 停止器
echo 正在停止前后端服务...

REM 停止占用 8000 和 5173 端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo 停止后端进程 PID=%%a
    taskkill /F /PID %%a >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo 停止前端进程 PID=%%a
    taskkill /F /PID %%a >nul 2>nul
)

echo.
echo 已停止。关闭打开的后端/前端命令行窗口即可彻底结束。
pause
