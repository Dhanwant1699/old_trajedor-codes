import os
import json
import re

brain_dir = r"C:\Users\Golu\.gemini\antigravity-ide\brain"
convs = [
    "0bd77b67-b9b6-4781-ac9c-a2075dc38501",
    "87648fae-a32a-4d8a-9d16-ea8117d675a3",
    "85e7aa9c-39ed-4bdc-8c40-8e1cbed70cb0",
    "70bda8e2-bc82-4fd9-b297-1286f3d449f5",
    "03b7da76-7763-4f1f-b89b-273343321663",
    "af2223fa-b937-41f7-8bae-c353c0b4e2c7"
]

for cid in convs:
    tpath = os.path.join(brain_dir, cid, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(tpath):
        continue
    user_times = []
    with open(tpath, "r", encoding="utf-8") as f:
        for line in f:
            if "The current local time is:" in line:
                m = re.findall(r"The current local time is:\s*([0-9T:\-\+\.]+)", line)
                if m:
                    user_times.extend(m)
    print(f"Conversation {cid}:")
    if user_times:
        print(f"  First user time: {user_times[0]}")
        print(f"  Last user time:  {user_times[-1]}")
    else:
        print("  No user times found")
