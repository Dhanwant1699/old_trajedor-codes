import os
import shutil
import glob

base = "d:/Ai Trading ALGO"

# 1. Ensure directories exist
for d in ["core", "tests", "docs", "logs"]:
    os.makedirs(os.path.join(base, d), exist_ok=True)

# 2. Copy/Move engines to core/
engines = ["data_engine.py", "news_engine.py", "execution_engine.py", "risk_manager.py"]
for f in engines:
    src = os.path.join(base, f)
    dst = os.path.join(base, "core", f)
    if os.path.exists(src):
        shutil.copy2(src, dst)

# 3. Copy tests to tests/
test_files = ["test_multi_agent.py", "test_engines.py", "test_nvidia_live.py"]
for f in test_files:
    src = os.path.join(base, f)
    dst = os.path.join(base, "tests", f)
    if os.path.exists(src):
        shutil.copy2(src, dst)

if os.path.exists(os.path.join(base, "test_all_nvidia_parallel.py")):
    shutil.copy2(os.path.join(base, "test_all_nvidia_parallel.py"), os.path.join(base, "tests", "benchmark_models.py"))

# Create tests/__init__.py
with open(os.path.join(base, "tests", "__init__.py"), "w", encoding="utf-8") as f:
    f.write('"""Test suites for AI Trading ALGO."""\n')

# Create logs/.gitkeep
with open(os.path.join(base, "logs", ".gitkeep"), "w", encoding="utf-8") as f:
    f.write('')

# 4. Copy docs to docs/
doc_files = ["ARCHITECTURE_FLOW_DIAGRAM.md", "HOW_AGENTS_WORK_AND_COST.md", "flow_diagram.html"]
for f in doc_files:
    src = os.path.join(base, f)
    dst = os.path.join(base, "docs", f)
    if os.path.exists(src):
        shutil.copy2(src, dst)

# 5. Delete scratch & temporary test artifacts from root
cleanup_files = [
    "bench_log.txt", "bench_sync.py", "benchmark_nvidia_models.py",
    "test_deepseek_nvidia.py", "test_nvidia_rest.py", "test_top_models.py",
    "test_user_snippet.py", "test_user_snippet_stream.py", "test_nemotron_70b.py",
    "run_user_nvidia_code.py", "list_nvidia_models.py", "available_nvidia_models.json",
    "active_nvidia_models.json", "nvidia_result.txt", "payload.json",
    "payload_fast.json", "rest_result.json", "test_all_nvidia_parallel.py",
    "claude_trader.py" # old monolithic file replaced by multi-agent system
]

for f in cleanup_files:
    p = os.path.join(base, f)
    if os.path.exists(p):
        try:
            os.remove(p)
            print(f"Removed scratch: {f}")
        except Exception as e:
            print(f"Error removing {f}: {e}")

print("Workspace hierarchy organized successfully!")
