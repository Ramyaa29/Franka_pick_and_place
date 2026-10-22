@echo off
title Franka Emika Panda - Docker Desktop Deployment
echo ========================================================
echo 🤖 Deploying Franka Panda Robot to Docker Desktop...
echo ========================================================

cd /d "%~dp0"

echo [1/3] Building Docker image and starting container...
docker compose up --build -d

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo ✅ Container successfully deployed to Docker Desktop!
    echo.
    echo 📌 Docker Desktop Application:
    echo    Look for container: "panda_robot_stack" (Status: Running)
    echo.
    echo 🌐 Open Web Dashboard in your browser:
    echo    👉 http://localhost:5000
    echo ========================================================
    echo.
    echo Opening browser automatically...
    start http://localhost:5000
) else (
    echo.
    echo [ERROR] Failed to start container. Make sure Docker Desktop is running!
)

pause
