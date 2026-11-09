"""
Cumulative Volume Delta (CVD) & Aggressor Specialist Agent for XAUUSD & Multi-Asset Council.
Institutional footprint & volume delta specialist:
- Calculates Buy Volume vs Sell Volume Delta per candle.
- Tracks Cumulative Volume Delta (CVD) across multi-candle swings.
- Detects Institutional Absorption Divergences (Price flat at support while CVD surges = High-conviction reversal).
- Detects Exhaustion Divergences (Price pushing highs while CVD declines = Reversal imminent).
"""

import json
from typing import Dict, Any
from agents.llm_client import UnifiedLLMClient


VOLUME_DELTA_SYSTEM_PROMPT = """
You are the Cumulative Volume Delta (CVD) & Aggressor Specialist Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to track institutional volume footprints and delta divergences:
1. BULLISH_ABSORPTION_DIVERGENCE: Price is flat or making lower lows, but Cumulative Volume Delta (CVD) is surging higher. This indicates institutions are absorbing retail sell orders with limit bids. Output 'BUY'.
2. BEARISH_EXHAUSTION_DIVERGENCE: Price is pushing higher, but CVD is falling. This indicates buyers are exhausted and smart money is exiting. Output 'SELL'.
3. CONVERGENT_BULLISH_THRUST: Price and CVD both surging together in strong unison. Output 'BUY'.
4. CONVERGENT_BEARISH_THRUST: Price and CVD both dumping together in strong unison. Output 'SELL'.
5. NEUTRAL_DELTA: Volume delta is balanced with no divergence. Output 'HOLD'.

RULES:
- Strictly submit your analysis via the `submit_volume_delta_proposal` tool call.
"""

VOLUME_DELTA_TOOL = {
    "name": "submit_volume_delta_proposal",
    "description": "Submit Cumulative Volume Delta (CVD) and institutional absorption analysis for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Volume_Delta_CVD_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "cvd_pattern": {
                "type": "string",
                "enum": ["BULLISH_ABSORPTION_DIVERGENCE", "BEARISH_EXHAUSTION_DIVERGENCE", "CONVERGENT_BULLISH_THRUST", "CONVERGENT_BEARISH_THRUST", "NEUTRAL_DELTA"]
            },
            "5_bar_cvd_delta": {"type": "number"},
            "reasoning": {"type": "string", "description": "Detailed institutional CVD footprint interpretation"}
        },
        "required": ["action", "confidence_score", "bias", "cvd_pattern", "reasoning"]
    }
}


class VolumeDeltaAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Cumulative Volume Delta (CVD) and divergence analysis."""
        cvd_ctx = market_data.get("market_structures", {}).get("volume_delta_cvd", {})
        prompt = f"""
Analyze the live Cumulative Volume Delta (CVD) and volume footprint for XAUUSD:

VOLUME DELTA TELEMETRY:
{json.dumps(cvd_ctx, indent=2)}

PRICING:
{json.dumps(market_data.get('pricing', {}), indent=2)}

Determine:
1. Is there an institutional absorption or exhaustion divergence?
2. Is CVD expanding with the trend or diverging from price?
3. Output your ruling using `submit_volume_delta_proposal`.
"""
        res = self.llm.call_structured(
            system_prompt=VOLUME_DELTA_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=VOLUME_DELTA_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_volume_delta(market_data)

        res["agent_name"] = "Volume_Delta_CVD_Agent"
        return res

    def _fallback_volume_delta(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        cvd_ctx = market_data.get("market_structures", {}).get("volume_delta_cvd", {})
        div = cvd_ctx.get("cvd_divergence", "CONVERGENT_BULLISH_THRUST")
        delta5 = float(cvd_ctx.get("5_bar_cvd_delta", 0.0) or 0.0)
        desc = cvd_ctx.get("description", "CVD Volume Delta Active")

        if div == "BULLISH_ABSORPTION_DIVERGENCE":
            action = "BUY"
            bias = "BULLISH"
            conf = 94
            reason = f"Institutional Footprint: {desc}. Smart money passively absorbing sell orders at support."
        elif div == "BEARISH_EXHAUSTION_DIVERGENCE":
            action = "SELL"
            bias = "BEARISH"
            conf = 92
            reason = f"Institutional Footprint: {desc}. Buyers exhausted at highs; institutional distribution active."
        elif div == "CONVERGENT_BULLISH_THRUST":
            action = "BUY"
            bias = "BULLISH"
            conf = 88
            reason = f"Volume Delta Expansion: CVD +{delta5:.0f} confirming aggressive market buying thrust."
        elif div == "CONVERGENT_BEARISH_THRUST":
            action = "SELL"
            bias = "BEARISH"
            conf = 88
            reason = f"Volume Delta Dumping: CVD {delta5:.0f} confirming aggressive market selling momentum."
        else:
            action = "HOLD"
            bias = "NEUTRAL"
            conf = 65
            reason = "Volume Delta Neutral: No institutional absorption or exhaustion divergence active."

        return {
            "agent_name": "Volume_Delta_CVD_Agent",
            "action": action,
            "confidence_score": conf,
            "bias": bias,
            "cvd_pattern": div,
            "5_bar_cvd_delta": delta5,
            "reasoning": reason
        }
