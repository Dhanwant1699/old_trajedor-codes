"""
Market Regime Detection Specialist Agent for XAUUSD & Multi-Asset Council.
Classifies current conditions into:
1. TRENDING_BULLISH (Breakout & Trend Following Favored, Mean Reversion Gated to Pullbacks)
2. TRENDING_BEARISH (Breakdown & Short Momentum Favored, Counter-Trend Buying Gated)
3. MEAN_REVERTING_RANGE (Fade Extremes Favored, Breakouts Vetoed as False Traps)
4. HIGH_VOLATILITY_CHOP (Capital Preservation / Wider SL Mandatory, Scalp or Hold)
5. LOW_VOLATILITY_COMPRESSION (Bollinger Squeeze Coiling, Prepare for Explosive Expansion)
"""

import json
from typing import Dict, Any
from agents.llm_client import UnifiedLLMClient


REGIME_SYSTEM_PROMPT = """
You are the Market Regime Detection Specialist Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to determine the current macro and micro market regime to prevent Strategy-Regime Mismatches:
1. TRENDING_BULLISH: ADX >= 25 with +DI dominance, Choppiness < 50. Output 'BUY' bias. Breakouts and pullback continuations are active. Mean-reversion counter-trend fading is VETOED.
2. TRENDING_BEARISH: ADX >= 25 with -DI dominance, Choppiness < 50. Output 'SELL' bias. Trend breakdowns active. Counter-trend bottom picking is VETOED.
3. MEAN_REVERTING_RANGE: Choppiness >= 58 or ADX < 20. Output 'HOLD' or range boundary trades. Breakout trades are VETOED as false traps. Support/Resistance reversals favored.
4. HIGH_VOLATILITY_CHOP: Long double-sided wicks, erratic ATR. Output 'HOLD' or suggest reduced position size.
5. LOW_VOLATILITY_COMPRESSION: Bollinger Bandwidth Squeeze. Market coiling. Alert the Council for imminent breakout.

RULES:
- Strictly output your analysis and strategy guidance via the `submit_regime_proposal` tool call.
"""

REGIME_TOOL = {
    "name": "submit_regime_proposal",
    "description": "Submit Market Regime classification and strategy gating rules for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Regime_Detection_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "regime_type": {
                "type": "string",
                "enum": ["TRENDING_BULLISH", "TRENDING_BEARISH", "MEAN_REVERTING_RANGE", "HIGH_VOLATILITY_CHOP", "LOW_VOLATILITY_COMPRESSION"]
            },
            "favored_strategies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Strategies permitted in this regime (e.g. ['Trend_Momentum', 'Breakout_Squeeze'])"
            },
            "vetoed_strategies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Strategies suppressed to avoid whipsaw (e.g. ['CounterTrend_MeanReversion'])"
            },
            "reasoning": {"type": "string", "description": "Detailed quantitative breakdown of ADX, Choppiness, and Volatility"}
        },
        "required": ["action", "confidence_score", "bias", "regime_type", "reasoning"]
    }
}


class RegimeDetectionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs quantitative regime classification on live market data."""
        regime_ctx = market_data.get("market_structures", {}).get("regime_analysis", {})
        prompt = f"""
Analyze the current live market structure to classify the exact trading regime for XAUUSD:

REGIME QUANTITATIVE TELEMETRY:
{json.dumps(regime_ctx, indent=2)}

FULL MARKET DATA:
{json.dumps(market_data.get('pricing', {}), indent=2)}

Determine:
1. Is market trending strongly (ADX >= 25, Choppiness < 50) or ranging (Choppiness >= 58, ADX < 20)?
2. Which strategies must be favored and which must be suppressed to prevent whipsaw?
3. Output your ruling using `submit_regime_proposal`.
"""
        res = self.llm.call_structured(
            system_prompt=REGIME_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=REGIME_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_regime(market_data)

        res["agent_name"] = "Regime_Detection_Agent"
        return res

    def _fallback_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        regime_ctx = market_data.get("market_structures", {}).get("regime_analysis", {})
        # Prioritize H4 regime to prevent low-TF false breakouts
        regime = regime_ctx.get("h4_regime") or regime_ctx.get("regime", "TRENDING_BULLISH")
        adx = regime_ctx.get("adx_14", 25.0)
        chop = regime_ctx.get("choppiness_index", 50.0)

        if regime == "TRENDING_BULLISH":
            action = "BUY"
            bias = "BULLISH"
            conf = 88
            favored = ["Trend_Momentum", "Breakout_Squeeze", "SMC_ICT"]
            vetoed = ["CounterTrend_MeanReversion"]
            reason = f"Bullish Trend Regime Active (ADX {adx:.1f}, Chop {chop:.1f}). Trend continuations prioritized; counter-trend shorts suppressed."
        elif regime == "TRENDING_BEARISH":
            action = "SELL"
            bias = "BEARISH"
            conf = 88
            favored = ["Trend_Momentum", "Breakout_Squeeze", "Supply_Demand"]
            vetoed = ["CounterTrend_MeanReversion"]
            reason = f"Bearish Trend Regime Active (ADX {adx:.1f}, Chop {chop:.1f}). Downward momentum prioritized; counter-trend buys suppressed."
        elif regime == "MEAN_REVERTING_RANGE":
            action = "HOLD"
            bias = "NEUTRAL"
            conf = 82
            favored = ["Mean_Reversion", "Supply_Demand", "Fibonacci_OTE"]
            vetoed = ["Breakout_Squeeze"]
            reason = f"Mean-Reverting Range Regime Active (Chop {chop:.1f}, ADX {adx:.1f}). Breakouts vetoed as false traps; fade range boundaries."
        elif regime == "LOW_VOLATILITY_COMPRESSION":
            action = "HOLD"
            bias = "NEUTRAL"
            conf = 85
            favored = ["Breakout_Squeeze"]
            vetoed = ["Intraday_Scalping"]
            reason = "Volatility Compression Squeeze. Market coiling for explosive breakout; stand by for directional thrust."
        else:
            action = "HOLD"
            bias = "NEUTRAL"
            conf = 75
            favored = ["Chief_Risk_Officer"]
            vetoed = ["Aggressive_Scalp"]
            reason = f"High Volatility Rotational Chop (Chop {chop:.1f}). Preserve capital until directional clarity emerges."

        return {
            "agent_name": "Regime_Detection_Agent",
            "action": action,
            "confidence_score": conf,
            "bias": bias,
            "regime_type": regime,
            "favored_strategies": favored,
            "vetoed_strategies": vetoed,
            "reasoning": reason
        }
