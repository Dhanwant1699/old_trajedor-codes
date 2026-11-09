import os
import json
from datetime import datetime

brain_dir = r"C:\Users\Golu\.gemini\antigravity-ide\brain"

# Let's inspect conversation timestamps
convs = [
    "0c711b1e-466b-4b07-be85-8360ceb6a251",
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
    first_time = None
    last_time = None
    count = 0
    with open(tpath, "r", encoding="utf-8") as f:
        for line in f:
            count += 1
            if '"timestamp"' in line:
                try:
                    obj = json.loads(line)
                    # timestamp might be in step
                    ts = obj.get("timestamp")
                    if ts:
                        if not first_time:
                            first_time = ts
                        last_time = ts
                except:
                    pass
    print(f"Conversation {cid}: {count} lines | First: {first_time} | Last: {last_time}")
