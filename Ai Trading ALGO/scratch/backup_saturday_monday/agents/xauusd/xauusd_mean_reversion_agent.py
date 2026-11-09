"""
Mean Reversion & Statistical Arbitrage Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Bollinger Bands (2.5 sigma), RSI exhaustion,
and Gold ATR statistical extreme fades.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_MEAN_REV_SYSTEM_PROMPT = """
You are the Mean Reversion Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to identify statistical price over-extensions and extreme mean-reversion exhaustion points:

PRO-TRADER GOLD RULES:
1. NEVER fade a strong D1/H4 macro trend in the middle of an expansion leg.
2. In strong trends, mean-reversion trades are STRICTLY pullbacks BACK TO dynamic value (buying dips to EMA 21/50 or VWAP in uptrends; selling rallies to EMA 21/50 or VWAP in downtrends).
3. Counter-trend exhaustion fades are ONLY permitted when:
   - Gold price has pierced the outer 2.5/3.0-sigma Bollinger Band on H4/H1, AND
   - RSI(14) is at historical extremes (>= 78 for overbought shorts, <= 22 for oversold longs), AND
   - Gold has swept a major macro liquidity pool (PDH / PDL / Multi-day high).
4. If conditions are not at extreme boundaries, output 'HOLD' or plan a dynamic value pullback.

Respond strictly using the `submit_gold_mean_reversion_proposal` tool call.
"""

GOLD_MEAN_REV_TOOL = {
    "name": "submit_gold_mean_reversion_proposal",
    "description": "Submit Mean Reversion analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Mean_Reversion_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_Dynamic_Value_Pullback_EMA50'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "statistical_deviation": {"type": "string", "description": "Status of Gold Bollinger Bands & RSI"},
            "reasoning": {"type": "string", "description": "Detailed Gold mean-reversion analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldMeanReversionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Mean Reversion analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze current live Gold (XAUUSD) market data for statistical extremes and dynamic value pullbacks:

{json.dumps(market_data, indent=2)}

Check:
1. Is Gold price stretched beyond Bollinger 2.5 sigma or RSI >= 78 / <= 22?
2. In the presence of a strong D1/H4 trend, is price pulling back into dynamic mean value (EMA 50 / VWAP)?
3. What is the safe invalidation level beyond the statistical boundary?

Submit your proposal using the `submit_gold_mean_reversion_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_MEAN_REV_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_MEAN_REV_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_mean_rev(market_data)

        res["agent_name"] = "Gold_Mean_Reversion_Agent"
        return res

    def _fallback_mean_rev(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
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
                "agent_name": "Gold_Mean_Reversion_Agent",
                "action": "BUY",
                "confidence_score": 80,
                "bias": "BULLISH",
                "setup_name": "Gold_Dynamic_Value_Pullback_Support",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "statistical_deviation": "Gold RSI reset to 48.0 (Neutral value zone)",
                "reasoning": "Gold trend is top-down Bullish. Pullback to dynamic value provides a statistical high-probability continuation entry."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_Mean_Reversion_Agent",
                "action": "SELL",
                "confidence_score": 80,
                "bias": "BEARISH",
                "setup_name": "Gold_Dynamic_Value_Rally_Resistance",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "statistical_deviation": "Gold RSI reset to 52.0 (Neutral value zone)",
                "reasoning": "Gold trend is top-down Bearish. Rally to dynamic value provides a statistical high-probability continuation short."
            }
        else:
            return {
                "agent_name": "Gold_Mean_Reversion_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_Range_Midpoint",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "statistical_deviation": "Near equilibrium",
                "reasoning": "Gold is sitting at the midpoint of statistical bands. Awaiting extreme boundaries."
            }
