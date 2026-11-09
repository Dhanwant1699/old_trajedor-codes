"""
Trend Following, Momentum & Multi-Timeframe Fractal Harmony Specialist Agent for XAUUSD.
Combines:
1. VasilyTrader Top-Down MTF Architecture: Higher Timeframe (D1/H4) Level -> Trading Timeframe (H1/M15) Confirmation.
2. FXNX Fractal Harmony Strategy:
   - D1 Compass: Institutional battlefield mapping & Premium vs Discount territory.
   - H4 Structural Filter: The bridge that filters out noise via Market Structure Shift (MSS).
   - M15 Execution Trigger: Change of Character (ChoCH), FVG fill, and dynamic EMA retests.
3. The Golden Rule of Fractal Harmony:
   - Longs ONLY when H4 is Bullish AND D1 is at Discount / Bullish.
   - Shorts ONLY when H4 is Bearish AND D1 is at Premium / Bearish.
   - When D1 and H4 conflict: Stand Aside ("Patience is you refusing to pay for someone else's stop hunt").
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


TREND_SYSTEM_PROMPT = """
You are the Trend, Momentum & Multi-Timeframe Fractal Harmony Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade strictly with the hierarchy of time:

1. The Hierarchy of Time (Top-Down Multi-Timeframe Strategy):
   - Daily (D1) = The Compass: Defines who is winning the macro war and whether price is in an institutional Discount (buy territory) or Premium (sell territory).
   - 4-Hour (H4) = The Filter / The Bridge: Slow enough to ignore intraday spikes, fast enough to capture structural shifts (MSS). Never catch falling knives; wait for the 4H bridge to confirm direction.
   - 1-Hour / 15-Minute (H1/M15) = The Execution Trigger: Identifies Change of Character (ChoCH), EMA 21/50 pullback bounces, and unmitigated FVG entries.

2. The Golden Rule of Fractal Harmony:
   - ONLY take longs when H4 is Bullish AND D1 is at Discount or Bullish structure.
   - ONLY take shorts when H4 is Bearish AND D1 is at Premium or Bearish structure.
   - When D1 and H4 disagree (e.g. D1 Discount but 4H still printing lower highs), you DO NOT have a trade—you have an unanswered question. Enforce 'HOLD' ("Patience is you refusing to pay for someone else's stop hunt").

3. Gold Volatility & ATR Risk Management:
   - Never place tight 15M/5M micro-stops on Gold (easily wiped out by institutional sweeps).
   - Stops MUST be placed below 4H/M15 structural swing lows or dynamic EMA 50 + ATR buffer (+1.50 to +2.50 pts).
   - Targets should aim for the opposing HTF structural boundary with minimum 1.5R to 2.5R.

Respond strictly using the `submit_trend_proposal` tool call.
"""

TREND_TOOL = {
    "name": "submit_trend_proposal",
    "description": "Submit Multi-Timeframe Trend & Fractal Harmony analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Trend_Momentum_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'D1_Discount_H4_Bullish_MSS_M15_Pullback'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "timeframe_alignment": {"type": "string", "description": "Status of D1 Compass, H4 Filter, and M15 Trigger"},
            "reasoning": {"type": "string", "description": "Detailed multi-timeframe fractal harmony analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class TrendAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Multi-Timeframe Trend & Fractal Harmony analysis on live market data."""
        prompt = f"""
Analyze the current live XAUUSD market data strictly through VasilyTrader Top-Down MTF and FXNX Fractal Harmony principles:

{json.dumps(market_data, indent=2)}

Check:
1. D1 Compass: Is price in an institutional Discount or Premium zone? What is the D1 trend bias?
2. H4 Filter: Is H4 confirmed Bullish or Bearish? Has an MSS occurred?
3. Fractal Harmony Golden Rule: Are D1 and H4 aligned, or are they in conflict?
4. M15 Trigger: Is price offering a clean pullback entry to dynamic EMA 21/50 or FVG?
5. Is the Stop Loss safely buffered outside structural swing levels?

Submit your proposal using the `submit_trend_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=TREND_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=TREND_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res or not res.get("action"):
            return self._fallback_trend(market_data)
        res["agent_name"] = "Trend_Momentum_Agent"
        return res

    def _fallback_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4180.0)
        ms = market_data.get("market_structures", {})
        struct = ms.get("m15_execution_structure", {})
        m5 = ms.get("m5_micro_momentum", {})
        h1 = ms.get("h1_trend_structure", {})
        h4 = ms.get("h4_macro_trend", {})
        d1 = ms.get("d1_macro_compass", {})
        fh = ms.get("fractal_harmony_matrix", {})

        # 1. Multi-Timeframe Indicators
        d1_zone = str(d1.get("d1_auction_zone", "DISCOUNT")).upper()
        d1_bias = str(d1.get("d1_trend_bias", "BEARISH")).upper()
        h4_bias = str(h4.get("macro_bias", "BULLISH")).upper()
        h4_mss = str(h4.get("h4_mss_structure", "IN_RANGE")).upper()
        h1_bias = str(h1.get("trend_bias", "BULLISH")).upper()
        m5_cross = str(m5.get("fast_cross", "BULLISH")).upper()

        atr = float(struct.get("atr_14", 8.0) or 8.0)
        ema21 = float(struct.get("ema_21", live_price) or live_price)
        ema50 = float(struct.get("ema_50", live_price) or live_price)

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        sl_pts = 850.0 if is_btc else max(9.0, round(atr * 1.25, 2))
        tp1_pts = 1400.0 if is_btc else 14.00
        tp2_pts = 2800.0 if is_btc else 26.00

        dist_from_ema = live_price - ema21

        # 2. Check Fractal Harmony Golden Rule Alignment
        aligned_buy = (d1_zone == "DISCOUNT" or d1_bias == "BULLISH") and h4_bias == "BULLISH"
        aligned_sell = (d1_zone == "PREMIUM" or d1_bias == "BEARISH") and h4_bias == "BEARISH"

        # CASE A: BULLISH FRACTAL HARMONY (D1 Discount/Bullish + H4 Bullish)
        if aligned_buy:
            if dist_from_ema > (atr * 1.35):
                return {
                    "agent_name": "Trend_Momentum_Agent",
                    "action": "HOLD",
                    "confidence_score": 75,
                    "bias": "BULLISH",
                    "reasoning": f"Bullish Fractal Harmony active (D1 {d1_zone} + H4 {h4_bias}), but price is overextended +{dist_from_ema:.2f} pts above M15 EMA 21. Chasing highs prohibited; awaiting pullback."
                }
            elif m5_cross == "BEARISH":
                return {
                    "agent_name": "Trend_Momentum_Agent",
                    "action": "HOLD",
                    "confidence_score": 70,
                    "bias": "NEUTRAL",
                    "reasoning": f"Bullish Fractal Harmony active, but M5 micro-momentum is in pullback/cooling. Standing aside until M5 prints bullish turn."
                }
            else:
                entry = round(live_price - 0.50, 2)
                return {
                    "agent_name": "Trend_Momentum_Agent",
                    "action": "BUY",
                    "confidence_score": 91,
                    "bias": "BULLISH",
                    "setup_name": "Bullish_Fractal_Harmony_M15_Pullback",
                    "entry_price": entry,
                    "stop_loss": round(ema50 - 1.50, 2),
                    "take_profit_1": round(entry + tp1_pts, 2),
                    "take_profit_2": round(entry + tp2_pts, 2),
                    "timeframe_alignment": f"D1 Compass: {d1_zone} | H4 Filter: {h4_bias} ({h4_mss}) | M15 Trigger: Aligned",
                    "reasoning": f"Fractal Harmony confirmed: D1 in {d1_zone} with H4 Bullish trend. Price respecting dynamic EMA support with safe ATR stop."
                }

        # CASE B: BEARISH FRACTAL HARMONY (D1 Premium/Bearish + H4 Bearish)
        elif aligned_sell:
            if dist_from_ema < -(atr * 1.35):
                return {
                    "agent_name": "Trend_Momentum_Agent",
                    "action": "HOLD",
                    "confidence_score": 75,
                    "bias": "BEARISH",
                    "reasoning": f"Bearish Fractal Harmony active (D1 {d1_zone} + H4 {h4_bias}), but price is overextended -{abs(dist_from_ema):.2f} pts below M15 EMA 21. Shorting bottoms prohibited; awaiting bounce."
                }
            elif m5_cross == "BULLISH":
                return {
                    "agent_name": "Trend_Momentum_Agent",
                    "action": "HOLD",
                    "confidence_score": 70,
                    "bias": "NEUTRAL",
                    "reasoning": f"Bearish Fractal Harmony active, but M5 micro-momentum is in upward bounce. Standing aside until M5 prints bearish continuation."
                }
            else:
                entry = round(live_price + 0.50, 2)
                return {
                    "agent_name": "Trend_Momentum_Agent",
                    "action": "SELL",
                    "confidence_score": 91,
                    "bias": "BEARISH",
                    "setup_name": "Bearish_Fractal_Harmony_M15_Pullback",
                    "entry_price": entry,
                    "stop_loss": round(ema50 + 1.50, 2),
                    "take_profit_1": round(entry - tp1_pts, 2),
                    "take_profit_2": round(entry - tp2_pts, 2),
                    "timeframe_alignment": f"D1 Compass: {d1_zone}/{d1_bias} | H4 Filter: {h4_bias} ({h4_mss}) | M15 Trigger: Aligned",
                    "reasoning": f"Fractal Harmony confirmed: D1 {d1_zone}/{d1_bias} with H4 Bearish trend. Selling dynamic resistance pullback with safe ATR stop."
                }

        # CASE C: FRACTAL CONFLICT (D1 and H4 Disagree) -> PATIENCE MANDATE
        else:
            return {
                "agent_name": "Trend_Momentum_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "reasoning": f"Fractal Conflict Gate: D1 Compass ({d1_zone}/{d1_bias}) and H4 Filter ({h4_bias}) are out of sync. Standing aside until the 4H structural bridge confirms an MSS to avoid paying for institutional stop hunts."
            }
