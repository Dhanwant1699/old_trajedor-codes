import requests
import json

r = requests.get('http://localhost:8888/api/admin/config', timeout=5)
print(f"Status: {r.status_code}")
data = r.json()
print("Keys:", data.keys())
print("Config:", json.dumps(data.get("config", {}), indent=2)[:300])
print("Telemetry:", json.dumps(data.get("telemetry", {}), indent=2)[:300])
