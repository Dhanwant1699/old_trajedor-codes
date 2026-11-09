import re
import subprocess
import os

with open("docs/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# Extract all <script> blocks
scripts = re.findall(r"<script>(.*?)</script>", content, re.DOTALL)
print(f"Found {len(scripts)} script blocks.")

for idx, sc in enumerate(scripts):
    js_filename = f"scratch/script_{idx}.js"
    with open(js_filename, "w", encoding="utf-8") as jf:
        jf.write(sc)
    print(f"Saved {js_filename} ({len(sc.splitlines())} lines)")
    
    # Try checking with node if available
    try:
        res = subprocess.run(["node", "--check", js_filename], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  [OK] Node.js syntax check passed for script_{idx}.js")
        else:
            print(f"  [FAIL] Node.js syntax error in script_{idx}.js:")
            print(res.stderr)
    except Exception as e:
        print(f"  Node check unavailable: {e}")
