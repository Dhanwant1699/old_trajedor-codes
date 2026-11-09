"""
Tick / Order Flow Aggressor Specialist Agent for XAUUSD & Multi-Asset Council.
Microstructure leading momentum specialist:
- Analyzes trade-by-trade aggressor flow across last 100-150 ticks.
- Tracks Ask Lifters (Aggressive Buyers taking liquidity) vs Bid Hitters (Aggressive Sellers).
- Detects institutional momentum surges before 1-minute and 5-minute candles close.
"""

import json
from typing import Dict, Any
from agents.llm_client import UnifiedLLMClient


TICK_FLOW_SYSTEM_PROMPT = """
You are the Tick / Order Flow Aggressor Specialist Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to read live microstructure order flow and aggressor imbalance:
1. Ask Lifters (Buy Aggressors): When market buyers aggressively lift the offer. If >= 60%, strong leading bullish momentum.
2. Bid Hitters (Sell Aggressors): When market sellers aggressively hit the bid. If >= 60%, strong leading bearish momentum.
3. Balanced Flow: Flow between 45% and 55% indicates two-sided rotational auction. Output 'HOLD'.

RULES:
- Propose BUY if Ask Lifters >= 58% and tick velocity is positive.
- Propose SELL if Bid Hitters >= 58% and tick velocity is negative.
- Output 'HOLD' if order flow is balanced or conflicting.
- Strictly submit your analysis via the `submit_tick_flow_proposal` tool call.
"""

TICK_FLOW_TOOL = {
    "name": "submit_tick_flow_proposal",
    "description": "Submit live tick-by-tick order flow aggressor analysis for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Tick_OrderFlow_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "ask_lifters_pct": {"type": "number", "description": "Percentage of aggressive buy ticks lifting the ask"},
            "bid_hitters_pct": {"type": "number", "description": "Percentage of aggressive sell ticks hitting the bid"},
            "flow_imbalance": {"type": "string", "description": "e.g. 'HEAVY_BUY_ABSORPTION_68PCT'"},
            "reasoning": {"type": "string", "description": "Microstructure order flow interpretation"}
        },
        "required": ["action", "confidence_score", "bias", "ask_lifters_pct", "bid_hitters_pct", "reasoning"]
    }
}


class TickOrderFlowAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs live tick-by-tick order flow analysis."""
        flow_ctx = market_data.get("market_structures", {}).get("tick_order_flow", {})
        prompt = f"""
Analyze the live tick-by-tick microstructure aggressor flow for XAUUSD:

TICK ORDER FLOW TELEMETRY:
{json.dumps(flow_ctx, indent=2)}

PRICING:
{json.dumps(market_data.get('pricing', {}), indent=2)}

Determine:
1. Are aggressive buyers lifting the ask or aggressive sellers hitting the bid?
2. Is there a directional order flow surge before candle close?
3. Output your ruling using `submit_tick_flow_proposal`.
"""
        res = self.llm.call_structured(
            system_prompt=TICK_FLOW_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=TICK_FLOW_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_tick_flow(market_data)

        res["agent_name"] = "Tick_OrderFlow_Agent"
        ask_pct = float(res.get("ask_lifters_pct", flow_ctx.get("ask_lifters_pct", 50.0)) or 50.0)
        bid_pct = float(res.get("bid_hitters_pct", flow_ctx.get("bid_hitters_pct", 50.0)) or 50.0)
        res["lifter_pct"] = round(ask_pct, 1)
        res["hitter_pct"] = round(bid_pct, 1)
        res["ask_lifters_pct"] = round(ask_pct, 1)
        res["bid_hitters_pct"] = round(bid_pct, 1)
        return res

    def _fallback_tick_flow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        flow_ctx = market_data.get("market_structures", {}).get("tick_order_flow", {})
        buy_pct = float(flow_ctx.get("ask_lifters_pct", 50.0) or 50.0)
        sell_pct = float(flow_ctx.get("bid_hitters_pct", 50.0) or 50.0)
        sampled = int(flow_ctx.get("ticks_sampled", 100) or 100)

        if buy_pct >= 58.0:
            action = "BUY"
            bias = "BULLISH"
            conf = int(min(96, 70 + (buy_pct - 50) * 1.5))
            imb = f"BUY_AGGRESSORS_{buy_pct:.0f}PCT"
            reason = f"Aggressive Order Flow: Buyers lifting the ask on {buy_pct:.1f}% of last {sampled} ticks. Leading momentum positive."
        elif sell_pct >= 58.0:
            action = "SELL"
            bias = "BEARISH"
            conf = int(min(96, 70 + (sell_pct - 50) * 1.5))
            imb = f"SELL_AGGRESSORS_{sell_pct:.0f}PCT"
            reason = f"Aggressive Order Flow: Sellers hitting the bid on {sell_pct:.1f}% of last {sampled} ticks. Leading momentum downward."
        else:
            action = "HOLD"
            bias = "NEUTRAL"
            conf = 65
            imb = "BALANCED_TWO_SIDED_FLOW"
            reason = f"Balanced Flow: {buy_pct:.1f}% Ask Lifters vs {sell_pct:.1f}% Bid Hitters. No aggressive order flow breakout detected."

        return {
            "agent_name": "Tick_OrderFlow_Agent",
            "action": action,
            "confidence_score": conf,
            "bias": bias,
            "lifter_pct": round(buy_pct, 1),
            "hitter_pct": round(sell_pct, 1),
            "ask_lifters_pct": round(buy_pct, 1),
            "bid_hitters_pct": round(sell_pct, 1),
            "ask_lifters_pct": buy_pct,
            "bid_hitters_pct": sell_pct,
            "flow_imbalance": imb,
            "reasoning": reason
        }
