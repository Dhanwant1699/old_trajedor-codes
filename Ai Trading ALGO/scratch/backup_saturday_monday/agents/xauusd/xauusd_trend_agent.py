"""
Trend Following & Momentum Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Multi-timeframe trend alignment (D1/H4/H1/M15), EMA 50/200 stacks,
and Gold pullback continuation dynamics.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_TREND_SYSTEM_PROMPT = """
You are the Trend & Momentum Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade strictly in the direction of dominant Top-Down Gold Trends (D1 -> H4 -> H1 -> M15):
1. Macro Trend Stack (D1 / H4): Position of Gold price relative to EMA 50 & EMA 200, slope of EMA ribbon, and macro momentum.
2. Intermediate Trend (H1): Directional structure of EMA 9/21/50 clouds confirming Gold trend continuation.
3. Pullback Entry Execution (M15): Buying Gold pullbacks into dynamic EMA 21 / EMA 50 support in uptrends; selling rallies into EMA 21 / EMA 50 resistance in downtrends.
4. Momentum Thrust (M5): Fast momentum alignment confirming the Gold continuation burst.

PRO-TRADER GOLD RULES:
- NEVER fight the dominant D1 and H4 Gold macro trend.
- If Gold D1 is Bullish and H4 is Bullish, look strictly for H1/M15 pullback BUY opportunities.
- If Gold D1 is Bearish and H4 is Bearish, look strictly for H1/M15 rally SELL opportunities.
- If timeframes are conflicted or Gold is trapped in EMA 50/200 compression, output 'HOLD'.
- Place Stop Loss below dynamic trend support (EMA 50 or swing low + ATR buffer).
- Target at least 1.75R (TP1) to 3.0R (TP2) trailing trend targets.

Respond strictly using the `submit_gold_trend_proposal` tool call.
"""

GOLD_TREND_TOOL = {
    "name": "submit_gold_trend_proposal",
    "description": "Submit Trend Following analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Trend_Momentum_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_H1_H4_Bullish_Trend_M15_EMA50_Pullback'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "timeframe_alignment": {"type": "string", "description": "Status of Gold H4, H1, M15 alignment"},
            "reasoning": {"type": "string", "description": "Detailed Gold trend & momentum analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldTrendAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Trend & Momentum analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) market data across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Is Gold H4 macro trend aligned with H1 intermediate trend?
2. Where is current Gold price relative to M15 EMA 50 and EMA 200?
3. Is price pulling back into high-probability trend continuation support/resistance?
4. What is the ATR volatility state for Gold?

Submit your proposal using the `submit_gold_trend_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_TREND_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_TREND_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_trend(market_data)

        res["agent_name"] = "Gold_Trend_Momentum_Agent"
        return res

    def _fallback_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        d1_bias = top_down.get("d1_bias", "BULLISH")
        h4_bias = top_down.get("h4_bias", "BULLISH")
        h1_bias = top_down.get("h1_bias", "BULLISH")
        m15_bias = top_down.get("m15_bias", "BULLISH")
        
        sl_buffer = 10.0
        tp1_buffer = 18.0
        tp2_buffer = 32.0

        if d1_bias == "BULLISH" and h4_bias == "BULLISH":
            entry = live_price
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Gold_Trend_Momentum_Agent",
                "action": "BUY",
                "confidence_score": 88,
                "bias": "BULLISH",
                "setup_name": "Gold_TopDown_Macro_Trend_Continuation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "timeframe_alignment": f"D1: {d1_bias} | H4: {h4_bias} | H1: {h1_bias} | M15: {m15_bias}",
                "reasoning": f"Gold Top-Down Bullish alignment (D1/H4). Treating lower timeframe consolidation as high-probability pullback buy."
            }
        elif d1_bias == "BEARISH" and h4_bias == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_Trend_Momentum_Agent",
                "action": "SELL",
                "confidence_score": 88,
                "bias": "BEARISH",
                "setup_name": "Gold_TopDown_Macro_Trend_Continuation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "timeframe_alignment": f"D1: {d1_bias} | H4: {h4_bias} | H1: {h1_bias} | M15: {m15_bias}",
                "reasoning": f"Gold Top-Down Bearish alignment (D1/H4). Treating lower timeframe bounces as high-probability rally sell."
            }
        else:
            return {
                "agent_name": "Gold_Trend_Momentum_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_Timeframe_Conflict",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "timeframe_alignment": f"D1: {d1_bias} | H4: {h4_bias} | H1: {h1_bias}",
                "reasoning": "Gold macro timeframes are conflicted. Standing aside until alignment clears."
            }
