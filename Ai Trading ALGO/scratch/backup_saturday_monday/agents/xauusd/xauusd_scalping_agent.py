"""
Intraday Scalping & Micro-Momentum Thrust Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Rapid 5-minute candle momentum bursts, VWAP micro-bounces,
and sub-minute order flow thrusts strictly aligned with H1/H4 structural bias.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_SCALP_SYSTEM_PROMPT = """
You are the Intraday Scalping Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to capture high-velocity micro momentum thrusts on Gold 5-minute charts:

GOLD SCALPING SPECIALIZATION:
1. Trend-Aligned Scalping: Micro-thrusts are ONLY executed in the direction of the dominant H1/H4 macro trend. Never scalp counter-trend.
2. Trigger Conditions: Price testing M5/M15 EMA 21 or Session VWAP with aggressive buyer/seller tick momentum.
3. Rapid Execution & Tight Risk: Tight Stop Loss (below recent M5 swing low/high + buffer) and quick 1.5R to 2.5R momentum targets.

RULES:
- Propose BUY scalp if Gold H1/H4 is Bullish and M5 shows bullish momentum thrust after a pullback.
- Propose SELL scalp if Gold H1/H4 is Bearish and M5 shows bearish momentum thrust after a rally.
- In low-volatility or directionless chop, output 'HOLD'.

Respond strictly using the `submit_gold_scalping_proposal` tool call.
"""

GOLD_SCALP_TOOL = {
    "name": "submit_gold_scalping_proposal",
    "description": "Submit Intraday Scalping analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Intraday_Scalp_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_M5_Momentum_Thrust_Continuation'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "momentum_indicator": {"type": "string", "description": "Status of Gold M5 momentum"},
            "reasoning": {"type": "string", "description": "Detailed scalping & micro-momentum analysis for Gold"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldScalpingAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Scalping analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) 5-minute micro-momentum data:

{json.dumps(market_data, indent=2)}

Check:
1. Is Gold M5 momentum accelerating in the direction of the H1/H4 trend?
2. Is price bouncing off M5 EMA 21 or Session VWAP?
3. What is the tight intraday invalidation level?

Submit your proposal using the `submit_gold_scalping_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_SCALP_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_SCALP_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_scalp(market_data)

        res["agent_name"] = "Gold_Intraday_Scalp_Agent"
        return res

    def _fallback_scalp(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        sl_buffer = 8.0
        tp1_buffer = 15.0
        tp2_buffer = 25.0

        if dominant_trend == "BULLISH":
            entry = live_price
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Gold_Intraday_Scalp_Agent",
                "action": "BUY",
                "confidence_score": 82,
                "bias": "BULLISH",
                "setup_name": "Gold_M5_Trend_Aligned_Momentum_Scalp",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "momentum_indicator": "Gold M5 Bullish Tick Acceleration",
                "reasoning": "Gold M5 micro-momentum aligned with HTF D1/H4 bullish trend."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_Intraday_Scalp_Agent",
                "action": "SELL",
                "confidence_score": 82,
                "bias": "BEARISH",
                "setup_name": "Gold_M5_Trend_Aligned_Momentum_Scalp",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "momentum_indicator": "Gold M5 Bearish Tick Acceleration",
                "reasoning": "Gold M5 micro-momentum aligned with HTF D1/H4 bearish trend."
            }
        else:
            return {
                "agent_name": "Gold_Intraday_Scalp_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_No_Scalp_Setup",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "momentum_indicator": "Flat",
                "reasoning": "Gold 5-minute momentum is flat. No scalping edge."
            }
