"""
Fibonacci & Golden Pocket (OTE) Specialist Agent for XAUUSD.
Analyzes mathematical impulse swing retracements (0.50, 0.618, 0.786 OTE) and Fibonacci extensions (1.272, 1.618).
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG


FIBO_SYSTEM_PROMPT = """
You are the Fibonacci & Golden Pocket Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade mathematical Fibonacci retracement zones and target expansion extensions:
1. Golden Pocket / OTE (Optimal Trade Entry): 0.618 to 0.786 retracement of a major impulsive swing.
2. 50% Equilibrium: Retracement to fair value median of the swing.
3. Extension Targets: 1.272 extension (TP1) and 1.618 Golden Extension (TP2).

RULES:
- Propose BUY when price completes a bullish impulse and pulls back precisely into the 0.618 - 0.786 Golden Pocket with bullish confirmation.
- Propose SELL when price completes a bearish impulse and retraces into the 0.618 - 0.786 Golden Pocket with bearish confirmation.
- Stop Loss MUST be placed beyond the 1.0 invalidation swing origin (or 0.886 level).
- Target TP1 at 1.272 extension and TP2 at 1.618 extension (minimum 1.5R to 2.5R+).
- If price is in no-man's land (< 0.382 or beyond 1.0), output 'HOLD'.
- Minimum confidence score >= 70.

Respond strictly using the `submit_fibonacci_proposal` tool call.
"""

FIBO_TOOL = {
    "name": "submit_fibonacci_proposal",
    "description": "Submit Fibonacci & Golden Pocket analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Fibonacci_OTE_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Bullish_0.618_Golden_Pocket_Pullback'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "fib_level_tested": {"type": "string", "description": "Fibonacci ratio tested (e.g. '0.618 Golden Pocket')"},
            "reasoning": {"type": "string", "description": "Detailed Fibonacci and extension analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class FibonacciAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Fibonacci & Golden Pocket OTE analysis."""
        prompt = f"""
Analyze the live XAUUSD market data strictly through Fibonacci & Golden Pocket principles:

{json.dumps(market_data, indent=2)}

Check:
1. What is the current Fibonacci swing impulse?
2. Has price pulled back into the 0.618 - 0.786 Golden Pocket OTE zone?
3. Where are the 1.272 and 1.618 extension target levels?

Submit your proposal using the `submit_fibonacci_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=FIBO_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=FIBO_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res:
            return self._fallback_fibonacci(market_data)
        res["agent_name"] = "Fibonacci_OTE_Agent"
        return res

    def _fallback_fibonacci(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        fib = struct.get("fibonacci_levels", {})
        trend = h1.get("trend_bias", "BULLISH")

        swing_high = float(fib.get("swing_high", live_price + 8.0) or (live_price + 8.0))
        swing_low = float(fib.get("swing_low", live_price - 8.0) or (live_price - 8.0))
        diff = max(0.1, swing_high - swing_low)
        rel_pos = (live_price - swing_low) / diff  # 0.0 = at low, 1.0 = at high

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        fib_618 = float(fib.get("fib_618", swing_low + (diff * 0.618)) or (swing_low + (diff * 0.618)))

        # Rule 1: If price is near swing high (> 75%), NEVER buy! Prohibit chasing top!
        if rel_pos >= 0.75:
            return {
                "agent_name": "Fibonacci_OTE_Agent",
                "action": "HOLD",
                "confidence_score": 85,
                "bias": "NEUTRAL",
                "reasoning": f"Price at {rel_pos*100:.0f}% of swing range (near high {swing_high:,.2f}). Buying into 0.786+ premium prohibited. Awaiting discount OTE retracement."
            }
        # Rule 2: If price is near swing low (< 25%), NEVER sell!
        elif rel_pos <= 0.25:
            return {
                "agent_name": "Fibonacci_OTE_Agent",
                "action": "HOLD",
                "confidence_score": 85,
                "bias": "NEUTRAL",
                "reasoning": f"Price at {rel_pos*100:.0f}% of swing range (near low {swing_low:,.2f}). Shorting into discount floor prohibited. Awaiting premium retracement."
            }
        # Rule 3: Legitimate 0.50 - 0.618 Golden Pocket Pullback
        elif 0.35 <= rel_pos <= 0.65:
            if trend == "BULLISH":
                entry = round(live_price - 0.50, 2)
                return {
                    "agent_name": "Fibonacci_OTE_Agent",
                    "action": "BUY",
                    "confidence_score": 90,
                    "bias": "BULLISH",
                    "setup_name": "Bullish_0.618_Golden_Pocket_Pullback",
                    "entry_price": entry,
                    "stop_loss": round(swing_low - 1.50, 2),
                    "take_profit_1": round(entry + tp1_pts, 2),
                    "take_profit_2": round(swing_high + 5.0, 2),
                    "fib_level_tested": f"0.618 OTE Zone ({fib_618:,.2f})",
                    "reasoning": f"Price pulled back to 0.618 Golden Pocket ({fib_618:,.2f}) in bullish trend. Risk/Reward highly favorable for continuation."
                }
            elif trend == "BEARISH":
                entry = round(live_price + 0.50, 2)
                return {
                    "agent_name": "Fibonacci_OTE_Agent",
                    "action": "SELL",
                    "confidence_score": 90,
                    "bias": "BEARISH",
                    "setup_name": "Bearish_0.618_Golden_Pocket_Pullback",
                    "entry_price": entry,
                    "stop_loss": round(swing_high + 1.50, 2),
                    "take_profit_1": round(entry - tp1_pts, 2),
                    "take_profit_2": round(swing_low - 5.0, 2),
                    "fib_level_tested": f"0.618 OTE Zone ({fib_618:,.2f})",
                    "reasoning": f"Price retraced to 0.618 Golden Pocket ({fib_618:,.2f}) in bearish trend. Downside continuation active."
                }

        return {
            "agent_name": "Fibonacci_OTE_Agent",
            "action": "HOLD",
            "confidence_score": 50,
            "bias": "NEUTRAL",
            "reasoning": "Price resting between Fibonacci nodes. Awaiting clean entry into Golden Pocket."
        }

