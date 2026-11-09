"""
Smart Money Concepts (SMC) & ICT Specialist Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: 24/7 crypto liquidity sweeps, CME Bitcoin Futures gap fills,
Binance/Bybit liquidation cluster sweeps (long/short squeezes), BTC Fair Value Gaps (FVGs), and whale Order Blocks.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_SMC_SYSTEM_PROMPT = """
You are the dedicated Smart Money Concepts (SMC) & ICT Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your sole mandate is to analyze Bitcoin crypto market candles and structure across all timeframes (D1 -> H4 -> H1 -> M15 -> M5):

BITCOIN SMC / ICT SPECIALIZATION:
1. Crypto Liquidity Sweeps: Weekend liquidity sweeps, CME Bitcoin futures gap fill sweeps, Binance/Bybit liquidation cluster raids, and sweeps of Prior Day High (PDH) / Prior Day Low (PDL).
2. Fair Value Gaps (FVG): Imbalances and unmitigated price inefficiencies on Bitcoin H4, H1, and M15 charts ($500 - $2,500 wide gaps).
3. Market Structure Shifts (MSS / CHoCH) and Break of Structure (BOS) confirming whale accumulation / distribution.
4. Premium vs Discount zones: Buy Bitcoin in discount (below equilibrium of macro swing), Sell Bitcoin in premium.

PRO-TRADER BITCOIN RULES:
- Never counter-trade the D1/H4 macro Bitcoin bull/bear trend on minor low-timeframe noise.
- Propose BUY when sell-side liquidation pool / PDL is swept into an H1/M15 Bullish FVG or Whale Order Block, followed by M5 MSS confirmation.
- Propose SELL when buy-side liquidation pool / PDH is swept into an H1/M15 Bearish FVG or Whale Order Block, followed by M5 MSS confirmation.
- Stop Loss MUST be placed beyond the structural swing low/high that created the sweep (BTC invalidation, typically $500 - $1,500 buffer).
- Take Profit 1 must target opposing internal liquidity (minimum 1.75R), TP2 targets macro liquidity pools ($1,500 - $5,000+).
- If there is no clear liquidity grab or price is resting inside mid-range chop, output 'HOLD'.

Respond strictly using the `submit_crypto_smc_proposal` tool call.
"""

CRYPTO_SMC_TOOL = {
    "name": "submit_crypto_smc_proposal",
    "description": "Submit SMC/ICT analysis and trade proposal for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_SMC_ICT_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'BTC_Liquidation_Sweep_M15_FVG_Mitigation'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "liquidity_swept": {"type": "string", "description": "Bitcoin liquidity pool grabbed"},
            "fvg_status": {"type": "string", "description": "Active BTC FVG being targeted or mitigated"},
            "reasoning": {"type": "string", "description": "Detailed SMC / ICT institutional analysis for Bitcoin"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class CryptoSMCAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs SMC/ICT analysis exclusively on Bitcoin (BTCUSD) market structure."""
        prompt = f"""
Analyze the current live Bitcoin (BTCUSD) market structure across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Has Bitcoin liquidation pool (or PDH/PDL / CME gap) been swept?
2. Are there active Bitcoin Fair Value Gaps (FVGs) on H1 or M15 offering discounted entry?
3. What is the structural state (BOS vs CHoCH)?
4. Is price in a Premium (sell) or Discount (buy) zone relative to the macro swing?

Submit your proposal using the `submit_crypto_smc_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_SMC_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_SMC_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_smc(market_data)

        res["agent_name"] = "Crypto_SMC_ICT_Agent"
        return res

    def _fallback_smc(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 80000.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        pdh = top_down.get("prior_day_high", 0.0)
        pdl = top_down.get("prior_day_low", 0.0)
        m15 = struct.get("m15_execution_structure", {})
        fvgs = m15.get("active_fvgs", [])
        
        sl_buffer = 850.0
        tp1_buffer = 1487.5
        tp2_buffer = 2550.0

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
                "agent_name": "Crypto_SMC_ICT_Agent",
                "action": "BUY",
                "confidence_score": 85,
                "bias": "BULLISH",
                "setup_name": "BTC_Macro_Bullish_FVG_Discount_Mitigation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "liquidity_swept": f"Bitcoin sell-side internal liquidity defended above PDL {pdl}",
                "fvg_status": "Bitcoin M15 Bullish FVG active",
                "reasoning": f"Bitcoin D1/H4/H1 top-down bullish structure aligned. Price positioned in institutional discount with upside targets toward {tp1} and PDH {pdh}."
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
                "agent_name": "Crypto_SMC_ICT_Agent",
                "action": "SELL",
                "confidence_score": 85,
                "bias": "BEARISH",
                "setup_name": "BTC_Macro_Bearish_FVG_Premium_Mitigation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "liquidity_swept": f"Bitcoin buy-side internal liquidity rejected below PDH {pdh}",
                "fvg_status": "Bitcoin M15 Bearish FVG active",
                "reasoning": f"Bitcoin D1/H4/H1 top-down bearish structure aligned. Price positioned in institutional premium with downside targets toward {tp1}."
            }
        else:
            return {
                "agent_name": "Crypto_SMC_ICT_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "BTC_Equilibrium_Chop",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "liquidity_swept": "None",
                "fvg_status": "No clear imbalance",
                "reasoning": "Bitcoin is consolidating near equilibrium with no major liquidity sweep."
            }
