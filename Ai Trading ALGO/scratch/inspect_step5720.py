import json

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        step_idx = idx + 1
        if step_idx in [5720, 5721, 5722, 5723, 5724, 5725]:
            obj = json.loads(line)
            print(f"Step {step_idx}: type={obj.get('type')}")
            for c in obj.get("tool_calls", []):
                print(f"  Tool: {c.get('name')}")
                print(f"  Args: {json.dumps(c.get('args'))[:300]}")
