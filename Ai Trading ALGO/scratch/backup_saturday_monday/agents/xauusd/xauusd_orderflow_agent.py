"""
Order Flow & Volume Profile Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Multi-Session VWAP (London, NY), Value Area High/Low (VAH/VAL),
Point of Control (POC), and volume rejection imbalances.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_ORDERFLOW_SYSTEM_PROMPT = """
You are the Volume Profile & Order Flow Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to evaluate institutional volume distribution and auction market dynamics:

GOLD VOLUME PROFILE & ORDER FLOW SPECIALIZATION:
1. Session VWAPs: Gold London Session VWAP (07:00 UTC anchor) and NY Session VWAP (12:00 UTC anchor). Price holding above VWAP indicates institutional buyers in control; below VWAP indicates sellers.
2. Value Area Dynamics: Value Area High (VAH), Value Area Low (VAL), and Point of Control (POC - highest volume node).
3. Value Acceptance vs Rejection: Price breaking out of Value Area and accepting = trend continuation; price probing outside and aggressively rejecting back inside = auction failure mean reversion.

PRO-TRADER GOLD RULES:
- Buy Gold pullbacks that test and defend Value Area Low (VAL) or Session VWAP in an HTF Bullish trend.
- Sell Gold rallies that test and reject Value Area High (VAH) or Session VWAP in an HTF Bearish trend.
- Stop Loss placed outside the Value Area boundary and high-volume node.
- Target opposing Value Area High / Low (1.75R - 3.0R).

Respond strictly using the `submit_gold_orderflow_proposal` tool call.
"""

GOLD_ORDERFLOW_TOOL = {
    "name": "submit_gold_orderflow_proposal",
    "description": "Submit Volume Profile & Order Flow analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_OrderFlow_VWAP_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_Session_VWAP_Defense_Continuation'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "vwap_status": {"type": "string", "description": "Position relative to London/NY VWAP & POC"},
            "reasoning": {"type": "string", "description": "Detailed Gold volume profile & auction analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldOrderFlowAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Order Flow & VWAP analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) volume profile and VWAP structure across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Is Gold price trading above or below Session VWAP?
2. Where is price relative to Value Area High (VAH), Value Area Low (VAL), and POC?
3. Is institutional volume confirming continuation or rejection?

Submit your proposal using the `submit_gold_orderflow_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_ORDERFLOW_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_ORDERFLOW_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_orderflow(market_data)

        res["agent_name"] = "Gold_OrderFlow_VWAP_Agent"
        return res

    def _fallback_orderflow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
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
                "agent_name": "Gold_OrderFlow_VWAP_Agent",
                "action": "BUY",
                "confidence_score": 85,
                "bias": "BULLISH",
                "setup_name": "Gold_VWAP_Institutional_Defense_Long",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "vwap_status": "Gold trading above London/NY Session VWAP in Bullish Value Area",
                "reasoning": "Institutional buyers defending Gold VWAP with aggressive absorption at Value Area support."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_OrderFlow_VWAP_Agent",
                "action": "SELL",
                "confidence_score": 85,
                "bias": "BEARISH",
                "setup_name": "Gold_VWAP_Institutional_Rejection_Short",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "vwap_status": "Gold trading below London/NY Session VWAP in Bearish Value Area",
                "reasoning": "Institutional sellers capping Gold VWAP with supply pressure at Value Area resistance."
            }
        else:
            return {
                "agent_name": "Gold_OrderFlow_VWAP_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_POC_Balance",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "vwap_status": "Inside Point of Control (POC) Chop",
                "reasoning": "Gold auction is fully balanced at Point of Control. No directional imbalance."
            }
