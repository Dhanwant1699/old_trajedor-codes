"""
Launcher for AI Trading Council Visual Web Cockpit Dashboard.
Runs standalone on Port 1111 (or custom port).
Usage:
    python launch_dashboard.py
    python launch_dashboard.py 1111
"""

import os
import sys

# Auto-detect and re-execute using project virtualenv (.venv) if run with global python
venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe"))
if os.path.exists(venv_python) and os.path.normpath(sys.executable).lower() != os.path.normpath(venv_python).lower():
    import subprocess
    sys.exit(subprocess.call([venv_python] + sys.argv))

# Ensure root in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import CONFIG
from core.dashboard_server import run_dashboard_server

if __name__ == "__main__":
    target_port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else getattr(CONFIG, "DASHBOARD_PORT", 1111)
    run_dashboard_server(port=target_port)
