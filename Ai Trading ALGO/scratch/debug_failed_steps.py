import json
import re

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

failed_steps = [1932, 2008, 2304, 2389, 3124, 3239, 3267, 3503, 3511, 4496, 4770, 4969, 4975, 4981, 5365, 5548, 5626, 5665]

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        step_idx = idx + 1
        if step_idx in failed_steps or (step_idx - 1) in failed_steps:
            obj = json.loads(line)
            print(f"=== Step {step_idx}: type={obj.get('type')}, status={obj.get('status')} ===")
            if obj.get("tool_calls"):
                for c in obj["tool_calls"]:
                    print(f"  Tool: {c.get('name')}")
                    args = c.get('args', {})
                    print(f"  Target: {args.get('TargetFile')}")
                    tc = args.get('TargetContent', '')
                    print(f"  TargetContent snippet: {repr(tc[:80])}")
            if obj.get("content"):
                print(f"  Content: {str(obj.get('content'))[:200]}")
