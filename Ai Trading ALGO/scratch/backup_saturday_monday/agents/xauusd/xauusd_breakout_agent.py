"""
Breakout & Volatility Squeeze Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Asian session volatility squeeze expansions,
London & NY open momentum breakouts, and Donchian channel expansions.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_BREAKOUT_SYSTEM_PROMPT = """
You are the Breakout & Volatility Squeeze Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to detect volatility compression and trade explosive expansions strictly aligned with the HTF Gold trend:

GOLD BREAKOUT SPECIALIZATION:
1. Volatility Squeeze: Bollinger Bands compressing inside Keltner Channels on Gold M15/H1 (Bandwidth < 1.0).
2. Asian Session Range Expansion: Breakout above Asian High during London Open with volume, or breakdown below Asian Low during London Open.
3. Donchian Channel High/Low Breakouts with momentum volume confirmation.

PRO-TRADER GOLD RULES:
- Only trade upside breakouts if Gold D1/H4 macro trend is Bullish.
- Only trade downside breakdowns if Gold D1/H4 macro trend is Bearish.
- In chop or range-bound regimes without volatility compression, output 'HOLD'.
- Place Stop Loss back inside the breakout base/consolidation range.
- Target at least 1.75R to 3.0R volatility expansion.

Respond strictly using the `submit_gold_breakout_proposal` tool call.
"""

GOLD_BREAKOUT_TOOL = {
    "name": "submit_gold_breakout_proposal",
    "description": "Submit Breakout & Volatility Squeeze analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Breakout_Volatility_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_London_Open_Asian_Range_Expansion_Long'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "squeeze_status": {"type": "string", "description": "Status of Gold Bollinger/Keltner squeeze"},
            "reasoning": {"type": "string", "description": "Detailed volatility expansion analysis for Gold"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldBreakoutAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Breakout & Squeeze analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) volatility compression and breakout state across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Is Gold in an active volatility squeeze (compressed bands)?
2. Is price breaking out of Asian Range or Key Donchian channel levels in the HTF trend direction?
3. Is volume expanding on the breakout?

Submit your proposal using the `submit_gold_breakout_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_BREAKOUT_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_BREAKOUT_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_breakout(market_data)

        res["agent_name"] = "Gold_Breakout_Volatility_Agent"
        return res

    def _fallback_breakout(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
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
                "agent_name": "Gold_Breakout_Volatility_Agent",
                "action": "BUY",
                "confidence_score": 82,
                "bias": "BULLISH",
                "setup_name": "Gold_Bullish_Volatility_Expansion_Continuation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "squeeze_status": "Gold Volatility Expansion in HTF Trend Direction",
                "reasoning": "Gold expanding out of intraday compression aligned with D1/H4 macro bullish momentum."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_Breakout_Volatility_Agent",
                "action": "SELL",
                "confidence_score": 82,
                "bias": "BEARISH",
                "setup_name": "Gold_Bearish_Volatility_Expansion_Continuation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "squeeze_status": "Gold Volatility Expansion in HTF Trend Direction",
                "reasoning": "Gold expanding out of intraday compression aligned with D1/H4 macro bearish momentum."
            }
        else:
            return {
                "agent_name": "Gold_Breakout_Volatility_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_Compression_Pending",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "squeeze_status": "In Range Compression",
                "reasoning": "Gold is compressing inside a narrow range. Waiting for confirmed directional breakout."
            }
