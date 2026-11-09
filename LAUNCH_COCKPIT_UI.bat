@echo off
title TRAJEDOR // JARVIS MARK-85 HOLOGRAPHIC COCKPIT
echo ===============================================================================
echo        TRAJEDOR - IRON MAN JARVIS HOLOGRAPHIC AI TRADING COCKPIT
echo                           PORT: http://localhost:1111
echo ===============================================================================

start "" http://localhost:1111

if exist "Ai Trading ALGO\.venv\Scripts\python.exe" (
    "Ai Trading ALGO\.venv\Scripts\python.exe" run_trajedor.py --ui
) else (
    python run_trajedor.py --ui
)

pause
