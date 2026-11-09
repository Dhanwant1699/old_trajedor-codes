import os
import json
import re
import sys

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"
output_dir = r"D:\Ai Trading ALGO\scratch\friday_restore"

os.makedirs(output_dir, exist_ok=True)

# Step 5800 is the start of Saturday morning
CUTOFF_STEP = 5800

files_state = {}  # rel_path -> content (string)

def normalize_rel_path(p):
    p = p.replace("\\", "/")
    # Normalize drive letters
    p = re.sub(r'^[a-zA-Z]:[/]+', '', p)
    p = re.sub(r'^ai\s+trading\s+algo[/]+', '', p, flags=re.IGNORECASE)
    p = p.lstrip('/')
    return p

step_idx = 0
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        step_idx += 1
        if step_idx > CUTOFF_STEP:
            break
        try:
            obj = json.loads(line)
            stype = obj.get("type")
            calls = obj.get("tool_calls", [])
            for c in calls:
                fn = c.get("name", "")
                args = c.get("args", {})
                if fn == "write_to_file":
                    target = args.get("TargetFile", "")
                    content = args.get("CodeContent", "")
                    rel = normalize_rel_path(target)
                    if rel.startswith("scratch/") or rel.startswith("scratch\\") or ".gemini" in rel:
                        continue
                    files_state[rel] = content
                elif fn == "replace_file_content":
                    target = args.get("TargetFile", "")
                    rel = normalize_rel_path(target)
                    if rel.startswith("scratch/") or rel.startswith("scratch\\") or ".gemini" in rel:
                        continue
                    target_content = args.get("TargetContent", "")
                    replacement_content = args.get("ReplacementContent", "")
                    allow_mult = args.get("AllowMultiple", False)
                    if rel in files_state:
                        curr = files_state[rel]
                        if target_content in curr:
                            if allow_mult:
                                files_state[rel] = curr.replace(target_content, replacement_content)
                            else:
                                files_state[rel] = curr.replace(target_content, replacement_content, 1)
                        else:
                            # Try normalizing line endings
                            tc_norm = target_content.replace("\r\n", "\n")
                            curr_norm = curr.replace("\r\n", "\n")
                            if tc_norm in curr_norm:
                                rc_norm = replacement_content.replace("\r\n", "\n")
                                if allow_mult:
                                    files_state[rel] = curr_norm.replace(tc_norm, rc_norm)
                                else:
                                    files_state[rel] = curr_norm.replace(tc_norm, rc_norm, 1)
                            else:
                                print(f"[Step {step_idx}] WARNING: targetContent not found in {rel}")
                    else:
                        print(f"[Step {step_idx}] WARNING: {rel} not in files_state for replace_file_content")
                elif fn == "multi_replace_file_content":
                    target = args.get("TargetFile", "")
                    rel = normalize_rel_path(target)
                    if rel.startswith("scratch/") or rel.startswith("scratch\\") or ".gemini" in rel:
                        continue
                    chunks = args.get("ReplacementChunks", [])
                    if rel in files_state:
                        curr = files_state[rel]
                        for chunk in chunks:
                            tc = chunk.get("TargetContent", "")
                            rc = chunk.get("ReplacementContent", "")
                            allow_mult = chunk.get("AllowMultiple", False)
                            if tc in curr:
                                if allow_mult:
                                    curr = curr.replace(tc, rc)
                                else:
                                    curr = curr.replace(tc, rc, 1)
                            else:
                                tc_norm = tc.replace("\r\n", "\n")
                                curr_norm = curr.replace("\r\n", "\n")
                                if tc_norm in curr_norm:
                                    rc_norm = rc.replace("\r\n", "\n")
                                    if allow_mult:
                                        curr = curr_norm.replace(tc_norm, rc_norm)
                                    else:
                                        curr = curr_norm.replace(tc_norm, rc_norm, 1)
                                else:
                                    print(f"[Step {step_idx}] WARNING: targetContent not found in chunk for {rel}")
                        files_state[rel] = curr
                    else:
                        print(f"[Step {step_idx}] WARNING: {rel} not in files_state for multi_replace_file_content")
        except Exception as e:
            print(f"[Step {step_idx}] Error parsing: {e}")

print(f"\nReconstruction complete. Total files: {len(files_state)}")
for rel, content in sorted(files_state.items()):
    print(f"  {rel:40s} : {len(content)} chars, {len(content.splitlines())} lines")
    out_file = os.path.join(output_dir, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as out_f:
        out_f.write(content)
