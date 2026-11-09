import os
import json
import glob
from datetime import datetime, timezone
import urllib.parse

# 1. Check Antigravity / Code Local History
history_dirs = [
    r"C:\Users\Golu\AppData\Roaming\Code\User\History",
    r"C:\Users\Golu\AppData\Roaming\Antigravity\User\History",
    r"C:\Users\Golu\AppData\Roaming\Antigravity IDE\User\History"
]

found_entries = []

for hdir in history_dirs:
    if not os.path.exists(hdir):
        continue
    for root, dirs, files in os.walk(hdir):
        if "entries.json" in files:
            entry_path = os.path.join(root, "entries.json")
            try:
                with open(entry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    res = data.get("resource", "")
                    if "Ai Trading ALGO" in urllib.parse.unquote(res) or "Ai%20Trading%20ALGO" in res:
                        found_entries.append((root, data))
            except Exception as e:
                pass

print(f"Found {len(found_entries)} files tracked in Local History")
for root, data in found_entries:
    res = urllib.parse.unquote(data.get("resource", ""))
    entries = data.get("entries", [])
    print(f"\nResource: {res}")
    for entry in entries:
        ts = entry.get("timestamp", 0) / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        eid = entry.get("id", "")
        fpath = os.path.join(root, eid)
        exists = os.path.exists(fpath)
        print(f"  Entry: id={eid}, time={dt}, file_exists={exists}")
