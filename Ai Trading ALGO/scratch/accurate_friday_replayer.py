import os
import json
import re
import sys

transcript_path = r"C:\Users\Golu\.gemini\antigravity-ide\brain\0bd77b67-b9b6-4781-ac9c-a2075dc38501\.system_generated\logs\transcript_full.jsonl"
output_dir = r"D:\Ai Trading ALGO\scratch\friday_restore"

os.makedirs(output_dir, exist_ok=True)

CUTOFF_STEP = 5800

files_state = {}

def normalize_rel_path(p):
    p = p.replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    p = re.sub(r'^[a-zA-Z]:[/]+', '', p)
    p = re.sub(r'^ai\s+trading\s+algo[/]+', '', p, flags=re.IGNORECASE)
    p = p.lstrip('/')
    return p

def do_replace(content, start_line, end_line, target, replacement):
    # Normalize newlines
    lines = content.split("\n")
    target_lines = target.split("\n")
    # If start_line and end_line are provided
    if start_line is not None and end_line is not None and 1 <= start_line <= len(lines):
        # Range is 1-indexed inclusive
        # Search target within [start_line-1 : end_line]
        s_idx = max(0, start_line - 1)
        e_idx = min(len(lines), end_line)
        sub_text = "\n".join(lines[s_idx:e_idx])
        if target in sub_text:
            sub_replaced = sub_text.replace(target, replacement, 1)
            new_lines = lines[:s_idx] + sub_replaced.split("\n") + lines[e_idx:]
            return "\n".join(new_lines), True
        
        # Try stripping \r
        target_clean = target.replace("\r", "")
        sub_text_clean = sub_text.replace("\r", "")
        if target_clean in sub_text_clean:
            rep_clean = replacement.replace("\r", "")
            sub_replaced = sub_text_clean.replace(target_clean, rep_clean, 1)
            new_lines = [l.replace("\r", "") for l in lines[:s_idx]] + sub_replaced.split("\n") + [l.replace("\r", "") for l in lines[e_idx:]]
            return "\n".join(new_lines), True

    # Fallback: global search
    if target in content:
        return content.replace(target, replacement, 1), True
    
    t_clean = target.replace("\r", "")
    c_clean = content.replace("\r", "")
    if t_clean in c_clean:
        r_clean = replacement.replace("\r", "")
        return c_clean.replace(t_clean, r_clean, 1), True
    
    # Strip whitespace line by line comparison
    # If target matches ignoring trailing whitespace
    return content, False

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
                    target = normalize_rel_path(args.get("TargetFile", ""))
                    content = args.get("CodeContent", "")
                    if target.startswith("scratch/") or ".gemini" in target:
                        continue
                    files_state[target] = content.replace("\r\n", "\n")
                elif fn == "replace_file_content":
                    target = normalize_rel_path(args.get("TargetFile", ""))
                    if target.startswith("scratch/") or ".gemini" in target:
                        continue
                    tc = args.get("TargetContent", "")
                    rc = args.get("ReplacementContent", "")
                    sl = args.get("StartLine")
                    el = args.get("EndLine")
                    
                    cand = target
                    if cand not in files_state:
                        if "core/" + cand in files_state:
                            cand = "core/" + cand
                        elif cand.startswith("core/") and cand[5:] in files_state:
                            cand = cand[5:]
                    
                    if cand in files_state:
                        new_content, ok = do_replace(files_state[cand], sl, el, tc, rc)
                        if ok:
                            files_state[cand] = new_content
                        else:
                            print(f"[Step {step_idx}] FAILED replace in {cand} (lines {sl}-{el})")
                    else:
                        print(f"[Step {step_idx}] NOT FOUND: {cand}")
                elif fn == "multi_replace_file_content":
                    target = normalize_rel_path(args.get("TargetFile", ""))
                    if target.startswith("scratch/") or ".gemini" in target:
                        continue
                    chunks = args.get("ReplacementChunks", [])
                    cand = target
                    if cand not in files_state:
                        if "core/" + cand in files_state:
                            cand = "core/" + cand
                        elif cand.startswith("core/") and cand[5:] in files_state:
                            cand = cand[5:]
                    if cand in files_state:
                        curr = files_state[cand]
                        all_ok = True
                        for ch in chunks:
                            tc = ch.get("TargetContent", "")
                            rc = ch.get("ReplacementContent", "")
                            sl = ch.get("StartLine")
                            el = ch.get("EndLine")
                            curr, ok = do_replace(curr, sl, el, tc, rc)
                            if not ok:
                                print(f"[Step {step_idx}] FAILED chunk in {cand} (lines {sl}-{el})")
                                all_ok = False
                        files_state[cand] = curr
                    else:
                        print(f"[Step {step_idx}] NOT FOUND: {cand}")
        except Exception as e:
            pass

print(f"\nTotal files reconstructed: {len(files_state)}")
for rel, content in sorted(files_state.items()):
    out_file = os.path.join(output_dir, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as out_f:
        out_f.write(content)
