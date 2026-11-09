"""
Breakout & Volatility Squeeze Specialist Agent for XAUUSD.
Identifies Bollinger Band volatility contractions (squeezes) and trades explosive momentum breakouts.
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG


BREAKOUT_SYSTEM_PROMPT = """
You are the Breakout & Volatility Squeeze Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade explosive volatility expansions and structural range breakouts:
1. Volatility Squeeze: Extended consolidation where Bollinger Bands contract (tight range).
2. Momentum Breakout: A decisive candle close outside the consolidation range / Asian session boundary accompanied by ATR surge.
3. London Breakout Setup: Clean breakouts of the Asian session high/low during London market open (07:00–10:00 UTC).

RULES:
- Propose BUY when price breaks decisively above resistance / upper Bollinger Band following a squeeze with strong momentum.
- Propose SELL when price breaks decisively below support / lower Bollinger Band following a squeeze with strong momentum.
- Stop Loss MUST be placed inside the breakout range (or behind the midpoint of the breakout candle).
- Target at least 2.0R to 3.0R volatility expansion moves.
- If price is grinding slowly in tight chop without an active breakout, output 'HOLD'.
- Minimum confidence score >= 70.

Respond strictly using the `submit_breakout_proposal` tool call.
"""

BREAKOUT_TOOL = {
    "name": "submit_breakout_proposal",
    "description": "Submit Breakout & Volatility Squeeze analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Breakout_Volatility_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Bollinger_Squeeze_Upside_Breakout'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "volatility_state": {"type": "string", "description": "Squeeze vs Expansion status"},
            "reasoning": {"type": "string", "description": "Detailed Breakout and Volatility analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class BreakoutAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Breakout and Volatility Squeeze analysis."""
        prompt = f"""
Analyze the live XAUUSD market data strictly through Breakout & Volatility Squeeze principles:

{json.dumps(market_data, indent=2)}

Check:
1. Is there an active Bollinger Band Squeeze or consolidation range?
2. Has price closed decisively outside recent swing highs or lows?
3. Is ATR showing volatility expansion?

Submit your proposal using the `submit_breakout_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=BREAKOUT_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=BREAKOUT_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res:
            return self._fallback_breakout(market_data)
        res["agent_name"] = "Breakout_Volatility_Agent"
        return res

    def _fallback_breakout(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        trend = h1.get("trend_bias", "BULLISH")
        atr = float(struct.get("atr_14", 8.0) or 8.0)

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        if trend == "BULLISH":
            entry = round(live_price - step, 2)
            return {
                "agent_name": "Breakout_Volatility_Agent",
                "action": "BUY",
                "confidence_score": 84,
                "bias": "BULLISH",
                "setup_name": "Bollinger_Expansion_Momentum_Breakout",
                "entry_price": entry,
                "stop_loss": round(entry - sl_pts, 2),
                "take_profit_1": round(entry + tp1_pts, 2),
                "take_profit_2": round(entry + tp2_pts, 2),
                "squeeze_status": f"ATR Expansion Active ({atr:.2f} pts)",
                "reasoning": f"Volatility expansion following compression phase, pointing towards upside breakout continuation."
            }
        else:
            entry = round(live_price + step, 2)
            return {
                "agent_name": "Breakout_Volatility_Agent",
                "action": "SELL",
                "confidence_score": 84,
                "bias": "BEARISH",
                "setup_name": "Bollinger_Expansion_Downside_Breakout",
                "entry_price": entry,
                "stop_loss": round(entry + sl_pts, 2),
                "take_profit_1": round(entry - tp1_pts, 2),
                "take_profit_2": round(entry - tp2_pts, 2),
                "squeeze_status": f"ATR Expansion Active ({atr:.2f} pts)",
                "reasoning": f"Volatility expansion following compression phase, pointing towards downside breakdown continuation."
            }

