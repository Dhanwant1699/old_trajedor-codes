import requests
import json

headers = {
    "Authorization": "Bearer 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",
    "Accept": "application/json"
}

try:
    print("Fetching models list from NVIDIA NIM...")
    r = requests.get("https://integrate.api.nvidia.com/v1/models", headers=headers, timeout=15)
    print("Status:", r.status_code)
    data = r.json()
    model_ids = [m["id"] for m in data.get("data", [])]
    print(f"Total models available: {len(model_ids)}")
    with open("d:/Ai Trading ALGO/available_nvidia_models.json", "w", encoding="utf-8") as f:
        json.dump(model_ids, f, indent=2)
    print("Top models:", model_ids[:15])
except Exception as e:
    print("Error:", e)
