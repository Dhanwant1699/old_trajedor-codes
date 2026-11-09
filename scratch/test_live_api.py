import urllib.request
import json

res = urllib.request.urlopen('http://localhost:1111/api/trajedor/status', timeout=5)
data = json.loads(res.read())
accs = data.get('accounts', {})
print(f"Total Live Accounts: {len(accs)}")
for acc_id, a in accs.items():
    print(f"[{acc_id}]")
    print(f"  Login: {a.get('login')}")
    print(f"  Server: {a.get('server')}")
    print(f"  Status: {a.get('status')}")
    print(f"  Balance: {a.get('balance')}")
    print(f"  Equity: {a.get('equity')}")
