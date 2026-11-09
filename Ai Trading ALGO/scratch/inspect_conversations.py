import os
import json

conv_ids = [
    "0bd77b67-b9b6-4781-ac9c-a2075dc38501",
    "87648fae-a32a-4d8a-9d16-ea8117d675a3",
    "85e7aa9c-39ed-4bdc-8c40-8e1cbed70cb0",
    "70bda8e2-bc82-4fd9-b297-1286f3d449f5",
    "03b7da76-7763-4f1f-b89b-273343321663",
    "af2223fa-b937-41f7-8bae-c353c0b4e2c7"
]

brain_dir = r"C:\Users\Golu\.gemini\antigravity-ide\brain"

for cid in conv_ids:
    tpath = os.path.join(brain_dir, cid, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(tpath):
        continue
    print(f"\n==================== CONVERSATION: {cid} ====================")
    with open(tpath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                stype = obj.get("type")
                if stype == "USER_INPUT":
                    content = obj.get("content", "")
                    print(f"USER: {content[:150]}...")
                elif stype == "PLANNER_RESPONSE":
                    # Check tool calls
                    calls = obj.get("tool_calls", [])
                    for c in calls:
                        fn = c.get("function", {}).get("name", "")
                        args = c.get("function", {}).get("arguments", {})
                        if fn in ["write_to_file", "replace_file_content", "multi_replace_file_content"]:
                            target = args.get("TargetFile", "")
                            print(f"  EDIT [{fn}]: {target}")
            except Exception as e:
                pass
