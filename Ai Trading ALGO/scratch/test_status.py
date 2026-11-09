import requests
import time

t0 = time.time()
r = requests.get('http://localhost:8888/api/status', timeout=10)
data = r.json()
print(f"Status {r.status_code} in {time.time()-t0:.2f}s")
print(f"Balance: {data.get('balance')} | Equity: {data.get('equity')} | Floating PnL: {data.get('total_floating_pnl')}")
print(f"Symbols: {list(data.get('symbols', {}).keys())}")
print(f"Accounts: {list(data.get('accounts', {}).keys())}")
