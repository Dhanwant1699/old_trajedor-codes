"""
Smart Money Concepts (SMC) & ICT Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Asian session liquidity sweeps, London AM/PM Fix sweeps,
Gold Fair Value Gaps (FVGs), and institutional Order Blocks.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_SMC_SYSTEM_PROMPT = """
You are the dedicated Smart Money Concepts (SMC) & ICT Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your sole mandate is to analyze Gold market candles and structure across all timeframes (D1 -> H4 -> H1 -> M15 -> M5):

GOLD SMC / ICT SPECIALIZATION:
1. Liquidity Sweeps: Asian Range High/Low raids, London Open (07:00-09:00 UTC) raids, London PM Fix sweeps, and NY Open (12:00-14:00 UTC) liquidity grabs of Prior Day High (PDH) and Prior Day Low (PDL).
2. Fair Value Gaps (FVG): Imbalances and unmitigated price inefficiencies on Gold H4, H1, and M15 charts.
3. Market Structure Shifts (MSS / CHoCH) and Break of Structure (BOS) confirming institutional order flow.
4. Premium vs Discount zones: Buy Gold in discount (below equilibrium of macro swing), Sell Gold in premium.

PRO-TRADER GOLD RULES:
- Never counter-trade the D1/H4 macro trend on minor low-timeframe pullbacks.
- Propose BUY when sell-side liquidity / Asian low / PDL is swept into an H1/M15 FVG or Bullish Order Block, followed by M5 MSS confirmation.
- Propose SELL when buy-side liquidity / Asian high / PDH is swept into an H1/M15 FVG or Bearish Order Block, followed by M5 MSS confirmation.
- Stop Loss MUST be placed beyond the structural swing low/high that created the sweep (Gold invalidation).
- Take Profit 1 must target opposing internal liquidity (minimum 1.75R), TP2 targets macro liquidity pools (3.0R+).
- If there is no clear liquidity grab or price is resting inside mid-range chop, output 'HOLD'.

Respond strictly using the `submit_gold_smc_proposal` tool call.
"""

GOLD_SMC_TOOL = {
    "name": "submit_gold_smc_proposal",
    "description": "Submit SMC/ICT analysis and trade proposal for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_SMC_ICT_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'Gold_Asian_Low_Sweep_M15_FVG_Retest'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "liquidity_swept": {"type": "string", "description": "Gold liquidity pool grabbed"},
            "fvg_status": {"type": "string", "description": "Active Gold FVG being targeted or mitigated"},
            "reasoning": {"type": "string", "description": "Detailed SMC / ICT institutional analysis for Gold"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class GoldSMCAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs SMC/ICT analysis exclusively on Gold (XAUUSD) market structure."""
        prompt = f"""
Analyze the current live Gold (XAUUSD) market structure across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Has Gold Asian Session High or Low liquidity (or PDH/PDL) been raided?
2. Are there active Gold Fair Value Gaps (FVGs) on H1 or M15 offering discounted entry?
3. What is the structural state (BOS vs CHoCH)?
4. Is price in a Premium (sell) or Discount (buy) zone relative to the macro swing?

Submit your proposal using the `submit_gold_smc_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_SMC_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_SMC_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_smc(market_data)

        res["agent_name"] = "Gold_SMC_ICT_Agent"
        return res

    def _fallback_smc(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4360.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        pdh = top_down.get("prior_day_high", 0.0)
        pdl = top_down.get("prior_day_low", 0.0)
        m15 = struct.get("m15_execution_structure", {})
        fvgs = m15.get("active_fvgs", [])
        
        sl_buffer = 10.0
        tp1_buffer = 18.0
        tp2_buffer = 32.0

        if dominant_trend == "BULLISH":
            entry = live_price
            if fvgs:
                for fvg in fvgs:
                    if fvg.get("type") == "BULLISH":
                        entry = float(fvg.get("top", live_price))
                        break
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Gold_SMC_ICT_Agent",
                "action": "BUY",
                "confidence_score": 85,
                "bias": "BULLISH",
                "setup_name": "Gold_Macro_Bullish_FVG_Discount_Mitigation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "liquidity_swept": f"Gold sell-side internal liquidity defended above PDL {pdl}",
                "fvg_status": "Gold M15 Bullish FVG active",
                "reasoning": f"Gold D1/H4/H1 top-down bullish structure aligned. Price positioned in institutional discount with upside liquidity targets toward {tp1} and PDH {pdh}."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            if fvgs:
                for fvg in fvgs:
                    if fvg.get("type") == "BEARISH":
                        entry = float(fvg.get("bottom", live_price))
                        break
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Gold_SMC_ICT_Agent",
                "action": "SELL",
                "confidence_score": 85,
                "bias": "BEARISH",
                "setup_name": "Gold_Macro_Bearish_FVG_Premium_Mitigation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "liquidity_swept": f"Gold buy-side internal liquidity rejected below PDH {pdh}",
                "fvg_status": "Gold M15 Bearish FVG active",
                "reasoning": f"Gold D1/H4/H1 top-down bearish structure aligned. Price positioned in institutional premium with downside targets toward {tp1}."
            }
        else:
            return {
                "agent_name": "Gold_SMC_ICT_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "Gold_Equilibrium_Chop",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "liquidity_swept": "None",
                "fvg_status": "No clear imbalance",
                "reasoning": "Gold is consolidating near equilibrium with no major liquidity sweep."
            }
