import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))
from core.dashboard_server import scan_all_accounts

print("Calling scan_all_accounts()...")
t0 = time.time()
res = scan_all_accounts()
print(f"Finished in {time.time()-t0:.2f}s")
print("Accounts returned:", list(res.keys()))
for k, v in res.items():
    print(k, v.get("connected"), v.get("name"), v.get("equity"), v.get("error"))
