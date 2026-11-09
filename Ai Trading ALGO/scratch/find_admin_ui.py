with open("docs/dashboard.html", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "/api/admin" in line or "switchAsset('ACCOUNTS')" in line or "switchAsset('ADMIN')" in line or "renderAccounts" in line:
            print(f"Line {idx+1}: {line.strip()[:140]}")
