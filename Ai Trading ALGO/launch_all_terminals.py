"""
Autonomous Multi-Terminal Launcher for AI Trading Council.
Scans configured MT5 accounts in data/admin_config.json and starts any closed terminal.
"""

import os
import sys

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import subprocess
import time
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "admin_config.json")

def get_running_terminal_paths():
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path"],
            text=True
        )
        return set(os.path.normpath(p.strip()).lower() for p in out.splitlines() if p.strip())
    except Exception:
        return set()

def launch_all_terminals():
    print("==================================================")
    print("🚀 LAUNCHING ALL CONFIGURED METATRADER 5 TERMINALS")
    print("==================================================")

    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Admin config not found at: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    accounts = config.get("accounts", {})
    running = get_running_terminal_paths()

    launched_count = 0
    already_running = 0

    for acc_id, acc in accounts.items():
        name = acc.get("name", acc_id)
        path = acc.get("terminal_path", "")
        if not path or not os.path.exists(path):
            print(f"⚠️ [{name}] Executable not found at: {path}")
            continue

        normalized_path = os.path.normpath(path).lower()
        if normalized_path in running:
            print(f"✅ [{name}] Already running: {path}")
            already_running += 1
        else:
            print(f"⚡ [{name}] Starting terminal: {path} ...")
            try:
                subprocess.Popen([path], shell=False)
                launched_count += 1
                time.sleep(1.0)
            except Exception as e:
                print(f"❌ Failed to launch {name}: {e}")

    print("\n--------------------------------------------------")
    print(f"🎯 Status: {already_running} already running | {launched_count} newly launched.")
    print("==================================================")

if __name__ == "__main__":
    launch_all_terminals()
