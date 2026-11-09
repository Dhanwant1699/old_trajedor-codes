import re

with open("docs/dashboard.html", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

lines = content.splitlines()

# Search for /api/status or fetch calls
for idx, line in enumerate(lines):
    if "/api/status" in line or "function update" in line:
        print(f"Line {idx+1:4d}: {line[:100]}")
