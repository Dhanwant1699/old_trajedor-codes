import sys
import os
import json
import time

log_file = "d:/Ai Trading ALGO/bench_log.txt"

def log(msg):
    print(msg, flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

with open(log_file, "w", encoding="utf-8") as f:
    f.write("BENCHMARK STARTED\n")

from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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",
    timeout=10.0
)

test_models = [
    "deepseek-ai/deepseek-v4-flash-0731",
    "mistralai/mistral-large-2-instruct",
    "google/gemma-3-12b-it",
    "writer/palmyra-fin-70b-32k",
    "01-ai/yi-large"
]

for m in test_models:
    log(f"Testing {m}...")
    start_t = time.time()
    try:
        kwargs = {
            "model": m,
            "messages": [{"role": "user", "content": "Ping"}],
            "max_tokens": 15
        }
        res = client.chat.completions.create(**kwargs)
        dur = round(time.time() - start_t, 2)
        content = res.choices[0].message.content.strip()
        log(f"SUCCESS [{dur}s]: {m} -> {content}")
    except Exception as e:
        dur = round(time.time() - start_t, 2)
        log(f"FAILED [{dur}s]: {m} -> {str(e)[:80]}")

log("BENCHMARK COMPLETE")
