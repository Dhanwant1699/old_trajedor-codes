import sys
from openai import OpenAI

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

models_to_test = [
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nvidia/nemotron-3-super-120b-a12b",
    "meta/llama-3.2-11b-vision-instruct"
]

for m in models_to_test:
    print(f"\n==========================================")
    print(f"Testing: {m}")
    try:
        completion = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "Write a limerick about the wonders of GPU computing."}],
            temperature=0.7,
            max_tokens=250
        )
        print("=== RESPONSE ===")
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")
