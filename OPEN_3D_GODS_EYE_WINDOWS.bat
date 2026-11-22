@echo off
cd /d "%~dp0"
where npm >nul 2>&1 || (echo Install Node.js first. & pause & exit /b 1)
if not exist "external\gods-eye-view\public\jarvis_gesture_overlay.js" (echo First run INSTALL_GODS_EYE_WINDOWS.ps1. & pause & exit /b 1)
cd external\gods-eye-view
start "" http://127.0.0.1:4173
call npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
pause
