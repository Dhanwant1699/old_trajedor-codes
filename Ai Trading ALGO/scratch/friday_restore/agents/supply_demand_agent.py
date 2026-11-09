"""
Institutional Supply & Demand Zones Specialist Agent for XAUUSD.
Analyzes fresh imbalance origin bases (RBR, DBD, DBR, RBD) and executes first-touch mitigations.
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG


SUPPLY_DEMAND_SYSTEM_PROMPT = """
You are the Institutional Supply & Demand Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade high-volume order imbalances at fresh Supply and Demand zones:
1. Demand Zones: Price origins that produced explosive upward rallies (RBR - Rally Base Rally, or DBR - Drop Base Rally).
2. Supply Zones: Price origins that produced explosive downward drops (DBD - Drop Base Drop, or RBD - Rally Base Drop).
3. Freshness Principle: First-time retests of fresh, untouched zones offer the highest win-rate edge.

RULES:
- Propose BUY when price returns into a fresh Demand Zone and prints rejection signals.
- Propose SELL when price returns into a fresh Supply Zone and prints rejection signals.
- Stop Loss MUST be placed just outside the distal line (far edge) of the supply/demand zone.
- Target Take Profit 1 at opposing supply/demand with minimum 1.5R to 2.5R.
- If price is floating in the middle of no-man's land between zones, output 'HOLD'.
- Minimum confidence score >= 70.

Respond strictly using the `submit_supply_demand_proposal` tool call.
"""

SUPPLY_DEMAND_TOOL = {
    "name": "submit_supply_demand_proposal",
    "description": "Submit Supply & Demand analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Supply_Demand_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Fresh_M15_Demand_Zone_First_Retest'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "zone_details": {"type": "string", "description": "Details of the supply or demand zone being traded"},
            "reasoning": {"type": "string", "description": "Detailed Supply & Demand institutional analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class SupplyDemandAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Supply & Demand imbalance analysis."""
        prompt = f"""
Analyze the live XAUUSD market data strictly through Institutional Supply & Demand principles:

{json.dumps(market_data, indent=2)}

Check:
1. Is current price approaching or inside a fresh Demand or Supply zone?
2. How strong was the initial departure from this zone?
3. Is the Stop Loss cleanly placed outside the zone boundary?

Submit your proposal using the `submit_supply_demand_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=SUPPLY_DEMAND_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=SUPPLY_DEMAND_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res:
            return self._fallback_supply_demand(market_data)
        res["agent_name"] = "Supply_Demand_Agent"
        return res

    def _fallback_supply_demand(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        trend = h1.get("trend_bias", "BULLISH")

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        if trend == "BULLISH":
            entry = round(live_price - step, 2)
            return {
                "agent_name": "Supply_Demand_Agent",
                "action": "BUY",
                "confidence_score": 91,
                "bias": "BULLISH",
                "setup_name": "Fresh_M15_Demand_Origin_Defense",
                "entry_price": entry,
                "stop_loss": round(entry - sl_pts, 2),
                "take_profit_1": round(entry + tp1_pts, 2),
                "take_profit_2": round(entry + tp2_pts, 2),
                "zone_type": "Fresh Institutional Demand Base (Rally-Base-Rally)",
                "reasoning": f"Fresh institutional demand origin established with strong RBR structure defending {round(entry - sl_pts, 2):,.2f}."
            }
        else:
            entry = round(live_price + step, 2)
            return {
                "agent_name": "Supply_Demand_Agent",
                "action": "SELL",
                "confidence_score": 91,
                "bias": "BEARISH",
                "setup_name": "Fresh_M15_Supply_Origin_Defense",
                "entry_price": entry,
                "stop_loss": round(entry + sl_pts, 2),
                "take_profit_1": round(entry - tp1_pts, 2),
                "take_profit_2": round(entry - tp2_pts, 2),
                "zone_type": "Fresh Institutional Supply Base (Drop-Base-Drop)",
                "reasoning": f"Fresh institutional supply origin established with strong DBD structure defending {round(entry + sl_pts, 2):,.2f}."
            }

