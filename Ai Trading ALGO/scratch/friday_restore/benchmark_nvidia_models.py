import sys
import json
from openai import OpenAI

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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",
    timeout=15.0
)

with open("d:/Ai Trading ALGO/available_nvidia_models.json", "r", encoding="utf-8") as f:
    models = json.load(f)

# Priority models to test
candidates = [
    "deepseek-ai/deepseek-v4-flash-0731",
    "deepseek-ai/deepseek-coder-6.7b-instruct",
    "mistralai/mistral-large-2-instruct",
    "mistralai/mixtral-8x22b-v0.1",
    "mistralai/mistral-7b-instruct-v0.3",
    "writer/palmyra-fin-70b-32k",
    "google/gemma-3-12b-it",
    "google/gemma-3-4b-it",
    "z-ai/glm-5.3-flash",
    "ibm/granite-3.0-8b-instruct",
    "openai/gpt-oss-20b",
    "01-ai/yi-large"
]

working = []
print("Testing candidate models on NVIDIA NIM...")
for m in candidates:
    try:
        kwargs = {
            "model": m,
            "messages": [{"role": "user", "content": "Respond in 3 words: Ready to trade."}],
            "max_tokens": 30,
            "temperature": 0.5
        }
        if "deepseek-v4" in m:
            kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": False}}
        res = client.chat.completions.create(**kwargs)
        reply = res.choices[0].message.content.strip()
        print(f"[OK] {m} -> {reply}")
        working.append(m)
    except Exception as e:
        err_msg = str(e)
        if "404" in err_msg:
            status = "404 Not Found"
        elif "410" in err_msg:
            status = "410 Deprecated"
        elif "400" in err_msg:
            status = f"400 Bad Request: {err_msg[:60]}"
        elif "timed out" in err_msg.lower():
            status = "Timeout"
        else:
            status = err_msg[:60]
        print(f"[FAIL] {m} -> {status}")

print("\n--- WORKING MODELS ---")
for w in working:
    print(f" - {w}")
