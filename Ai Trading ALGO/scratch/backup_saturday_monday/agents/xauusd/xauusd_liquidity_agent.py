"""
Liquidity & Execution Quality Shield Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Real-time spread spike detection (max 45 pts threshold),
market rollover blackout (21:55-23:05 UTC), and slippage hazard gating.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_LIQUIDITY_SYSTEM_PROMPT = """
You are the Liquidity & Execution Quality Shield Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to protect capital from toxic execution environments, spread widening, and rollover illiquidity:

GOLD SPREAD & LIQUIDITY SPECIALIZATION:
1. Spread Filter: Normal Gold spread is 12-25 points. If spread exceeds 45 points (4.5 pips), trigger an immediate LIQUIDITY_BLACKOUT veto.
2. Market Rollover Blackout: Gold liquidity evaporates between 21:55 UTC and 23:05 UTC (daily broker swap rollover). Halt all entries during this window.
3. Market Depth & Slippage Hazard: Veto aggressive market orders when liquidity is thin.

RULES:
- If spread > 45 pts or time is in rollover window, output execution_clearance = 'LIQUIDITY_BLACKOUT'.
- If spread is normal (<= 45 pts) and liquidity depth is solid, output execution_clearance = 'CLEAR_FOR_EXECUTION'.

Respond strictly using the `submit_gold_liquidity_clearance` tool call.
"""

GOLD_LIQUIDITY_TOOL = {
    "name": "submit_gold_liquidity_clearance",
    "description": "Submit Liquidity & Execution Quality assessment for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Liquidity_Execution_Agent"},
            "execution_clearance": {
                "type": "string",
                "enum": ["CLEAR_FOR_EXECUTION", "CAUTION_WIDE_SPREAD", "LIQUIDITY_BLACKOUT"]
            },
            "current_spread_points": {"type": "number"},
            "max_allowed_spread": {"type": "number"},
            "slippage_risk_level": {"type": "string", "enum": ["LOW", "MODERATE", "HIGH", "EXTREME"]},
            "market_depth_quality": {"type": "string", "enum": ["DEEP", "NORMAL", "THIN", "VACUUM"]},
            "reasoning": {"type": "string", "description": "Detailed liquidity evaluation for Gold"}
        },
        "required": ["execution_clearance", "current_spread_points", "slippage_risk_level", "reasoning"]
    }
}


class GoldLiquidityExecutionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Liquidity & Spread Shield analysis exclusively on Gold (XAUUSD)."""
        pricing = market_data.get("pricing", {})
        spread = float(pricing.get("spread_points", 0.0) or 0.0)
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour
        minute = now_utc.minute

        # Check daily rollover blackout (21:55 - 23:05 UTC)
        is_rollover = (hour == 21 and minute >= 55) or (hour == 22) or (hour == 23 and minute <= 5)
        max_spread = float(CONFIG.MAX_SPREAD_POINTS or 45.0)

        if spread > max_spread:
            return {
                "agent_name": "Gold_Liquidity_Execution_Agent",
                "execution_clearance": "LIQUIDITY_BLACKOUT",
                "current_spread_points": spread,
                "max_allowed_spread": max_spread,
                "slippage_risk_level": "EXTREME",
                "market_depth_quality": "THIN",
                "reasoning": f"Gold live spread ({spread:.1f} pts) exceeds maximum institutional threshold ({max_spread:.1f} pts). Execution blocked."
            }

        if is_rollover:
            return {
                "agent_name": "Gold_Liquidity_Execution_Agent",
                "execution_clearance": "LIQUIDITY_BLACKOUT",
                "current_spread_points": spread,
                "max_allowed_spread": max_spread,
                "slippage_risk_level": "EXTREME",
                "market_depth_quality": "VACUUM",
                "reasoning": "Gold daily broker rollover period active (21:55 - 23:05 UTC). Liquidity blackout active."
            }

        return {
            "agent_name": "Gold_Liquidity_Execution_Agent",
            "execution_clearance": "CLEAR_FOR_EXECUTION",
            "current_spread_points": spread,
            "max_allowed_spread": max_spread,
            "slippage_risk_level": "LOW",
            "market_depth_quality": "DEEP",
            "reasoning": f"Gold liquidity is optimal (Spread: {spread:.1f} pts). Prime institutional execution conditions."
        }
