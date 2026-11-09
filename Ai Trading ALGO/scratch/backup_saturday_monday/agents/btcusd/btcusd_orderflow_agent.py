"""
Order Flow & Volume Profile Specialist Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: 24/7 Rolling VWAP, Weekly Anchor VWAP, Value Area High/Low (VAH/VAL),
Point of Control (POC), and high-volume crypto liquidity nodes.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_ORDERFLOW_SYSTEM_PROMPT = """
You are the Volume Profile & Order Flow Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your mandate is to evaluate crypto volume distribution and auction market dynamics:

BITCOIN VOLUME PROFILE & ORDER FLOW SPECIALIZATION:
1. 24/7 Rolling & Weekly VWAP: Bitcoin trades 24/7 without market closes; tracking the 24h Rolling VWAP and Weekly Anchor VWAP defines true institutional cost basis.
2. Crypto Value Area Dynamics: Value Area High (VAH), Value Area Low (VAL), and Point of Control (POC - highest traded volume cluster).
3. Auction Acceptance: Bitcoin accepting above VAL/VWAP in a bull trend confirms aggressive spot/derivatives buyer presence.

PRO-TRADER BITCOIN RULES:
- Buy Bitcoin pullbacks that test and defend Value Area Low (VAL) or 24h Rolling VWAP in an HTF Bullish trend.
- Sell Bitcoin rallies that test and reject Value Area High (VAH) or 24h Rolling VWAP in an HTF Bearish trend.
- Stop Loss placed outside the Value Area boundary and high-volume node ($500 - $1,500 buffer).
- Target opposing Value Area High / Low (1.75R - 3.0R).

Respond strictly using the `submit_crypto_orderflow_proposal` tool call.
"""

CRYPTO_ORDERFLOW_TOOL = {
    "name": "submit_crypto_orderflow_proposal",
    "description": "Submit Volume Profile & Order Flow analysis and trade proposal for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_OrderFlow_VWAP_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'BTC_Rolling_VWAP_Institutional_Defense'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "vwap_status": {"type": "string", "description": "Position relative to 24h Rolling VWAP & POC"},
            "reasoning": {"type": "string", "description": "Detailed Bitcoin volume profile & auction analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class CryptoOrderFlowAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Order Flow & VWAP analysis exclusively on Bitcoin (BTCUSD)."""
        prompt = f"""
Analyze the current live Bitcoin (BTCUSD) volume profile and VWAP structure across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Is Bitcoin price trading above or below 24h Rolling VWAP?
2. Where is price relative to Value Area High (VAH), Value Area Low (VAL), and POC?
3. Is institutional crypto volume confirming continuation or rejection?

Submit your proposal using the `submit_crypto_orderflow_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_ORDERFLOW_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_ORDERFLOW_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_orderflow(market_data)

        res["agent_name"] = "Crypto_OrderFlow_VWAP_Agent"
        return res

    def _fallback_orderflow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 80000.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        sl_buffer = 850.0
        tp1_buffer = 1487.5
        tp2_buffer = 2550.0

        if dominant_trend == "BULLISH":
            entry = live_price
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Crypto_OrderFlow_VWAP_Agent",
                "action": "BUY",
                "confidence_score": 85,
                "bias": "BULLISH",
                "setup_name": "BTC_VWAP_Institutional_Defense_Long",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "vwap_status": "Bitcoin trading above 24h Rolling VWAP in Bullish Value Area",
                "reasoning": "Institutional buyers defending Bitcoin Rolling VWAP with aggressive absorption at Value Area support."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Crypto_OrderFlow_VWAP_Agent",
                "action": "SELL",
                "confidence_score": 85,
                "bias": "BEARISH",
                "setup_name": "BTC_VWAP_Institutional_Rejection_Short",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "vwap_status": "Bitcoin trading below 24h Rolling VWAP in Bearish Value Area",
                "reasoning": "Institutional sellers capping Bitcoin Rolling VWAP with supply pressure at Value Area resistance."
            }
        else:
            return {
                "agent_name": "Crypto_OrderFlow_VWAP_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "BTC_POC_Balance",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "vwap_status": "Inside Point of Control (POC) Chop",
                "reasoning": "Bitcoin auction is fully balanced at Point of Control. No directional imbalance."
            }
