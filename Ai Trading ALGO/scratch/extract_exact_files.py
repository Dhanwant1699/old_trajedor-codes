import os
import json
import re

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"
output_dir = r"D:\Ai Trading ALGO\scratch\friday_exact_extracted"

os.makedirs(output_dir, exist_ok=True)

# We will collect the last known full or assembled view of every file before step 5800
CUTOFF_STEP = 5800

# Let's inspect all files viewed or written up to 5800
file_views = {}  # filepath -> dict of {line_num: line_text}

def normalize_rel_path(p):
    p = p.replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    p = re.sub(r'^[a-zA-Z]:[/]+', '', p)
    p = re.sub(r'^ai\s+trading\s+algo[/]+', '', p, flags=re.IGNORECASE)
    p = p.lstrip('/')
    return p

# First, collect all write_to_file up to step 5800 as base
files_content = {}

step_idx = 0
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        step_idx += 1
        if step_idx > CUTOFF_STEP:
            break
        try:
            obj = json.loads(line)
            stype = obj.get("type")
            calls = obj.get("tool_calls", [])
            for c in calls:
                fn = c.get("name", "")
                args = c.get("args", {})
                if fn == "write_to_file":
                    target = normalize_rel_path(args.get("TargetFile", ""))
                    content = args.get("CodeContent", "")
                    if not target.startswith("scratch/") and ".gemini" not in target:
                        files_content[target] = content.replace("\r\n", "\n")
        except:
            pass

print(f"Base written files: {len(files_content)}")

# Now collect view_file outputs up to step 5800 to update/verify files_content
step_idx = 0
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        step_idx += 1
        if step_idx > CUTOFF_STEP:
            break
        try:
            obj = json.loads(line)
            if obj.get("type") == "VIEW_FILE":
                content = obj.get("content", "")
                m_path = re.search(r"File Path:\s*`file:///([^`]+)`", content)
                m_lines = re.search(r"Showing lines\s*([0-9]+)\s*to\s*([0-9]+)", content)
                m_total = re.search(r"Total Lines:\s*([0-9]+)", content)
                if m_path and m_lines:
                    p = normalize_rel_path(m_path.group(1))
                    start_l = int(m_lines.group(1))
                    end_l = int(m_lines.group(2))
                    total_l = int(m_total.group(1)) if m_total else None
                    
                    # Extract the lines shown
                    # Usually formatted like:
                    # LineNumber: LineContent or just lines
                    # Let's see how VIEW_FILE content is formatted
                    if p not in file_views:
                        file_views[p] = {"total_lines": total_l, "slices": []}
                    file_views[p]["slices"].append((step_idx, start_l, end_l, content))
        except:
            pass

print(f"Files with view logs: {len(file_views)}")
for p, v in file_views.items():
    print(f"  {p}: {len(v['slices'])} views, total lines recorded: {v['total_lines']}")
