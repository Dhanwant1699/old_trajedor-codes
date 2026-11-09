import requests
import json

url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {
    "Authorization": "Bearer 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",
    "Content-Type": "application/json"
}
payload = {
    "model": "deepseek-ai/deepseek-v4-flash-0731",
    "messages": [{"role": "user", "content": "Write a limerick about the wonders of GPU computing."}],
    "temperature": 1,
    "top_p": 0.95,
    "max_tokens": 512,
    "chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"},
    "stream": False
}

try:
    print("Sending direct REST request to NVIDIA NIM...")
    res = requests.post(url, headers=headers, json=payload, timeout=60)
    print("Status code:", res.status_code)
    try:
        data = res.json()
        with open("d:/Ai Trading ALGO/rest_result.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("SUCCESS: written to rest_result.json")
    except Exception:
        print("Response text:", res.text)
except Exception as e:
    print("ERROR:", e)
