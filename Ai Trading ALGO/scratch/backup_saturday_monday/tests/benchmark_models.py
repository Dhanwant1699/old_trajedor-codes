import concurrent.futures
import requests
import json
import time

headers = {
    "Authorization": "Bearer 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",
    "Content-Type": "application/json"
}

with open("d:/Ai Trading ALGO/available_nvidia_models.json", "r", encoding="utf-8") as f:
    all_models = json.load(f)

def test_model(model_name):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
    }
    t0 = time.time()
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=12)
        dur = round(time.time() - t0, 2)
        if r.status_code == 200:
            res_json = r.json()
            reply = res_json["choices"][0]["message"]["content"].strip()
            return {"model": model_name, "status": 200, "reply": reply, "duration": dur}
        else:
            return {"model": model_name, "status": r.status_code, "error": r.text[:80], "duration": dur}
    except Exception as e:
        dur = round(time.time() - t0, 2)
        return {"model": model_name, "status": "EXC", "error": str(e)[:60], "duration": dur}

print(f"Testing {len(all_models)} NVIDIA models in parallel...")
results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
    futures = {executor.submit(test_model, m): m for m in all_models}
    for future in concurrent.futures.as_completed(futures):
        res = future.result()
        results.append(res)
        if res["status"] == 200:
            print(f"[ACTIVE 200 OK] {res['model']} ({res['duration']}s): {res['reply']}", flush=True)

active_models = [r for r in results if r["status"] == 200]
print(f"\n==========================================")
print(f"TOTAL ACTIVE MODELS: {len(active_models)} / {len(all_models)}")
for a in sorted(active_models, key=lambda x: x["duration"]):
    print(f"  * {a['model']} (Latency: {a['duration']}s)")

with open("d:/Ai Trading ALGO/active_nvidia_models.json", "w", encoding="utf-8") as f:
    json.dump(active_models, f, indent=2)
