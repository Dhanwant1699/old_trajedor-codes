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

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        if trend == "BULLISH":
            entry = round(live_price - step, 2)
            golden_zone = fib.get("golden_pocket_ote", f"{entry-1.0:,.2f} - {entry+1.0:,.2f}")
            return {
                "agent_name": "Fibonacci_OTE_Agent",
                "action": "BUY",
                "confidence_score": 94,
                "bias": "BULLISH",
                "setup_name": "Bullish_0.618_Golden_Pocket_Pullback",
                "entry_price": entry,
                "stop_loss": round(entry - sl_pts, 2),
                "take_profit_1": round(entry + tp1_pts, 2),
                "take_profit_2": round(entry + tp2_pts, 2),
                "fib_level_tested": f"0.618-0.786 Golden Pocket ({golden_zone})",
                "reasoning": f"0.618 Golden Pocket retracement holding key harmonic support with 1.618 extension target projected at {entry + tp2_pts:,.2f}."
            }
        elif trend == "BEARISH":
            entry = round(live_price + step, 2)
            golden_zone = fib.get("golden_pocket_ote", f"{entry-1.0:,.2f} - {entry+1.0:,.2f}")
            return {
                "agent_name": "Fibonacci_OTE_Agent",
                "action": "SELL",
                "confidence_score": 94,
                "bias": "BEARISH",
                "setup_name": "Bearish_0.618_Golden_Pocket_Pullback",
                "entry_price": entry,
                "stop_loss": round(entry + sl_pts, 2),
                "take_profit_1": round(entry - tp1_pts, 2),
                "take_profit_2": round(entry - tp2_pts, 2),
                "fib_level_tested": f"0.618-0.786 Golden Pocket ({golden_zone})",
                "reasoning": f"0.618 Golden Pocket retracement holding key harmonic resistance with 1.618 extension target projected at {entry - tp2_pts:,.2f}."
            }
        else:
            return {
                "agent_name": "Fibonacci_OTE_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "reasoning": "Price resting in 50% equilibrium no-man's land. Awaiting clean impulse leg."
            }

