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
    # Normalize \r\n to \n
    c_norm = content.replace("\r\n", "\n")
    t_norm = target.replace("\r\n", "\n")
    r_norm = replacement.replace("\r\n", "\n")
    
    lines = c_norm.split("\n")
    
    if start_line is not None and end_line is not None and 1 <= start_line <= len(lines):
        s_idx = max(0, start_line - 1)
        e_idx = min(len(lines), end_line)
        sub_text = "\n".join(lines[s_idx:e_idx])
        if t_norm in sub_text:
            sub_replaced = sub_text.replace(t_norm, r_norm, 1)
            new_lines = lines[:s_idx] + sub_replaced.split("\n") + lines[e_idx:]
            return "\n".join(new_lines), True

    # Try searching entire text
    if t_norm in c_norm:
        return c_norm.replace(t_norm, r_norm, 1), True
    
    # Try fuzzy line matching (ignore trailing whitespace per line)
    t_lines = [l.rstrip() for l in t_norm.split("\n")]
    # Find matching block in lines
    for i in range(len(lines) - len(t_lines) + 1):
        if [lines[i+j].rstrip() for j in range(len(t_lines))] == t_lines:
            # Replace lines[i : i+len(t_lines)] with r_norm.split("\n")
            new_lines = lines[:i] + r_norm.split("\n") + lines[i+len(t_lines):]
            return "\n".join(new_lines), True
            
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
                
                # Check organize_workspace trigger
                if fn == "run_command":
                    cmd = args.get("CommandLine", "")
                    if "organize_workspace.py" in cmd:
                        # Copy engines to core/
                        for e in ["data_engine.py", "news_engine.py", "execution_engine.py", "risk_manager.py"]:
                            if e in files_state:
                                files_state["core/" + e] = files_state[e]
                        # Copy tests to tests/
                        for t in ["test_multi_agent.py", "test_engines.py", "test_nvidia_live.py"]:
                            if t in files_state:
                                files_state["tests/" + t] = files_state[t]
                        if "test_all_nvidia_parallel.py" in files_state:
                            files_state["tests/benchmark_models.py"] = files_state["test_all_nvidia_parallel.py"]
                        files_state["tests/__init__.py"] = '"""Test suites for AI Trading ALGO."""\n'
                        # Copy docs to docs/
                        for d in ["ARCHITECTURE_FLOW_DIAGRAM.md", "HOW_AGENTS_WORK_AND_COST.md", "flow_diagram.html"]:
                            if d in files_state:
                                files_state["docs/" + d] = files_state[d]
                        # Remove scratch
                        cleanup = [
                            "bench_log.txt", "bench_sync.py", "benchmark_nvidia_models.py",
                            "test_deepseek_nvidia.py", "test_nvidia_rest.py", "test_top_models.py",
                            "test_user_snippet.py", "test_user_snippet_stream.py", "test_nemotron_70b.py",
                            "run_user_nvidia_code.py", "list_nvidia_models.py", "available_nvidia_models.json",
                            "active_nvidia_models.json", "nvidia_result.txt", "payload.json",
                            "payload_fast.json", "rest_result.json", "test_all_nvidia_parallel.py",
                            "claude_trader.py", "data_engine.py", "news_engine.py", "execution_engine.py",
                            "risk_manager.py", "test_engines.py", "test_multi_agent.py", "test_nvidia_live.py",
                            "ARCHITECTURE_FLOW_DIAGRAM.md", "HOW_AGENTS_WORK_AND_COST.md", "flow_diagram.html",
                            "organize_workspace.py"
                        ]
                        for cl in cleanup:
                            files_state.pop(cl, None)
                        continue

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
                    
                    if target in files_state:
                        new_content, ok = do_replace(files_state[target], sl, el, tc, rc)
                        if ok:
                            files_state[target] = new_content
                        else:
                            print(f"[Step {step_idx}] FAILED replace in {target} (lines {sl}-{el})")
                    else:
                        print(f"[Step {step_idx}] NOT FOUND: {target}")
                elif fn == "multi_replace_file_content":
                    target = normalize_rel_path(args.get("TargetFile", ""))
                    if target.startswith("scratch/") or ".gemini" in target:
                        continue
                    chunks = args.get("ReplacementChunks", [])
                    if target in files_state:
                        curr = files_state[target]
                        all_ok = True
                        for ch in chunks:
                            tc = ch.get("TargetContent", "")
                            rc = ch.get("ReplacementContent", "")
                            sl = ch.get("StartLine")
                            el = ch.get("EndLine")
                            curr, ok = do_replace(curr, sl, el, tc, rc)
                            if not ok:
                                print(f"[Step {step_idx}] FAILED chunk in {target} (lines {sl}-{el})")
                                all_ok = False
                        files_state[target] = curr
                    else:
                        print(f"[Step {step_idx}] NOT FOUND: {target}")
        except Exception as e:
            pass

print(f"\nTotal files reconstructed: {len(files_state)}")
for rel, content in sorted(files_state.items()):
    out_file = os.path.join(output_dir, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as out_f:
        out_f.write(content)
