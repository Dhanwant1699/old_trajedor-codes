"""
Liquidity & Execution Quality Specialist Agent for XAUUSD & Multi-Asset Council.
Performs pre-execution microsecond auditing right before order dispatch:
- Spread Blowout Detection: Compares live spread to 50-tick rolling baseline.
- Slippage Hazard Assessment: Evaluates IOC fill probability and tick volatility.
- Liquidity Blackout Protection: Guards against news spikes and broker spread widening.
"""

import json
from typing import Dict, Any
from agents.llm_client import UnifiedLLMClient


LIQUIDITY_SYSTEM_PROMPT = """
You are the Liquidity & Execution Quality Specialist Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to evaluate real-time market microstructure and spread conditions at the point of execution:
1. Spread Deviation: Is current spread normal (<= 1.3x baseline) or blown out (> 1.8x baseline)?
2. Slippage Hazard: Will a market order suffer severe negative slippage due to thin order book depth?
3. Execution Clearance:
   - CLEAR_OPTIMAL: Spread <= 22 pts, spread ratio <= 1.3. Output 'BUY' or 'SELL' clearance.
   - SPREAD_WIDENED_CAUTION: Spread 23-35 pts, spread ratio 1.4-1.8. Permit trade only if conviction >= 90%.
   - SLIPPAGE_HAZARD_VETO: Spread > 35 pts or ratio > 2.0. Output 'HOLD' to protect prop firm balance.
   - LIQUIDITY_BLACKOUT: News release spread expansion. Output 'HOLD'.

RULES:
- Strictly output your execution audit via the `submit_liquidity_audit` tool call.
"""

LIQUIDITY_TOOL = {
    "name": "submit_liquidity_audit",
    "description": "Submit pre-execution liquidity, spread, and slippage audit for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Liquidity_Execution_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "execution_clearance": {
                "type": "string",
                "enum": ["CLEAR_OPTIMAL", "SPREAD_WIDENED_CAUTION", "SLIPPAGE_HAZARD_VETO", "LIQUIDITY_BLACKOUT"]
            },
            "current_spread_pts": {"type": "number"},
            "spread_ratio": {"type": "number"},
            "slippage_estimate_pts": {"type": "number"},
            "reasoning": {"type": "string", "description": "Execution quality and order book assessment"}
        },
        "required": ["action", "confidence_score", "bias", "execution_clearance", "reasoning"]
    }
}


class LiquidityExecutionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs pre-execution liquidity and spread audit on live tick data."""
        liq_ctx = market_data.get("market_structures", {}).get("liquidity_execution_quality", {})
        prompt = f"""
Audit the live execution quality and spread conditions for XAUUSD order placement:

LIQUIDITY & SPREAD TELEMETRY:
{json.dumps(liq_ctx, indent=2)}

PRICING:
{json.dumps(market_data.get('pricing', {}), indent=2)}

Determine:
1. Is the current spread tight and optimal for market execution?
2. Is there any slippage hazard or liquidity blackout?
3. Output your clearance decision using `submit_liquidity_audit`.
"""
        res = self.llm.call_structured(
            system_prompt=LIQUIDITY_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=LIQUIDITY_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_liquidity(market_data)

        res["agent_name"] = "Liquidity_Execution_Agent"
        return res

    def _fallback_liquidity(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        liq_ctx = market_data.get("market_structures", {}).get("liquidity_execution_quality", {})
        curr_spread = float(liq_ctx.get("current_spread_pts", 15.0) or 15.0)
        avg_spread = float(liq_ctx.get("avg_50_spread_pts", 15.0) or 15.0)
        ratio = float(liq_ctx.get("spread_ratio", 1.0) or 1.0)
        flow_bias = liq_ctx.get("flow_bias", "BALANCED_FLOW")

        if ratio > 2.2 or curr_spread > 45.0:
            clearance = "LIQUIDITY_BLACKOUT"
            action = "HOLD"
            bias = "NEUTRAL"
            conf = 95
            reason = f"Liquidity Blackout VETO: Spread blew out to {curr_spread:.1f} pts ({ratio:.2f}x average). Halting orders to prevent slippage."
        elif ratio > 1.5 or curr_spread > 25.0:
            clearance = "SPREAD_WIDENED_CAUTION"
            action = "BUY" if flow_bias == "AGGRESSIVE_BUYING" else "SELL" if flow_bias == "AGGRESSIVE_SELLING" else "HOLD"
            bias = "BULLISH" if action == "BUY" else "BEARISH" if action == "SELL" else "NEUTRAL"
            conf = 72
            reason = f"Spread Widened ({curr_spread:.1f} pts, {ratio:.2f}x avg). Execution cleared with caution; slippage buffer required."
        else:
            clearance = "CLEAR_OPTIMAL"
            action = "BUY" if flow_bias == "AGGRESSIVE_BUYING" else "SELL" if flow_bias == "AGGRESSIVE_SELLING" else "HOLD"
            bias = "BULLISH" if action == "BUY" else "BEARISH" if action == "SELL" else "NEUTRAL"
            conf = 92
            reason = f"Pristine Liquidity: Live spread {curr_spread:.1f} pts is optimal ({ratio:.2f}x baseline). Execution quality Green."

        return {
            "agent_name": "Liquidity_Execution_Agent",
            "action": action,
            "confidence_score": conf,
            "bias": bias,
            "execution_clearance": clearance,
            "current_spread_pts": curr_spread,
            "spread_ratio": ratio,
            "slippage_estimate_pts": round(curr_spread * 0.1, 2),
            "reasoning": reason
        }
