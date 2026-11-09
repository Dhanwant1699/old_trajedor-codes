import json

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

files_to_track = ["risk_manager.py", "core/risk_manager.py", "core/dashboard_server.py", "docs/dashboard.html", "core/dual_account_manager.py", "core/data_engine.py", "data/admin_config.json"]

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        step_idx = idx + 1
        if step_idx > 5800:
            break
        if any(f in line for f in files_to_track):
            obj = json.loads(line)
            for c in obj.get("tool_calls", []):
                fn = c.get("name")
                args = c.get("args", {})
                tf = args.get("TargetFile", "")
                if any(k in tf for k in files_to_track):
                    print(f"Step {step_idx}: fn={fn}, file={tf}")
