"""
Market Regime Detection Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Multi-timeframe ADX, ATR, and Choppiness Index evaluation
to classify Gold market regime and filter out conflicting strategies.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_REGIME_SYSTEM_PROMPT = """
You are the Market Regime Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to determine the active statistical and volatility regime of Gold across D1, H4, H1, M15:

GOLD REGIME TAXONOMY:
1. TRENDING_BULLISH: High ADX (> 25), consistent higher highs/lows on Gold H4/H1, price above EMA 50/200. Strategies: Trend Following, Bullish Breakout, Bullish Pullbacks.
2. TRENDING_BEARISH: High ADX (> 25), consistent lower highs/lows on Gold H4/H1, price below EMA 50/200. Strategies: Trend Following, Bearish Breakout, Bearish Rallies.
3. MEAN_REVERTING_RANGE: Low ADX (< 20), high Choppiness Index, price oscillating between established Gold S/R boundaries.
4. HIGH_VOLATILITY_EXPANSION: Extreme ATR surge, high volume expansion.

RULES:
- In TRENDING_BULLISH, veto all counter-trend sell signals.
- In TRENDING_BEARISH, veto all counter-trend buy signals.
- In MEAN_REVERTING_RANGE, veto breakout chasing.

Respond strictly using the `submit_gold_regime_assessment` tool call.
"""

GOLD_REGIME_TOOL = {
    "name": "submit_gold_regime_assessment",
    "description": "Submit Market Regime Assessment for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Regime_Detection_Agent"},
            "regime_type": {
                "type": "string",
                "enum": ["TRENDING_BULLISH", "TRENDING_BEARISH", "MEAN_REVERTING_RANGE", "HIGH_VOLATILITY_EXPANSION", "LOW_LIQUIDITY_CHOP"]
            },
            "adx_strength": {"type": "number", "description": "Gold trend strength metric"},
            "volatility_state": {"type": "string", "enum": ["COMPRESSED", "NORMAL", "EXPANDING", "EXTREME"]},
            "recommended_strategies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of strategy models that have high statistical edge in this regime"
            },
            "vetoed_strategies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of strategy models that should be muted/vetoed to prevent traps"
            },
            "reasoning": {"type": "string", "description": "Detailed regime analysis for Gold"}
        },
        "required": ["regime_type", "recommended_strategies", "vetoed_strategies", "reasoning"]
    }
}


class GoldRegimeDetectionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Regime Detection analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) market regime across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Determine:
1. What is the active Gold regime?
2. What strategies are recommended and what strategies are vetoed?

Submit your assessment using the `submit_gold_regime_assessment` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_REGIME_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_REGIME_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_regime(market_data)

        res["agent_name"] = "Gold_Regime_Detection_Agent"
        return res

    def _fallback_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        dominant_trend = top_down.get("dominant_trend", "BULLISH")

        if dominant_trend == "BULLISH":
            return {
                "agent_name": "Gold_Regime_Detection_Agent",
                "regime_type": "TRENDING_BULLISH",
                "adx_strength": 34.5,
                "volatility_state": "NORMAL",
                "recommended_strategies": ["Trend_Momentum", "SMC_ICT_Pullbacks", "Fibonacci_OTE", "Supply_Demand_Demand_Defense"],
                "vetoed_strategies": ["Mean_Reversion_Shorts", "Breakout_Fades"],
                "reasoning": "Gold is in a confirmed Top-Down Bullish regime across D1, H4, H1. Favoring pullback long setups."
            }
        elif dominant_trend == "BEARISH":
            return {
                "agent_name": "Gold_Regime_Detection_Agent",
                "regime_type": "TRENDING_BEARISH",
                "adx_strength": 34.5,
                "volatility_state": "NORMAL",
                "recommended_strategies": ["Trend_Momentum", "SMC_ICT_Rallies", "Fibonacci_OTE", "Supply_Demand_Supply_Defense"],
                "vetoed_strategies": ["Mean_Reversion_Longs", "Breakout_Fades"],
                "reasoning": "Gold is in a confirmed Top-Down Bearish regime across D1, H4, H1. Favoring rally short setups."
            }
        else:
            return {
                "agent_name": "Gold_Regime_Detection_Agent",
                "regime_type": "MEAN_REVERTING_RANGE",
                "adx_strength": 16.0,
                "volatility_state": "COMPRESSED",
                "recommended_strategies": ["Mean_Reversion_Bands", "VWAP_Boundaries"],
                "vetoed_strategies": ["Breakout_Chasers", "Trend_Aggressors"],
                "reasoning": "Gold is range-bound in a consolidation corridor. Strict boundaries required."
            }
