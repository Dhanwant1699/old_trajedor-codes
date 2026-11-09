@echo off
title Trajedor System Diagnostics
echo ===============================================================================
echo               TRAJEDOR 360-DEGREE SYSTEM STATUS & HEALTH CHECK
echo ===============================================================================
cd /d "%~dp0Ai Trading ALGO"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" core\market_research_terminal.py
) else (
    python core\market_research_terminal.py
)

pause
