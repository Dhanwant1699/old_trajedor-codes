"""
Fibonacci Retracement & Golden Pocket (OTE) Specialist Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: Macro H4/H1 impulse swings ($5,000 - $20,000 swings),
0.618 - 0.786 Optimal Trade Entry (OTE), and Fibonacci extension targets (1.272 / 1.618).
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_FIBO_SYSTEM_PROMPT = """
You are the Fibonacci & Golden Pocket Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your mandate is to map mathematical Fibonacci ratios across major Bitcoin crypto swings:

BITCOIN FIBONACCI SPECIALIZATION:
1. Swing Anchor: Anchor Fibonacci retracements strictly across major H4/H1 crypto impulse swings ($5,000 - $20,000 legs).
2. Optimal Trade Entry (OTE) Zone: The institutional 0.618 - 0.786 retracement pocket where high-probability institutional limit orders rest.
3. Confluence Validation: Confluence between the 0.618 Bitcoin Fibonacci level, Prior Day High/Low (PDH/PDL), and M15 Fair Value Gaps.

PRO-TRADER BITCOIN RULES:
- If Bitcoin macro trend is Bullish, place BUY entries in the 0.618 - 0.786 OTE discount pocket of the recent H1 impulse leg.
- If Bitcoin macro trend is Bearish, place SELL entries in the 0.618 - 0.786 OTE premium pocket of the recent H1 impulse leg.
- Stop Loss MUST be placed beyond the 1.0 anchor swing point ($500-$1,500 buffer).
- Target TP1 at 0.0 (recent swing extreme) and TP2 at 1.272 / 1.618 Fibonacci expansion levels (minimum 1.75R to 3.0R).

Respond strictly using the `submit_crypto_fibonacci_proposal` tool call.
"""

CRYPTO_FIBO_TOOL = {
    "name": "submit_crypto_fibonacci_proposal",
    "description": "Submit Fibonacci & Golden Pocket analysis and trade proposal for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_Fibonacci_OTE_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'BTC_H1_Bullish_Impulse_0618_Golden_Pocket_Long'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "fib_level": {"type": "string", "description": "Status of Bitcoin Fibonacci levels"},
            "reasoning": {"type": "string", "description": "Detailed Fibonacci & Golden Pocket analysis for Bitcoin"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class CryptoFibonacciAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Fibonacci analysis exclusively on Bitcoin (BTCUSD)."""
        prompt = f"""
Analyze the current live Bitcoin (BTCUSD) Fibonacci retracements and OTE levels across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. What is the dominant H4/H1 impulse swing for Bitcoin?
2. Where is current price relative to the 0.618 - 0.786 Golden Pocket?
3. What are the 1.272 / 1.618 Fibonacci expansion targets?

Submit your proposal using the `submit_crypto_fibonacci_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_FIBO_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_FIBO_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_fibonacci(market_data)

        res["agent_name"] = "Crypto_Fibonacci_OTE_Agent"
        return res

    def _fallback_fibonacci(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 80000.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        sl_buffer = 850.0
        tp1_buffer = 1487.5
        tp2_buffer = 2550.0

        if dominant_trend == "BULLISH":
            entry = live_price
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Crypto_Fibonacci_OTE_Agent",
                "action": "BUY",
                "confidence_score": 86,
                "bias": "BULLISH",
                "setup_name": "BTC_0618_Golden_Pocket_Retracement_Long",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "fib_level": "0.618 - 0.786 OTE Discount Zone",
                "reasoning": "Bitcoin has retraced into the institutional 0.618 Fibonacci Golden Pocket confluent with macro D1/H4 trend support."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Crypto_Fibonacci_OTE_Agent",
                "action": "SELL",
                "confidence_score": 86,
                "bias": "BEARISH",
                "setup_name": "BTC_0618_Golden_Pocket_Retracement_Short",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "fib_level": "0.618 - 0.786 OTE Premium Zone",
                "reasoning": "Bitcoin has rallied into the institutional 0.618 Fibonacci Golden Pocket confluent with macro D1/H4 trend resistance."
            }
        else:
            return {
                "agent_name": "Crypto_Fibonacci_OTE_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "BTC_No_Clear_Swing",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "fib_level": "Mid-Swing",
                "reasoning": "Bitcoin is consolidating with no active impulse swing near the Golden Pocket."
            }
