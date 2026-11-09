"""
TRAJEDOR - Root Launcher & Execution CLI.
Usage:
    python run_trajedor.py           # Runs the autonomous cognitive trading engine
    python run_trajedor.py --ui      # Launches the Iron Man JARVIS Holographic Cockpit UI
    python run_trajedor.py --all     # Launches both the engine and Cockpit UI
"""

import os
import sys
import threading
import subprocess

os.environ["PYTHONUNBUFFERED"] = "1"

# Auto-detect virtualenv from Ai Trading ALGO if present
venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "Ai Trading ALGO", ".venv", "Scripts", "python.exe"))
if os.path.exists(venv_python) and not os.environ.get("TRAJEDOR_VENV_ACTIVATED"):
    os.environ["TRAJEDOR_VENV_ACTIVATED"] = "1"
    if os.path.normpath(sys.executable).lower() != os.path.normpath(venv_python).lower():
        sys.exit(subprocess.call([venv_python, "-u"] + sys.argv))

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from trajedor.src.jarvis_server import start_jarvis_cockpit
from trajedor.src.jarvis_executive import JarvisExecutive


def main():
    args = sys.argv[1:]

    if "--ui" in args or "-u" in args:
        print("[LAUNCHER] Initializing Trajedor Iron Man JARVIS Holographic Cockpit...", flush=True)
        start_jarvis_cockpit(port=1111)

    elif "--all" in args or "-a" in args:
        print("[LAUNCHER] Launching Trajedor JARVIS Suite (Cockpit UI + Autonomous Engine)...")
        # Start UI in background thread
        ui_thread = threading.Thread(target=start_jarvis_cockpit, args=(1111,), daemon=True)
        ui_thread.start()
        
        # Start Autonomous Engine in main thread
        executive = JarvisExecutive()
        executive.run_loop(poll_interval_secs=10)

    else:
        # Default: Run autonomous engine cycle
        print("[LAUNCHER] Initializing Trajedor Autonomous Cognitive Brain...")
        executive = JarvisExecutive()
        executive.run_cycle()


if __name__ == "__main__":
    main()
