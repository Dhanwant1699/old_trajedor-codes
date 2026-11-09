import json

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        step_idx = idx + 1
        if 580 <= step_idx <= 600:
            obj = json.loads(line)
            print(f"Step {step_idx}: type={obj.get('type')}, status={obj.get('status')}")
            for c in obj.get("tool_calls", []):
                print(f"  Tool: {c.get('name')}")
                print(f"  Args: {json.dumps(c.get('args'))[:200]}")
            if obj.get("content"):
                print(f"  Content: {str(obj.get('content'))[:200]}")
