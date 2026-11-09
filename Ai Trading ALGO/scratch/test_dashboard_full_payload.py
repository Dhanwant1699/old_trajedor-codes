import urllib.request
import json
import subprocess
import time
import sys

# Start dashboard server on port 1119 in background
proc = subprocess.Popen([sys.executable, "launch_dashboard.py", "1119"])

try:
    print("Waiting 6 seconds for background telemetry thread to warm up MT5 cache...")
    time.sleep(6)
    # Check /api/status with generous timeout for initial cold MT5 startup
    req = urllib.request.Request("http://localhost:1119/api/status")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("[OK] Dashboard /api/status responded successfully!")
        print("  - Symbols:", list(data.get("symbols", {}).keys()))
        print("  - Accounts:", list(data.get("accounts", {}).keys()))
        
        dossier = data.get("market_research_dossier")
        if dossier:
            print("[OK] market_research_dossier present:")
            print("  - Threat Level:", dossier.get("shock_threat_level"))
            print("  - Action Clearance:", dossier.get("institutional_action_clearance"))
            macro = dossier.get("macro_suite", {})
            if macro:
                print("[OK] macro_suite present:")
                print("  - DXY:", macro.get("dxy", {}).get("price"))
                print("  - US 10Y:", macro.get("us10y_yield", {}).get("price"))
                print("  - Oil:", macro.get("crude_oil", {}).get("price"))
                print("  - Breaking News items:", len(macro.get("breaking_news", [])))
            else:
                print("[WARN] macro_suite is missing from dossier")
        else:
            print("[WARN] market_research_dossier missing from status payload")
            
    # Check GET /
    req_html = urllib.request.Request("http://localhost:1119/")
    with urllib.request.urlopen(req_html, timeout=5) as resp:
        html = resp.read().decode("utf-8")
        print(f"[OK] Root GET / responded with {len(html)} bytes of HTML!")
        if "macro-threat-radar-container" in html:
            print("[OK] macro-threat-radar-container found in served HTML!")
finally:
    proc.terminate()
    proc.wait()
    print("[OK] Test server stopped cleanly.")
