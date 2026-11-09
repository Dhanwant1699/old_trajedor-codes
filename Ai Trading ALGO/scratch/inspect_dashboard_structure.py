import re

with open("docs/dashboard.html", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

lines = content.splitlines()
print(f"Total lines: {len(lines)}")

# Find all HTML elements with id that seem like main sections or views
for idx, line in enumerate(lines):
    if re.search(r'<(div|section|main|nav)[^>]*id="([^"]+)"', line, re.I):
        m = re.search(r'<(div|section|main|nav)[^>]*id="([^"]+)"', line, re.I)
        tag = m.group(1)
        elem_id = m.group(2)
        if any(w in elem_id.lower() for w in ['view', 'tab', 'panel', 'container', 'section', 'modal', 'card', 'table', 'grid']):
            print(f"Line {idx+1:4d}: <{tag} id='{elem_id}'>")
