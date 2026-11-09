"""
Intraday Scalping & Fast Momentum Thrust Specialist Agent for XAUUSD.
Analyzes micro-momentum M5/M15 price thrusts, fast EMA (9/21) crossovers, and rapid volatility impulses.
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG


SCALPING_SYSTEM_PROMPT = """
You are the Intraday Scalping & Fast Momentum Specialist on an institutional Gold (XAUUSD) trading desk.
Your mandate is to capture rapid intraday price thrusts and micro-momentum breakouts:
1. Fast Moving Average Dynamic: EMA 9 crossing and holding above EMA 21 (Bullish thrust), or below EMA 21 (Bearish thrust).
2. Micro Momentum Pullbacks: Snapping into fast M5/M15 pullbacks during active London/NY high-liquidity sessions.
3. Rapid Impulse Captures: Quick, disciplined intraday runs targeting nearest liquidity swing points.

RULES:
- Propose BUY when EMA 9 crosses above EMA 21 on M5/M15 with expanding momentum during high-volume sessions.
- Propose SELL when EMA 9 crosses below EMA 21 on M5/M15 with expanding momentum during high-volume sessions.
- Stop Loss MUST be tight, placed just behind the fast EMA 21 / recent micro-swing low or high.
- Target swift 1.5R to 2.0R moves.
- If spread is wide, volume is low, or market is in dead Asian hours, output 'HOLD'.
- Minimum confidence score >= 70.

Respond strictly using the `submit_scalping_proposal` tool call.
"""

SCALPING_TOOL = {
    "name": "submit_scalping_proposal",
    "description": "Submit Intraday Scalping and Momentum trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Scalping_Momentum_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Fast_EMA9_21_Bullish_Thrust_Pullback'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "scalp_trigger": {"type": "string", "description": "Specific micro-momentum trigger"},
            "reasoning": {"type": "string", "description": "Detailed intraday scalping and momentum analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class ScalpingAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Intraday Scalping & Momentum analysis."""
        prompt = f"""
Analyze the live XAUUSD market data strictly through Intraday Scalping & Fast Momentum principles:

{json.dumps(market_data, indent=2)}

Check:
1. What is the status of the Fast EMA 9 / EMA 21 dynamic on M5 and M15?
2. Is the current market session (London / NY) providing high liquidity?
3. Is there a clean micro-thrust pullback opportunity?

Submit your proposal using the `submit_scalping_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=SCALPING_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=SCALPING_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res:
            return self._fallback_scalping(market_data)
        res["agent_name"] = "Scalping_Momentum_Agent"
        return res

    def _fallback_scalping(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        m5 = market_data.get("market_structures", {}).get("m5_micro_momentum", {})
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        fast_cross = str(m5.get("fast_cross", "BULLISH")).upper()
        trend = str(h1.get("trend_bias", "BULLISH")).upper()
        m5_ema9 = float(m5.get("ema_9", 0.0) or 0.0)
        m5_ema21 = float(m5.get("ema_21", 0.0) or 0.0)

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        sl_pts = 850.0 if is_btc else 8.50
        tp1_pts = 1400.0 if is_btc else 14.00
        tp2_pts = 2800.0 if is_btc else 25.00

        # Strict Scalper Rule: Micro-momentum MUST match trade direction!
        if fast_cross == "BEARISH":
            # If fast cross is bearish, NEVER BUY!
            return {
                "agent_name": "Scalping_Momentum_Agent",
                "action": "SELL" if trend == "BEARISH" else "HOLD",
                "confidence_score": 85 if trend == "BEARISH" else 60,
                "bias": "BEARISH",
                "setup_name": "M5_Fast_EMA9_21_Micro_Bearish_Thrust",
                "entry_price": round(live_price, 2),
                "stop_loss": round(live_price + sl_pts, 2),
                "take_profit_1": round(live_price - tp1_pts, 2),
                "take_profit_2": round(live_price - tp2_pts, 2),
                "micro_momentum_status": f"M5 EMA 9 ({m5_ema9:.2f}) < EMA 21 ({m5_ema21:.2f})",
                "reasoning": f"Fast micro-momentum is BEARISH (EMA 9 below EMA 21). Buying strictly blocked."
            }
        elif fast_cross == "BULLISH":
            return {
                "agent_name": "Scalping_Momentum_Agent",
                "action": "BUY" if trend == "BULLISH" else "HOLD",
                "confidence_score": 85 if trend == "BULLISH" else 60,
                "bias": "BULLISH",
                "setup_name": "M5_Fast_EMA9_21_Micro_Bullish_Thrust",
                "entry_price": round(live_price, 2),
                "stop_loss": round(live_price - sl_pts, 2),
                "take_profit_1": round(live_price + tp1_pts, 2),
                "take_profit_2": round(live_price + tp2_pts, 2),
                "micro_momentum_status": f"M5 EMA 9 ({m5_ema9:.2f}) > EMA 21 ({m5_ema21:.2f})",
                "reasoning": f"Fast micro-momentum is BULLISH (EMA 9 holding above EMA 21). Upside thrust active."
            }
        else:
            return {
                "agent_name": "Scalping_Momentum_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "reasoning": "EMAs flat and tangled. Scalp momentum unclear."
            }

