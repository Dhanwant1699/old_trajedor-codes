@echo off
title TRAJEDOR // MASTER JARVIS SUITE LAUNCHER
echo ===============================================================================
echo            TRAJEDOR MASTER SUITE - RUNNING JARVIS AI + COCKPIT UI
echo ===============================================================================

start "" http://localhost:1111

if exist "Ai Trading ALGO\.venv\Scripts\python.exe" (
    "Ai Trading ALGO\.venv\Scripts\python.exe" run_trajedor.py --all
) else (
    python run_trajedor.py --all
)

pause
