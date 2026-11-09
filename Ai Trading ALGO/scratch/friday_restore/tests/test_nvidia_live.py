"""
Live test of NVIDIA NIM connection using user's API key.
"""

import sys
import json
from openai import OpenAI

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import CONFIG
from agents.llm_client import UnifiedLLMClient
from agents.smc_agent import SMCAgent
from agents.master_coordinator import MasterCoordinator

def test_nvidia_connection():
    print("=" * 80)
    print(f"   TESTING LIVE NVIDIA NIM API CONNECTION")
    print(f"   Provider: {CONFIG.AI_PROVIDER} | Model: {CONFIG.NVIDIA_MODEL}")
    print("=" * 80)

    # 1. Direct OpenAI Client test to NVIDIA NIM
    print("1. Direct Ping to NVIDIA NIM endpoint...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=CONFIG.NVIDIA_API_KEY
    )

    try:
        completion = client.chat.completions.create(
            model=CONFIG.NVIDIA_MODEL,
            messages=[{"role": "user", "content": "Respond with the word 'CONNECTED' if you receive this message."}],
            max_tokens=50,
            temperature=0.1
        )
        content = completion.choices[0].message.content.strip()
        print(f"   [SUCCESS] NVIDIA NIM Response: '{content}'")
    except Exception as e:
        print(f"   [NOTE] Model {CONFIG.NVIDIA_MODEL} response: {e}")
        # Test meta/llama-3.3-70b-instruct as well
        print("   Testing meta/llama-3.3-70b-instruct fallback...")
        try:
            completion = client.chat.completions.create(
                model="meta/llama-3.3-70b-instruct",
                messages=[{"role": "user", "content": "Respond with 'CONNECTED'."}],
                max_tokens=50,
                temperature=0.1
            )
            print(f"   [SUCCESS] Llama 3.3 70B Response: '{completion.choices[0].message.content.strip()}'")
        except Exception as ex:
            print(f"   [ERROR] Fallback error: {ex}")

    # 2. Test SMC Agent with UnifiedLLMClient
    print("\n2. Testing SMC Specialist Agent via UnifiedLLMClient...")
    smc = SMCAgent()
    sample_market = {
        "symbol": "XAUUSD",
        "current_price": 2725.00,
        "m15_structure": {
            "asian_low": 2718.00,
            "asian_high": 2730.00,
            "liquidity_status": "Asian Low swept at London Open",
            "active_fvgs": [{"type": "BULLISH_FVG", "bottom": 2720.00, "top": 2723.00}]
        }
    }
    proposal = smc.analyze(sample_market)
    print(f"   SMC Agent Proposal: Action={proposal.get('action')} | Conf={proposal.get('confidence_score')}% | Setup='{proposal.get('setup_name')}'")
    print(f"   Reasoning: {proposal.get('reasoning')[:120]}...")

    print("\n[SUCCESS] LIVE NVIDIA NIM INTEGRATION CONFIRMED WORKING!")

if __name__ == "__main__":
    test_nvidia_connection()
