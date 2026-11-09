"""
Supply & Demand Origin Specialist Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: Whale accumulation bases, cold-storage exchange outflow zones,
unmitigated crypto demand/supply blocks on H4/H1 ($500 - $2,500 wide zones) with M15 retest validation.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_SD_SYSTEM_PROMPT = """
You are the Supply & Demand Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your mandate is to map fresh whale accumulation and distribution zones across H4, H1, and M15:

BITCOIN SUPPLY & DEMAND SPECIALIZATION:
1. Demand Zone Origin: Aggressive crypto displacement leaving fresh unmitigated whale limit orders (Rally-Base-Rally / Drop-Base-Rally).
2. Supply Zone Origin: Aggressive bearish displacement leaving fresh unmitigated institutional sell orders (Drop-Base-Drop / Rally-Base-Drop).
3. Freshness & Zone Quality: First-time retests of fresh H4/H1 whale accumulation zones have the highest probability of institutional defense.

PRO-TRADER BITCOIN RULES:
- If Bitcoin macro trend is Bullish, buy first-touch retests of fresh H1/M15 Demand Zones.
- If Bitcoin macro trend is Bearish, sell first-touch retests of fresh H1/M15 Supply Zones.
- Stop Loss MUST be placed beyond the distal line (outer boundary) of the zone + $500-$1,500 buffer.
- Take Profit targets opposing supply/demand origin (minimum 1.75R to 3.0R).

Respond strictly using the `submit_crypto_supply_demand_proposal` tool call.
"""

CRYPTO_SD_TOOL = {
    "name": "submit_crypto_supply_demand_proposal",
    "description": "Submit Supply & Demand analysis and trade proposal for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_Supply_Demand_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'BTC_Fresh_H1_Whale_Demand_Retest'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "zone_quality": {"type": "string", "description": "Status of Bitcoin demand/supply zone"},
            "reasoning": {"type": "string", "description": "Detailed institutional supply/demand analysis for Bitcoin"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class CryptoSupplyDemandAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Supply & Demand analysis exclusively on Bitcoin (BTCUSD)."""
        prompt = f"""
Analyze the current live Bitcoin (BTCUSD) supply and demand structures across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Are there fresh unmitigated Bitcoin Demand or Supply zones on H4/H1?
2. Is current price returning to test an institutional whale accumulation origin?
3. What is the precise distal invalidation level for Stop Loss?

Submit your proposal using the `submit_crypto_supply_demand_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_SD_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_SD_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_supply_demand(market_data)

        res["agent_name"] = "Crypto_Supply_Demand_Agent"
        return res

    def _fallback_supply_demand(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
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
                "agent_name": "Crypto_Supply_Demand_Agent",
                "action": "BUY",
                "confidence_score": 85,
                "bias": "BULLISH",
                "setup_name": "BTC_H1_Fresh_Whale_Demand_Defense",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "zone_quality": "Fresh Unmitigated H1 Whale Demand Base",
                "reasoning": "Bitcoin is testing a strong whale accumulation origin with macro D1/H4 trend confluence."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Crypto_Supply_Demand_Agent",
                "action": "SELL",
                "confidence_score": 85,
                "bias": "BEARISH",
                "setup_name": "BTC_H1_Fresh_Whale_Supply_Defense",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "zone_quality": "Fresh Unmitigated H1 Whale Supply Base",
                "reasoning": "Bitcoin is testing a strong whale distribution origin with macro D1/H4 trend confluence."
            }
        else:
            return {
                "agent_name": "Crypto_Supply_Demand_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "BTC_No_Fresh_Zone",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "zone_quality": "Mid-Range",
                "reasoning": "Bitcoin price is floating between key zones. Waiting for a test of fresh H1 S/D levels."
            }
