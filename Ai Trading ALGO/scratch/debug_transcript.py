import json

tpath = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

with open(tpath, "r", encoding="utf-8") as f:
    count = 0
    for line in f:
        if "write_to_file" in line:
            obj = json.loads(line)
            print("Keys:", obj.keys())
            print("Sample tool calls:", json.dumps(obj.get("tool_calls", []))[:300])
            count += 1
            if count >= 3:
                break
