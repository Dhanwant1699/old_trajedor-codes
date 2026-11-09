import os
import json
import re

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"

def normalize_rel_path(p):
    p = p.replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    p = re.sub(r'^[a-zA-Z]:[/]+', '', p)
    p = re.sub(r'^ai\s+trading\s+algo[/]+', '', p, flags=re.IGNORECASE)
    p = p.lstrip('/')
    return p

# Let's inspect all tool calls in transcript_full up to step 5800
step_idx = 0
tool_events = []
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        step_idx += 1
        if step_idx > 5800:
            break
        try:
            obj = json.loads(line)
            calls = obj.get("tool_calls", [])
            for c in calls:
                fn = c.get("name", "")
                args = c.get("args", {})
                if fn in ["write_to_file", "replace_file_content", "multi_replace_file_content", "run_command"]:
                    tool_events.append((step_idx, fn, args))
        except:
            pass

print(f"Total tool events up to step 5800: {len(tool_events)}")

# Trace files_state
files_state = {}

for s_idx, fn, args in tool_events:
    if fn == "write_to_file":
        target = normalize_rel_path(args.get("TargetFile", ""))
        content = args.get("CodeContent", "")
        if target.startswith("scratch/") or ".gemini" in target:
            continue
        files_state[target] = content
    elif fn == "replace_file_content":
        target = normalize_rel_path(args.get("TargetFile", ""))
        if target.startswith("scratch/") or ".gemini" in target:
            continue
        tc = args.get("TargetContent", "")
        rc = args.get("ReplacementContent", "")
        allow_mult = args.get("AllowMultiple", False)
        
        # Check alias if not found
        candidates = [target]
        if not target.startswith("core/") and ("core/" + target) in files_state:
            candidates.append("core/" + target)
        if target.startswith("core/") and target[5:] in files_state:
            candidates.append(target[5:])
        
        applied = False
        for cand in candidates:
            if cand in files_state:
                curr = files_state[cand]
                tc_norm = tc.replace("\r\n", "\n")
                curr_norm = curr.replace("\r\n", "\n")
                rc_norm = rc.replace("\r\n", "\n")
                if tc in curr:
                    files_state[cand] = curr.replace(tc, rc, 1 if not allow_mult else -1)
                    applied = True
                    break
                elif tc_norm in curr_norm:
                    files_state[cand] = curr_norm.replace(tc_norm, rc_norm, 1 if not allow_mult else -1)
                    applied = True
                    break
        if not applied:
            print(f"[Step {s_idx}] replace failed for {target}")
    elif fn == "multi_replace_file_content":
        target = normalize_rel_path(args.get("TargetFile", ""))
        if target.startswith("scratch/") or ".gemini" in target:
            continue
        chunks = args.get("ReplacementChunks", [])
        candidates = [target]
        if not target.startswith("core/") and ("core/" + target) in files_state:
            candidates.append("core/" + target)
        if target.startswith("core/") and target[5:] in files_state:
            candidates.append(target[5:])
        applied = False
        for cand in candidates:
            if cand in files_state:
                curr = files_state[cand]
                chunk_ok = True
                for ch in chunks:
                    tc = ch.get("TargetContent", "")
                    rc = ch.get("ReplacementContent", "")
                    am = ch.get("AllowMultiple", False)
                    tc_n = tc.replace("\r\n", "\n")
                    rc_n = rc.replace("\r\n", "\n")
                    curr_n = curr.replace("\r\n", "\n")
                    if tc in curr:
                        curr = curr.replace(tc, rc, 1 if not am else -1)
                    elif tc_n in curr_n:
                        curr = curr_n.replace(tc_n, rc_n, 1 if not am else -1)
                    else:
                        print(f"[Step {s_idx}] chunk failed for {cand}")
                        chunk_ok = False
                files_state[cand] = curr
                applied = chunk_ok
                break
        if not applied:
            print(f"[Step {s_idx}] multi_replace failed for {target}")
    elif fn == "run_command":
        cmd = args.get("CommandLine", "")
        # Check if files were moved/copied
        # e.g., git mv or Move-Item or organize_workspace.py
        if "organize_workspace.py" in cmd or "Move-Item" in cmd or "mv " in cmd:
            print(f"[Step {s_idx}] Command: {cmd}")

output_dir = r"D:\Ai Trading ALGO\scratch\friday_restore"
for rel, content in sorted(files_state.items()):
    out_file = os.path.join(output_dir, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as out_f:
        out_f.write(content)

print(f"\nFinal reconstructed files: {len(files_state)}")
