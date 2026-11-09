import os
import json
import glob
from datetime import datetime

brain_dir = r"C:\Users\Golu\.gemini\antigravity-ide\brain"
conversations = []

for cdir in os.listdir(brain_dir):
    cpath = os.path.join(brain_dir, cdir)
    if os.path.isdir(cpath):
        mtime = os.path.getmtime(cpath)
        conversations.append((mtime, cdir, cpath))

conversations.sort(reverse=True)

print("Recent Conversations in Brain:")
for mtime, cdir, cpath in conversations[:15]:
    dt = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{dt}] {cdir}")
    # Check if there is transcript
    tpath = os.path.join(cpath, ".system_generated", "logs", "transcript.jsonl")
    if os.path.exists(tpath):
        size = os.path.getsize(tpath)
        print(f"    transcript.jsonl ({size} bytes)")
