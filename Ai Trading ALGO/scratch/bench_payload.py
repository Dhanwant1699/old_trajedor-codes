import time
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from core.dashboard_server import get_live_dashboard_payload, scan_all_accounts, get_real_mt5_trade_history

print("Testing scan_all_accounts()...")
t0 = time.time()
accs = scan_all_accounts(force_refresh=True)
print(f"scan_all_accounts took {time.time()-t0:.2f}s | Results: {len(accs)} accounts")

print("\nTesting get_real_mt5_trade_history()...")
t0 = time.time()
hist = get_real_mt5_trade_history(30)
print(f"get_real_mt5_trade_history took {time.time()-t0:.2f}s | Trades: {len(hist.get('trades', []))}")

print("\nTesting get_live_dashboard_payload()...")
t0 = time.time()
payload = get_live_dashboard_payload(force_refresh=True)
print(f"get_live_dashboard_payload took {time.time()-t0:.2f}s")
