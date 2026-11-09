import time
from openai import OpenAI
from config import CONFIG

client = OpenAI(base_url='https://integrate.api.nvidia.com/v1', api_key=CONFIG.NVIDIA_API_KEY)
test_models = [
    'mistralai/mistral-7b-instruct-v0.3',
    'google/gemma-3-12b-it',
    'nv-mistralai/mistral-nemo-12b-instruct',
    'deepseek-ai/deepseek-v4-flash-0731'
]
prompt = (
    "You are Bullion AI, an Alexa-style Gold trading copilot. Reply in 1-2 sharp, friendly, natural Hinglish sentences.\n"
    "Live Data: Gold is at $4,364.97, open buy 0.03 lots with +2.40 EUR profit, SL at 4,353.56, TP at 4,380.23.\n\n"
    "User asked: 'Mera profit kitna chal raha hai?'"
)

for m in test_models:
    try:
        t0 = time.time()
        res = client.chat.completions.create(
            model=m,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=80,
            temperature=0.2
        )
        dt = round(time.time()-t0, 2)
        print(f"=== {m} ({dt}s) ===")
        print(res.choices[0].message.content.strip())
    except Exception as e:
        print(f"=== {m} ERROR: {e}")
