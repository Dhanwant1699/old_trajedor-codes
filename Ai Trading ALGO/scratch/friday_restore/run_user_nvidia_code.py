import sys
import os
from openai import OpenAI

out_file = "d:/Ai Trading ALGO/nvidia_result.txt"

try:
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("STARTING CALL...\n")
    
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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"
    )

    completion = client.chat.completions.create(
        model="deepseek-ai/deepseek-v4-flash-0731",
        messages=[{"role": "user", "content": "Write a limerick about the wonders of GPU computing."}],
        temperature=1,
        top_p=0.95,
        max_tokens=2048,
        extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}},
        stream=False
    )

    reasoning = getattr(completion.choices[0].message, "reasoning", None) or getattr(completion.choices[0].message, "reasoning_content", None)
    content = completion.choices[0].message.content

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("=== REASONING ===\n")
        f.write(str(reasoning) + "\n\n")
        f.write("=== CONTENT ===\n")
        f.write(str(content) + "\n")
    print("FINISHED SUCCESSFULLY")

except Exception as e:
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"ERROR: {e}\n")
    print(f"FAILED: {e}")
