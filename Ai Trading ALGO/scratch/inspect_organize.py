import json

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "organize_workspace.py" in line and "write_to_file" in line:
            obj = json.loads(line)
            for c in obj.get("tool_calls", []):
                print(c.get("args", {}).get("CodeContent"))
