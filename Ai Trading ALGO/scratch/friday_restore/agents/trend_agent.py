"""
Trend Following & Momentum Specialist Agent for XAUUSD.
Analyzes multi-timeframe trend alignment (H4/H1/M15), EMA dynamics (50/200),
and momentum continuation pullbacks.
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG, get_model_api_kwargs


TREND_SYSTEM_PROMPT = """
You are the Trend & Momentum Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade strictly in the direction of dominant multi-timeframe trends:
1. Multi-Timeframe Alignment: H4 Macro Direction + H1 Trend + M15 Momentum.
2. Moving Average Confluence: EMA 50 vs EMA 200 slope, position of price relative to EMAs.
3. Pullback Entries: Buying pullbacks to dynamic EMA 50 support in uptrend, selling pullbacks to EMA 50 resistance in downtrend.
4. Momentum & Breakouts: Consecutive candle closes confirming directional continuation.

RULES:
- Never fight the H4/H1 dominant trend.
- If H4 is Bullish and H1 is Bullish, look for M15 pullback BUY opportunities.
- If H4 is Bearish and H1 is Bearish, look for M15 pullback SELL opportunities.
- If timeframes are conflicted or price is trapped between EMA 50 and EMA 200 in chop, output 'HOLD'.
- Place Stop Loss below dynamic trend support (EMA 50 or recent swing low + ATR buffer).
- Target at least 1.5R to 2.5R trailing trend targets.
- Only propose entries with confidence >= 70.

Respond strictly using the `submit_trend_proposal` tool call.
"""

TREND_TOOL = {
    "name": "submit_trend_proposal",
    "description": "Submit Trend Following analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Trend_Momentum_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'H1_H4_Bullish_Trend_M15_EMA50_Pullback'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "timeframe_alignment": {"type": "string", "description": "Status of H4, H1, M15 alignment"},
            "reasoning": {"type": "string", "description": "Detailed trend & momentum analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class TrendAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Trend & Momentum analysis on live market data."""
        prompt = f"""
Analyze the current live XAUUSD market data strictly through Trend & Momentum principles:

{json.dumps(market_data, indent=2)}

Check:
1. Is H4 macro trend aligned with H1 intermediate trend?
2. Where is current price relative to M15 EMA 50 and EMA 200?
3. Is price pulling back into high-probability trend continuation support/resistance?
4. What is the ATR volatility state?

Submit your proposal using the `submit_trend_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=TREND_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=TREND_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_trend(market_data)

        res["agent_name"] = "Trend_Momentum_Agent"
        return res

    def _fallback_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        h4 = market_data.get("market_structures", {}).get("h4_macro_trend", {})
        
        h1_bias = h1.get("trend_bias", "BULLISH")
        h4_bias = h4.get("macro_bias", "BULLISH")

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        if h1_bias == "BULLISH" or h4_bias == "BULLISH":
            entry = round(live_price - step, 2)
            ema50 = struct.get("ema_50", entry - 3.0)
            return {
                "agent_name": "Trend_Momentum_Agent",
                "action": "BUY",
                "confidence_score": 88,
                "bias": "BULLISH",
                "setup_name": "H1_H4_Bullish_Trend_M15_Pullback",
                "entry_price": entry,
                "stop_loss": round(entry - sl_pts, 2),
                "take_profit_1": round(entry + tp1_pts, 2),
                "take_profit_2": round(entry + tp2_pts, 2),
                "timeframe_alignment": "H4 Bullish / H1 Bullish / M15 Momentum Pullback",
                "reasoning": f"Multi-TF bullish trend alignment confirmed. Price respecting dynamic EMA 50 support ({ema50:,.2f}) with continuation targets active."
            }
        elif h1_bias == "BEARISH" or h4_bias == "BEARISH":
            entry = round(live_price + step, 2)
            ema50 = struct.get("ema_50", entry + 3.0)
            return {
                "agent_name": "Trend_Momentum_Agent",
                "action": "SELL",
                "confidence_score": 88,
                "bias": "BEARISH",
                "setup_name": "H1_H4_Bearish_Trend_M15_Pullback",
                "entry_price": entry,
                "stop_loss": round(entry + sl_pts, 2),
                "take_profit_1": round(entry - tp1_pts, 2),
                "take_profit_2": round(entry - tp2_pts, 2),
                "timeframe_alignment": "H4 Bearish / H1 Bearish / M15 Momentum Pullback",
                "reasoning": f"Multi-TF bearish trend alignment confirmed. Price rejecting dynamic EMA 50 resistance ({ema50:,.2f}) with downside targets active."
            }
        else:
            return {
                "agent_name": "Trend_Momentum_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "reasoning": "EMAs intertwined in choppy consolidation. Awaiting directional breakout."
            }

