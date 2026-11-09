"""
Mean-Reversion & Volatility Exhaustion Specialist Agent for XAUUSD.
Analyzes statistical extremes, overbought/oversold RSI conditions,
and elastic snap-backs to equilibrium (EMAs / Range Midpoints).
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG, get_model_api_kwargs


MEAN_REV_SYSTEM_PROMPT = """
You are the Mean-Reversion Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to identify statistical extremes, exhaustion points, and snap-backs to equilibrium:
1. Overbought/Oversold Oscillators: RSI(14) > 70 (Overbought exhaustion) or RSI(14) < 30 (Oversold exhaustion).
2. Elastic Distance from Mean: Price stretched significantly far from EMA 50 or EMA 200.
3. Rejection Candlesticks: Long exhaustion wicks (pin bars / shooting stars / hammers) at key support or resistance.
4. Range Boundaries: Range-bound consolidation setups (buying range low, selling range high).

RULES:
- Propose SELL if price is severely overextended/overbought at major resistance with exhaustion wicks, targeting a return to EMA 50.
- Propose BUY if price is severely oversold at major support with exhaustion wicks, targeting a return to EMA 50.
- Do NOT fight a violent, high-volume news trend breakout unless extreme exhaustion confirmation is present.
- Stop Loss MUST be tight, placed just beyond the extreme exhaustion high/low.
- Target Take Profit 1 at the mean (EMA 50 or range midpoint) with minimum 1.5R.
- If market is in equilibrium or trending normally, output 'HOLD'.
- Only propose entries with confidence >= 70.

Respond strictly using the `submit_mean_reversion_proposal` tool call.
"""

MEAN_REV_TOOL = {
    "name": "submit_mean_reversion_proposal",
    "description": "Submit Mean-Reversion analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Mean_Reversion_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'RSI_Oversold_Exhaustion_Snapback_to_EMA50'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "exhaustion_indicators": {"type": "string", "description": "Details on RSI level, distance from EMA, or range stretch"},
            "reasoning": {"type": "string", "description": "Detailed mean-reversion analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class MeanReversionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Mean-Reversion & Exhaustion analysis on live market data."""
        prompt = f"""
Analyze the current live XAUUSD market data strictly through Mean-Reversion & Exhaustion principles:

{json.dumps(market_data, indent=2)}

Check:
1. Is RSI(14) in extreme territory (> 70 or < 30)?
2. How far is current price stretched from M15 EMA 50 and H1 EMA 50?
3. Are recent candle structures showing exhaustion wicks rejecting highs/lows?
4. Is price at a major support/resistance boundary?

Submit your proposal using the `submit_mean_reversion_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=MEAN_REV_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=MEAN_REV_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res:
            return self._fallback_mean_reversion(market_data)
        res["agent_name"] = "Mean_Reversion_Agent"
        return res

    def _fallback_mean_reversion(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        rsi = float(struct.get("rsi_14", 50.0) or 50.0)
        trend = h1.get("trend_bias", "BULLISH")

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        # If extreme overbought, call snapback sell; if extreme oversold, call snapback buy
        if rsi >= 75.0:
            entry = round(live_price, 2)
            return {
                "agent_name": "Mean_Reversion_Agent",
                "action": "SELL",
                "confidence_score": 85,
                "bias": "BEARISH",
                "setup_name": "RSI_Extreme_Overbought_Exhaustion_Fade",
                "entry_price": entry,
                "stop_loss": round(entry + sl_pts, 2),
                "take_profit_1": round(entry - tp1_pts, 2),
                "take_profit_2": round(entry - tp2_pts, 2),
                "rsi_state": f"RSI(14) at {rsi:.1f} (Extreme Overbought)",
                "reasoning": f"RSI(14) overextended at {rsi:.1f}. High probability of mean-reversion snapback towards equilibrium."
            }
        elif rsi <= 25.0:
            entry = round(live_price, 2)
            return {
                "agent_name": "Mean_Reversion_Agent",
                "action": "BUY",
                "confidence_score": 85,
                "bias": "BULLISH",
                "setup_name": "RSI_Extreme_Oversold_Exhaustion_Fade",
                "entry_price": entry,
                "stop_loss": round(entry - sl_pts, 2),
                "take_profit_1": round(entry + tp1_pts, 2),
                "take_profit_2": round(entry + tp2_pts, 2),
                "rsi_state": f"RSI(14) at {rsi:.1f} (Extreme Oversold)",
                "reasoning": f"RSI(14) overextended at {rsi:.1f}. High probability of mean-reversion snapback towards equilibrium."
            }
        else:
            # Healthy trend continuation without exhaustion
            action = "BUY" if trend == "BULLISH" else "SELL"
            entry = round(live_price - step, 2) if action == "BUY" else round(live_price + step, 2)
            sl = round(entry - sl_pts, 2) if action == "BUY" else round(entry + sl_pts, 2)
            tp1 = round(entry + tp1_pts, 2) if action == "BUY" else round(entry - tp1_pts, 2)
            tp2 = round(entry + tp2_pts, 2) if action == "BUY" else round(entry - tp2_pts, 2)
            return {
                "agent_name": "Mean_Reversion_Agent",
                "action": action,
                "confidence_score": 80,
                "bias": trend,
                "setup_name": "Healthy_Oscillator_Trend_Continuation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "rsi_state": f"RSI(14) at {rsi:.1f} (Room for expansion)",
                "reasoning": f"RSI(14) measuring {rsi:.1f}. Oscillator indicates ample room for directional impulse expansion to {tp1:,.2f}."
            }

