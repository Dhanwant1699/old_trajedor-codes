import sys
from openai import OpenAI

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

print("Streaming test for deepseek-ai/deepseek-v4-flash-0731 on NVIDIA NIM...")
try:
    response = client.chat.completions.create(
        model="deepseek-ai/deepseek-v4-flash-0731",
        messages=[{"role": "user", "content": "Write a limerick about the wonders of GPU computing."}],
        temperature=1,
        top_p=0.95,
        max_tokens=1024,
        extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}},
        stream=True
    )

    reasoning_text = ""
    content_text = ""

    for chunk in response:
        delta = chunk.choices[0].delta
        r = getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None)
        if r:
            reasoning_text += r
        if delta.content:
            content_text += delta.content

    print("\n--- STREAMED REASONING ---")
    print(reasoning_text)
    print("\n--- STREAMED CONTENT ---")
    print(content_text)
    print("\n--- STATUS: STREAM SUCCESS ---")

except Exception as e:
    print(f"Stream Error: {e}")
