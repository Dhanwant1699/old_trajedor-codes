import os
import json
import re

tpath = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

user_steps = []
step_idx = 0

with open(tpath, "r", encoding="utf-8") as f:
    for line in f:
        step_idx += 1
        try:
            obj = json.loads(line)
            stype = obj.get("type")
            if stype == "USER_INPUT":
                content = obj.get("content", "")
                # Extract time
                m = re.search(r"The current local time is:\s*([0-9T:\-\+\.]+)", content)
                time_str = m.group(1) if m else "UNKNOWN_TIME"
                user_req_m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                req_text = user_req_m.group(1).strip() if user_req_m else content[:100].strip()
                user_steps.append((step_idx, time_str, req_text))
        except Exception as e:
            pass

print(f"Total USER_INPUT steps: {len(user_steps)}")
for s_idx, t_str, req in user_steps:
    print(f"Step {s_idx:5d} | Time: {t_str} | Req: {req[:80].replace(chr(10), ' ')}")
