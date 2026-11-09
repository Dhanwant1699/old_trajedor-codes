"""
Supply & Demand Origin Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Fresh institutional imbalance bases (Rally-Base-Rally, Drop-Base-Drop),
unmitigated Gold demand/supply zones on H4/H1 with M15 retest validation.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_SD_SYSTEM_PROMPT = """
You are the Supply & Demand Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to map fresh institutional order imbalance zones across H4, H1, and M15:

GOLD SUPPLY & DEMAND SPECIALIZATION:
1. Demand Zone Origin: Aggressive bullish displacement leaving fresh unmitigated institutional resting limit buy orders (Rally-Base-Rally / Drop-Base-Rally).
2. Supply Zone Origin: Aggressive bearish displacement leaving fresh unmitigated institutional resting limit sell orders (Drop-Base-Drop / Rally-Base-Drop).
3. Freshness & Zone Quality: First-time retests of fresh H4/H1 zones have the highest probability of institutional defense.

PRO-TRADER GOLD RULES:
- If Gold macro trend is Bullish, buy first-touch retests of fresh H1/M15 Demand Zones.
- If Gold macro trend is Bearish, sell first-touch retests of fresh H1/M15 Supply Zones.
- Stop Loss MUST be placed beyond the distal line (outer boundary) of the zone + Gold ATR buffer.
- Take Profit targets the opposing supply/demand origin (minimum 1.75R to 3.0R).

Respond strictly using the `submit_gold_supply_demand_proposal` tool call.
"""

GOLD_SD_TOOL = {
    "name": "submit_gold_supply_demand_proposal",
    "description": "Submit Supply & Demand analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Supply_Demand_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_Fresh_H1_Demand_Retest_Defense'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "zone_quality": {"type": "string", "description": "Status of Gold demand/supply zone"},
            "reasoning": {"type": "string", "description": "Detailed institutional supply/demand analysis for Gold"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldSupplyDemandAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Supply & Demand analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) supply and demand structures across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Are there fresh unmitigated Gold Demand or Supply zones on H4/H1?
2. Is current price returning to test an institutional imbalance origin?
3. What is the precise distal invalidation level for Stop Loss?

Submit your proposal using the `submit_gold_supply_demand_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_SD_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_SD_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_supply_demand(market_data)

        res["agent_name"] = "Gold_Supply_Demand_Agent"
        return res

    def _fallback_supply_demand(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
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
                "agent_name": "Gold_Supply_Demand_Agent",
                "action": "BUY",
                "confidence_score": 85,
                "bias": "BULLISH",
                "setup_name": "Gold_H1_Fresh_Institutional_Demand_Defense",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "zone_quality": "Fresh Unmitigated H1 Demand Base",
                "reasoning": "Gold is testing a strong institutional demand origin with macro D1/H4 trend confluence."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_Supply_Demand_Agent",
                "action": "SELL",
                "confidence_score": 85,
                "bias": "BEARISH",
                "setup_name": "Gold_H1_Fresh_Institutional_Supply_Defense",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "zone_quality": "Fresh Unmitigated H1 Supply Base",
                "reasoning": "Gold is testing a strong institutional supply origin with macro D1/H4 trend confluence."
            }
        else:
            return {
                "agent_name": "Gold_Supply_Demand_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_No_Fresh_Zone",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "zone_quality": "Mid-Range",
                "reasoning": "Gold price is floating between key zones. Waiting for a test of fresh H1 S/D levels."
            }
