@echo off
title TRAJEDOR // JARVIS AUTONOMOUS COGNITIVE ENGINE
echo ===============================================================================
echo            TRAJEDOR - AUTONOMOUS INSTITUTIONAL AI TRADING BRAIN
echo               SMC Order Blocks • Trade Doctor Active Defense
echo ===============================================================================

if exist "Ai Trading ALGO\.venv\Scripts\python.exe" (
    "Ai Trading ALGO\.venv\Scripts\python.exe" run_trajedor.py
) else (
    python run_trajedor.py
)

pause
