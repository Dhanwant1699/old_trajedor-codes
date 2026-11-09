import sys
from openai import OpenAI

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

print("Testing deepseek-ai/deepseek-v4-flash-0731 on NVIDIA NIM...")
try:
    completion = client.chat.completions.create(
        model="deepseek-ai/deepseek-v4-flash-0731",
        messages=[{"role": "user", "content": "Write a limerick about the wonders of GPU computing."}],
        temperature=1,
        top_p=0.95,
        max_tokens=1024,
        extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}},
        stream=False
    )

    reasoning = getattr(completion.choices[0].message, "reasoning", None) or getattr(completion.choices[0].message, "reasoning_content", None)
    if reasoning:
        print("\n--- REASONING / THINKING ---")
        print(reasoning)
    print("\n--- LIMERICK ---")
    print(completion.choices[0].message.content)
    print("\n--- STATUS: SUCCESS ---")

except Exception as e:
    print(f"Error: {e}")
