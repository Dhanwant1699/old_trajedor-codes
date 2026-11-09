import os

friday_dir = r"D:\Ai Trading ALGO\scratch\friday_restore"
current_dir = r"D:\Ai Trading ALGO"

friday_files = []
for root, dirs, files in os.walk(friday_dir):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, friday_dir).replace("\\", "/")
        friday_files.append(rel)

current_files = []
for root, dirs, files in os.walk(current_dir):
    if any(ignore in root for ignore in [".venv", ".git", "__pycache__", "scratch"]):
        continue
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, current_dir).replace("\\", "/")
        current_files.append(rel)

print(f"Total Friday files: {len(friday_files)}")
print(f"Total Current files: {len(current_files)}")

print("\n--- Files in Friday: ---")
for f in sorted(friday_files):
    print(f"  {f}")

print("\n--- Files currently present that were NOT in Friday (Added since Saturday): ---")
for f in sorted(set(current_files) - set(friday_files)):
    print(f"  + {f}")

print("\n--- Files in Friday that are currently missing: ---")
for f in sorted(set(friday_files) - set(current_files)):
    print(f"  - {f}")
