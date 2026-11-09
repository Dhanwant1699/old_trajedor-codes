import json
import re

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

view_events = []
with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        step_idx = idx + 1
        if 5000 <= step_idx <= 5800:
            if '"view_file"' in line or 'File Path:' in line:
                obj = json.loads(line)
                if obj.get("type") == "VIEW_FILE":
                    content = obj.get("content", "")
                    m_path = re.search(r"File Path:\s*`([^`]+)`", content)
                    m_lines = re.search(r"Total Lines:\s*([0-9]+)", content)
                    p = m_path.group(1) if m_path else ""
                    tl = m_lines.group(1) if m_lines else ""
                    view_events.append((step_idx, p, tl))

print(f"Total view events between 5000 and 5800: {len(view_events)}")
for s, p, tl in view_events:
    print(f"Step {s:5d}: {p} (Total lines: {tl})")
