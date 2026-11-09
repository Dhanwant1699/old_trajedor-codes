import json

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        step_idx = idx + 1
        if step_idx in [588, 594, 2843]:
            obj = json.loads(line)
            print(f"=== Step {step_idx} ===")
            for c in obj.get("tool_calls", []):
                print(c.get("name"))
                print(c.get("args", {}).get("TargetFile"))
                print("ReplacementContent:")
                print(c.get("args", {}).get("ReplacementContent"))
