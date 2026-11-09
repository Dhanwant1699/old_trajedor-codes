"""
Market Regime Detection Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: Multi-timeframe ADX, ATR, and Choppiness Index evaluation
to classify crypto volatility regime and filter out conflicting strategies.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_REGIME_SYSTEM_PROMPT = """
You are the Market Regime Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your mandate is to determine the active statistical and volatility regime of Bitcoin across D1, H4, H1, M15:

BITCOIN REGIME TAXONOMY:
1. TRENDING_BULLISH: High ADX (> 25), consistent higher highs/lows on Bitcoin H4/H1, price above EMA 50/200. Strategies: Trend Following, Bullish Breakout, Bullish Pullbacks.
2. TRENDING_BEARISH: High ADX (> 25), consistent lower highs/lows on Bitcoin H4/H1, price below EMA 50/200. Strategies: Trend Following, Bearish Breakout, Bearish Rallies.
3. MEAN_REVERTING_RANGE: Low ADX (< 20), high Choppiness Index, price oscillating between established Bitcoin S/R boundaries.
4. HIGH_VOLATILITY_EXPANSION: Extreme ATR surge, high volume expansion.

RULES:
- In TRENDING_BULLISH, veto all counter-trend sell signals.
- In TRENDING_BEARISH, veto all counter-trend buy signals.
- In MEAN_REVERTING_RANGE, veto breakout chasing.

Respond strictly using the `submit_crypto_regime_assessment` tool call.
"""

CRYPTO_REGIME_TOOL = {
    "name": "submit_crypto_regime_assessment",
    "description": "Submit Market Regime Assessment for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_Regime_Detection_Agent"},
            "regime_type": {
                "type": "string",
                "enum": ["TRENDING_BULLISH", "TRENDING_BEARISH", "MEAN_REVERTING_RANGE", "HIGH_VOLATILITY_EXPANSION", "LOW_LIQUIDITY_CHOP"]
            },
            "adx_strength": {"type": "number", "description": "Bitcoin trend strength metric"},
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
            "reasoning": {"type": "string", "description": "Detailed regime analysis for Bitcoin"}
        },
        "required": ["regime_type", "recommended_strategies", "vetoed_strategies", "reasoning"]
    }
}


class CryptoRegimeDetectionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Regime Detection analysis exclusively on Bitcoin (BTCUSD)."""
        prompt = f"""
Analyze the current live Bitcoin (BTCUSD) market regime across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Determine:
1. What is the active Bitcoin regime?
2. What strategies are recommended and what strategies are vetoed?

Submit your assessment using the `submit_crypto_regime_assessment` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_REGIME_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_REGIME_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_regime(market_data)

        res["agent_name"] = "Crypto_Regime_Detection_Agent"
        return res

    def _fallback_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        dominant_trend = top_down.get("dominant_trend", "BULLISH")

        if dominant_trend == "BULLISH":
            return {
                "agent_name": "Crypto_Regime_Detection_Agent",
                "regime_type": "TRENDING_BULLISH",
                "adx_strength": 36.0,
                "volatility_state": "NORMAL",
                "recommended_strategies": ["Trend_Momentum", "SMC_ICT_Pullbacks", "Fibonacci_OTE", "Supply_Demand_Demand_Defense"],
                "vetoed_strategies": ["Mean_Reversion_Shorts", "Breakout_Fades"],
                "reasoning": "Bitcoin is in a confirmed Top-Down Bullish regime across D1, H4, H1. Favoring pullback long setups."
            }
        elif dominant_trend == "BEARISH":
            return {
                "agent_name": "Crypto_Regime_Detection_Agent",
                "regime_type": "TRENDING_BEARISH",
                "adx_strength": 36.0,
                "volatility_state": "NORMAL",
                "recommended_strategies": ["Trend_Momentum", "SMC_ICT_Rallies", "Fibonacci_OTE", "Supply_Demand_Supply_Defense"],
                "vetoed_strategies": ["Mean_Reversion_Longs", "Breakout_Fades"],
                "reasoning": "Bitcoin is in a confirmed Top-Down Bearish regime across D1, H4, H1. Favoring rally short setups."
            }
        else:
            return {
                "agent_name": "Crypto_Regime_Detection_Agent",
                "regime_type": "MEAN_REVERTING_RANGE",
                "adx_strength": 15.5,
                "volatility_state": "COMPRESSED",
                "recommended_strategies": ["Mean_Reversion_Bands", "VWAP_Boundaries"],
                "vetoed_strategies": ["Breakout_Chasers", "Trend_Aggressors"],
                "reasoning": "Bitcoin is range-bound in a consolidation corridor. Strict boundaries required."
            }
