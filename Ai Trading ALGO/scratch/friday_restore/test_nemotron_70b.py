import sys
from openai import OpenAI

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

print("Testing nvidia/llama-3.1-nemotron-70b-instruct...")
try:
    completion = client.chat.completions.create(
        model="nvidia/llama-3.1-nemotron-70b-instruct",
        messages=[{"role": "user", "content": "Write a limerick about Gold trading in 5 lines."}],
        temperature=0.5,
        max_tokens=250,
        stream=False
    )
    print("--- NEMOTRON RESPONSE ---")
    print(completion.choices[0].message.content)
    print("--- STATUS: SUCCESS ---")
except Exception as e:
    print("Error:", e)
