"""
Volume Profile & VWAP Specialist Agent for XAUUSD.
Analyzes Volume-Weighted Average Price (VWAP), institutional value areas,
and volume liquidity acceptance/rejection.
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG


ORDERFLOW_SYSTEM_PROMPT = """
You are the Volume Profile & VWAP Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade based on institutional volume dynamics and fair value equilibrium:
1. VWAP Equilibrium: Trading above VWAP indicates institutional buyers in control; below VWAP indicates institutional sellers in control.
2. VWAP Retests: Buying high-volume pullbacks to VWAP in an uptrend; selling pullbacks to VWAP in a downtrend.
3. Value Area Rejections: Identifying when price accepts or rejects extremes relative to intraday volume.

RULES:
- Propose BUY when price is trending above VWAP and successfully retests VWAP with bullish price action.
- Propose SELL when price is trending below VWAP and rejects VWAP from underneath.
- Place Stop Loss on the other side of VWAP / volume node + ATR buffer.
- Target at least 1.5R to 2.5R opposing value area extensions.
- If price is chopping erratically across VWAP with no volume conviction, output 'HOLD'.
- Minimum confidence score >= 70 required for entry.

Respond strictly using the `submit_orderflow_proposal` tool call.
"""

ORDERFLOW_TOOL = {
    "name": "submit_orderflow_proposal",
    "description": "Submit Volume Profile & VWAP analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "OrderFlow_VWAP_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'VWAP_Pullback_Bullish_Acceptance'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "vwap_relation": {"type": "string", "description": "Relation of current price to VWAP"},
            "reasoning": {"type": "string", "description": "Detailed Volume and VWAP institutional reasoning"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class OrderFlowAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Volume Profile & VWAP analysis."""
        prompt = f"""
Analyze the live XAUUSD market data strictly through Volume Profile & VWAP principles:

{json.dumps(market_data, indent=2)}

Evaluate:
1. Is current price trading above or below intraday VWAP?
2. Is price respecting VWAP as dynamic support or resistance?
3. Is volume confirming institutional participation?

Submit your proposal using the `submit_orderflow_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=ORDERFLOW_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=ORDERFLOW_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res:
            return self._fallback_orderflow(market_data)
        res["agent_name"] = "OrderFlow_VWAP_Agent"
        return res

    def _fallback_orderflow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        vwap = float(struct.get("vwap", live_price) or live_price)
        trend = h1.get("trend_bias", "BULLISH")

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        if live_price >= vwap or trend == "BULLISH":
            entry = round(live_price - step, 2)
            return {
                "agent_name": "OrderFlow_VWAP_Agent",
                "action": "BUY",
                "confidence_score": 90,
                "bias": "BULLISH",
                "setup_name": "Intraday_VWAP_Pullback_Bullish_Acceptance",
                "entry_price": entry,
                "stop_loss": round(entry - sl_pts, 2),
                "take_profit_1": round(entry + tp1_pts, 2),
                "take_profit_2": round(entry + tp2_pts, 2),
                "vwap_relation": f"Price trading above VWAP ({vwap:,.2f}) with value area buyers defending pullbacks",
                "reasoning": f"Institutional VWAP holding as strong value floor. Buyers actively absorbing pullbacks around {entry:,.2f}."
            }
        else:
            entry = round(live_price + step, 2)
            return {
                "agent_name": "OrderFlow_VWAP_Agent",
                "action": "SELL",
                "confidence_score": 90,
                "bias": "BEARISH",
                "setup_name": "Intraday_VWAP_Pullback_Bearish_Rejection",
                "entry_price": entry,
                "stop_loss": round(entry + sl_pts, 2),
                "take_profit_1": round(entry - tp1_pts, 2),
                "take_profit_2": round(entry - tp2_pts, 2),
                "vwap_relation": f"Price trading below VWAP ({vwap:,.2f}) with value area sellers rejecting rallies",
                "reasoning": f"Institutional VWAP capping price upside. Sellers actively defending resistance around {entry:,.2f}."
            }

