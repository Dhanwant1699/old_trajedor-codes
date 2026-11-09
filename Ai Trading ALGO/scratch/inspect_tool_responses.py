import json

tpath = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

with open(tpath, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if idx > 100:
            break
        obj = json.loads(line)
        if obj.get("source") == "SYSTEM" or obj.get("type") not in ["USER_INPUT", "PLANNER_RESPONSE"]:
            print(f"Step {idx}: type={obj.get('type')}, source={obj.get('source')}, status={obj.get('status')}")
            content = str(obj.get("content", ""))
            print(f"   content: {content[:150]}")
