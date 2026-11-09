import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def timed_import(name, func):
    t0 = time.time()
    print(f"Importing {name}...", end="", flush=True)
    func()
    print(f" OK ({time.time()-t0:.2f}s)", flush=True)

timed_import("config", lambda: __import__("config"))
timed_import("core", lambda: __import__("core"))
timed_import("core.council_state", lambda: __import__("core.council_state"))
timed_import("core.pro_trade_manager", lambda: __import__("core.pro_trade_manager"))
timed_import("core.ai_ledger", lambda: __import__("core.ai_ledger"))
timed_import("core.dual_account_manager", lambda: __import__("core.dual_account_manager"))
timed_import("core.dashboard_server", lambda: __import__("core.dashboard_server"))
timed_import("agents.master_coordinator", lambda: __import__("agents.master_coordinator"))
print("ALL IMPORTS DONE SUCCESSFULLY!", flush=True)
