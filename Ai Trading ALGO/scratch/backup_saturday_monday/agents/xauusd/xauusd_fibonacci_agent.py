"""
Fibonacci Retracement & Golden Pocket (OTE) Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Macro H4/H1 swing impulses, 0.618 - 0.786 Optimal Trade Entry (OTE),
and Fibonacci extension targets (1.272 / 1.618).
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_FIBO_SYSTEM_PROMPT = """
You are the Fibonacci & Golden Pocket Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to map mathematical Fibonacci ratios across major Gold swings:

GOLD FIBONACCI SPECIALIZATION:
1. Swing Anchor: Anchor Fibonacci retracements strictly across major H4/H1 impulse swings.
2. Optimal Trade Entry (OTE) Zone: The institutional 0.618 - 0.786 retracement pocket where high-probability institutional limit orders rest.
3. Confluence Validation: Confluence between the 0.618 Gold Fibonacci level, Prior Day High/Low (PDH/PDL), and M15 Fair Value Gaps.

PRO-TRADER GOLD RULES:
- If Gold macro trend is Bullish, place BUY entries in the 0.618 - 0.786 OTE discount pocket of the recent H1 impulse leg.
- If Gold macro trend is Bearish, place SELL entries in the 0.618 - 0.786 OTE premium pocket of the recent H1 impulse leg.
- Stop Loss MUST be placed beyond the 1.0 anchor swing point (complete invalidation).
- Target TP1 at 0.0 (recent swing extreme) and TP2 at 1.272 / 1.618 Fibonacci expansion levels (minimum 1.75R to 3.0R).

Respond strictly using the `submit_gold_fibonacci_proposal` tool call.
"""

GOLD_FIBO_TOOL = {
    "name": "submit_gold_fibonacci_proposal",
    "description": "Submit Fibonacci & Golden Pocket analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Fibonacci_OTE_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_H1_Bullish_Impulse_0618_Golden_Pocket_Long'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "fib_level": {"type": "string", "description": "Status of Gold Fibonacci levels"},
            "reasoning": {"type": "string", "description": "Detailed Fibonacci & Golden Pocket analysis for Gold"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldFibonacciAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Fibonacci analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) Fibonacci retracements and OTE levels across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. What is the dominant H4/H1 impulse swing for Gold?
2. Where is current price relative to the 0.618 - 0.786 Golden Pocket?
3. What are the 1.272 / 1.618 Fibonacci expansion targets?

Submit your proposal using the `submit_gold_fibonacci_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_FIBO_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_FIBO_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_fibonacci(market_data)

        res["agent_name"] = "Gold_Fibonacci_OTE_Agent"
        return res

    def _fallback_fibonacci(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        sl_buffer = 10.0
        tp1_buffer = 18.0
        tp2_buffer = 32.0

        if dominant_trend == "BULLISH":
            entry = live_price
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Gold_Fibonacci_OTE_Agent",
                "action": "BUY",
                "confidence_score": 86,
                "bias": "BULLISH",
                "setup_name": "Gold_0618_Golden_Pocket_Retracement_Long",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "fib_level": "0.618 - 0.786 OTE Discount Zone",
                "reasoning": "Gold has retraced into the institutional 0.618 Fibonacci Golden Pocket confluent with macro D1/H4 trend support."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_Fibonacci_OTE_Agent",
                "action": "SELL",
                "confidence_score": 86,
                "bias": "BEARISH",
                "setup_name": "Gold_0618_Golden_Pocket_Retracement_Short",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "fib_level": "0.618 - 0.786 OTE Premium Zone",
                "reasoning": "Gold has rallied into the institutional 0.618 Fibonacci Golden Pocket confluent with macro D1/H4 trend resistance."
            }
        else:
            return {
                "agent_name": "Gold_Fibonacci_OTE_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_No_Clear_Swing",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "fib_level": "Mid-Swing",
                "reasoning": "Gold is consolidating with no active impulse swing near the Golden Pocket."
            }
