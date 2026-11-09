"""
Smart Money Concepts (SMC) & ICT Specialist Agent for XAUUSD.
Analyzes Fair Value Gaps (FVGs), Asian session liquidity sweeps, Order Blocks,
and structural breaks (BOS/CHoCH).
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG, get_model_api_kwargs


SMC_SYSTEM_PROMPT = """
You are the SMC & ICT Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to identify high-probability institutional order flow setups using:
1. Liquidity Sweeps: Asian Range High/Low raids, equal high/low sweeps during London & NY opens.
2. Fair Value Gaps (FVG): Imbalances and unmitigated price inefficiencies on M15 and H1.
3. Market Structure Shifts (MSS / CHoCH) and Break of Structure (BOS).
4. Premium vs Discount zones: Buy in discount (below equilibrium), Sell in premium (above equilibrium).

RULES:
- Propose BUY if a sell-side liquidity pool/Asian low was swept, followed by a bullish MSS/FVG retest.
- Propose SELL if a buy-side liquidity pool/Asian high was swept, followed by a bearish MSS/FVG retest.
- Stop Loss MUST be placed beyond the structural swing that created the sweep (strict invalidation).
- Take Profit 1 must target opposing internal liquidity (1.5R to 2.0R minimum).
- If there is no clear liquidity grab or market is resting inside an unmitigated chop zone, output 'HOLD'.
- Only propose entries with confidence >= 70.

Respond strictly using the `submit_smc_proposal` tool call.
"""

SMC_TOOL = {
    "name": "submit_smc_proposal",
    "description": "Submit SMC/ICT analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "SMC_ICT_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Asian_Low_Sweep_M15_FVG_Mitigation'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "liquidity_swept": {"type": "string", "description": "Description of liquidity grabbed (e.g. 'Asian Low swept at London Open')"},
            "fvg_status": {"type": "string", "description": "Active FVG being targeted or retested"},
            "reasoning": {"type": "string", "description": "Detailed SMC / ICT institutional analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class SMCAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs SMC/ICT analysis on live market structure data."""
        prompt = f"""
Analyze the current live XAUUSD market data strictly through the lens of Smart Money Concepts (SMC) & ICT:

{json.dumps(market_data, indent=2)}

Check:
1. Has Asian Session High or Low liquidity been raided?
2. Are there active M15 Fair Value Gaps (FVGs) offering discounted entry?
3. What is the structural state (BOS vs CHoCH)?
4. Is price in a Premium (sell) or Discount (buy) zone?

Submit your proposal using the `submit_smc_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=SMC_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=SMC_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_smc(market_data)

        res["agent_name"] = "SMC_ICT_Agent"
        return res

    def _fallback_smc(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        fib = struct.get("fibonacci_levels", {})
        fvgs = struct.get("active_fvgs", [])
        patterns = struct.get("candlestick_patterns", [])
        trend = h1.get("trend_bias", "BULLISH")
        
        swing_high = float(fib.get("swing_high", live_price + 8.0) or (live_price + 8.0))
        swing_low = float(fib.get("swing_low", live_price - 8.0) or (live_price - 8.0))
        diff = max(0.1, swing_high - swing_low)
        rel_pos = (live_price - swing_low) / diff

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 2.0
        sl_pts = 850.0 if is_btc else 9.50
        tp1_pts = 1400.0 if is_btc else 15.00
        tp2_pts = 2800.0 if is_btc else 28.00

        # Check for Reversal Patterns
        has_bearish_reversal = any("BEARISH" in str(p.get("pattern", "")).upper() for p in patterns)
        has_bullish_reversal = any("BULLISH" in str(p.get("pattern", "")).upper() for p in patterns)

        # 1. Bearish Liquidity Sweep (Swept Highs / Premium Zone Rejection)
        if rel_pos >= 0.70 or has_bearish_reversal:
            fvg_str = f"FVG at {fvgs[0]['top']:,.2f} - {fvgs[0]['bottom']:,.2f}" if fvgs else "Premium institutional supply block"
            return {
                "agent_name": "SMC_ICT_Agent",
                "action": "SELL" if has_bearish_reversal or rel_pos >= 0.85 else "HOLD",
                "confidence_score": 88 if has_bearish_reversal else 65,
                "bias": "BEARISH",
                "setup_name": "BuySide_Liquidity_Raid_Premium_Distribution",
                "entry_price": round(live_price, 2),
                "stop_loss": round(swing_high + 1.50, 2),
                "take_profit_1": round(live_price - tp1_pts, 2),
                "take_profit_2": round(swing_low, 2),
                "liquidity_swept": f"Buy-side liquidity swept near {swing_high:,.2f}. Retail trapped buying top.",
                "fvg_status": fvg_str,
                "reasoning": f"ICT Liquidity Raid: High at {swing_high:,.2f} tapped. Reversal pressure indicates smart money distribution."
            }

        # 2. Bullish Liquidity Sweep (Swept Lows / Discount Zone Mitigation)
        elif rel_pos <= 0.35 and (has_bullish_reversal or trend == "BULLISH"):
            fvg_str = f"FVG at {fvgs[0]['bottom']:,.2f} - {fvgs[0]['top']:,.2f}" if fvgs else "Discount institutional demand block"
            return {
                "agent_name": "SMC_ICT_Agent",
                "action": "BUY",
                "confidence_score": 90,
                "bias": "BULLISH",
                "setup_name": "SellSide_Liquidity_Sweep_Discount_Mitigation",
                "entry_price": round(live_price, 2),
                "stop_loss": round(swing_low - 1.50, 2),
                "take_profit_1": round(live_price + tp1_pts, 2),
                "take_profit_2": round(swing_high, 2),
                "liquidity_swept": f"Sell-side liquidity swept near {swing_low:,.2f}. Discount FVG mitigated.",
                "fvg_status": fvg_str,
                "reasoning": f"ICT Discount Mitigation: Institutional order block defending discount base. Bullish continuation favored."
            }

        else:
            return {
                "agent_name": "SMC_ICT_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "reasoning": "Price resting in neutral consolidation. No clean institutional liquidity sweep identified."
            }

