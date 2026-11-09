with open("docs/dashboard.html", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "three" in line.lower() or "initjarvisglobe" in line.lower():
            print(f"Line {idx+1}: {line.strip()[:120]}")
