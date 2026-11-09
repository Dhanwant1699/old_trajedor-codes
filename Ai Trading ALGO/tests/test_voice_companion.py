import sys
from pathlib import Path
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.voice_companion_agent import BullionVoiceCompanionAgent

def test_companion():
    agent = BullionVoiceCompanionAgent()
    
    mock_payload = {
        "symbols": {
            "XAUUSD": {
                "name": "GOLD (XAUUSD)",
                "symbol": "XAUUSD",
                "price": "4,359.50",
                "spread": "18.0 pts",
                "master_action": "BUY",
                "quorum_score": 92,
                "entry_zone": "4,357.50 - 4,359.50",
                "stop_loss": 4348.80,
                "take_profit_1": 4375.50,
                "take_profit_2": 4387.60,
                "setup_status": "IN_TRADE",
                "debate_summary": "Strong Bullish 5-Minute (M5) Trend Continuation on Gold above EMA 9/21 support.",
                "open_positions": [
                    {
                        "ticket": 58513584508,
                        "type": "BUY",
                        "volume": 0.03,
                        "price_open": 4364.05,
                        "sl": 4353.56,
                        "tp": 4380.23,
                        "profit": -10.50
                    }
                ],
                "agents": [
                    {"name": "SMC & ICT Specialist", "action": "BUY", "confidence": 92, "thought": "Bullish liquidity sweep verified above discount order block."},
                    {"name": "Trend & Momentum", "action": "BUY", "confidence": 88, "thought": "M15 EMA 9/21 aligned with H4 trend."}
                ]
            }
        },
        "balance": 5021.38,
        "equity": 5010.88,
        "total_floating_pnl": -10.50
    }

    print("\n--- Test 1: Fear / Panic Scenario (Drawdown anxiety) ---")
    res1 = agent.generate_response(
        user_query="Bhai thoda loss chal raha hai, mujhe tension ho rahi hai, trade cut kar du kya?",
        market_payload=mock_payload,
        user_language="hi"
    )
    print(f"Emotion: {res1['emotion']} | Badge: {res1['badge']}")
    print(f"Reply: {res1['reply']}\n")

    print("--- Test 2: Follow-up with Memory (Asking about target) ---")
    res2 = agent.generate_response(
        user_query="Aur iska target kahan tak expect kar rahe hain?",
        market_payload=mock_payload,
        user_language="hi"
    )
    print(f"Emotion: {res2['emotion']} | Badge: {res2['badge']}")
    print(f"Reply: {res2['reply']}\n")

    print("--- Test 3: Curiosity / Strategy Query ---")
    res3 = agent.generate_response(
        user_query="SMC agent ne kya setup identify kiya hai?",
        market_payload=mock_payload,
        user_language="hi"
    )
    print(f"Emotion: {res3['emotion']} | Badge: {res3['badge']}")
    print(f"Reply: {res3['reply']}\n")

if __name__ == "__main__":
    test_companion()
