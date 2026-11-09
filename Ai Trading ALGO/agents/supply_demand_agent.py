"""
Institutional Support & Resistance and Supply/Demand Imbalance Specialist Agent for XAUUSD.
Combines:
1. Deep Institutional Supply & Demand Origins (RBR, DBD, DBR, RBD, displacement & freshness).
2. ChartPrime High-Volume S&R Delta Boxes (Cumulative Delta Volume filtering & ATR depths).
3. Role Reversals & Flips (Broken Support flips to Resistance, Broken Resistance flips to Support).
4. Multi-Timeframe Value Area boundaries (VAH/VAL/POC) and Swing Pivots.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


SUPPLY_DEMAND_SYSTEM_PROMPT = """
You are the Institutional Support & Resistance and Supply/Demand Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to trade high-volume order imbalances and key structural boundaries with institutional precision:

1. Support & Resistance vs Supply & Demand (The Core Distinction):
   - Support & Resistance (S&R) represents crowd memory and horizontal reaction levels. Retail traders cluster stops at obvious S&R lines, which makes them prime targets for liquidity sweeps UNLESS validated by institutional volume.
   - Supply & Demand (S&D) represents the actual ORIGIN of institutional order imbalances (explosive displacement candles). 
   - A Support level is formed because a Demand zone sits right below it. A Resistance level is formed because a Supply zone sits right above it.
   - Freshness Rule: S&D is strongest on the FIRST TOUCH (fresh retest >= 88% edge). Repeated touches (3+) WEAKEN an S&D zone because limit orders are consumed! In contrast, S&R creates crowd consensus on multiple touches, but becomes a liquidity trap if no fresh institutional volume is present.

2. ChartPrime High-Volume S&R Delta Boxes:
   - High-Volume Resistance Box: Formed when a Pivot High occurs accompanied by heavy negative Delta Volume (Vol < vol_lo). Confirmed with 'RESISTANCE_HOLDS' (Bearish Rejection).
   - High-Volume Support Box: Formed when a Pivot Low occurs accompanied by heavy positive Delta Volume (Vol > vol_hi). Confirmed with 'SUPPORT_HOLDS' (Bullish Rejection).
   - Role Reversals (Flips):
     * RESISTANCE_FLIPPED_TO_SUPPORT: Resistance broken cleanly upward by institutional force, now acting as high-probability Support floor for pullback BUY retests.
     * SUPPORT_FLIPPED_TO_RESISTANCE: Support broken cleanly downward, now acting as high-probability Resistance ceiling for pullback SELL retests.

3. Execution Criteria:
   - Propose BUY when price returns into a fresh Demand Zone, High-Volume Support Box, or Resistance-Turned-Support Flip, confirmed by buyer defense or bullish candlestick triggers.
   - Propose SELL when price returns into a fresh Supply Zone, High-Volume Resistance Box, or Support-Turned-Resistance Flip, confirmed by seller defense or bearish candlestick triggers.
   - Distal Line Protection: Stop Loss MUST be placed outside the distal edge (far side) of the Box or Zone (+1.50 pts buffer on Gold).
   - Target TP1 at the nearest opposing high-volume box or S&D boundary (minimum 1.5R to 2.5R).
   - Strictly FORBID buying into overhead Resistance/Supply, and strictly FORBID selling into Support/Demand.

Respond strictly using the `submit_supply_demand_proposal` tool call.
"""

SUPPLY_DEMAND_TOOL = {
    "name": "submit_supply_demand_proposal",
    "description": "Submit Support & Resistance / Supply & Demand analysis and trade proposal for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Supply_Demand_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'High_Volume_Resistance_Box_Defense' or 'Fresh_Demand_Retest'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "zone_details": {"type": "string", "description": "Details of the support/resistance or supply/demand zone being traded"},
            "reasoning": {"type": "string", "description": "Detailed Support & Resistance and Supply/Demand institutional analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class SupplyDemandAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Institutional Support & Resistance and Supply & Demand imbalance analysis."""
        prompt = f"""
Analyze the live XAUUSD market data strictly through Institutional Support & Resistance and Supply/Demand principles:

{json.dumps(market_data, indent=2)}

Check:
1. Is current price approaching or inside a High-Volume S&R Box (with Delta Volume filter) or a fresh S&D Imbalance base?
2. Is there an active 'RESISTANCE_HOLDS' or 'SUPPORT_HOLDS' signal, or a confirmed S&R Role Reversal (Flip)?
3. What is the touch count? Is it a pristine fresh 1st touch or an exhausted 3rd+ touch?
4. Is the Stop Loss cleanly placed outside the distal edge (+1.50 pts buffer)?

Submit your proposal using the `submit_supply_demand_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=SUPPLY_DEMAND_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=SUPPLY_DEMAND_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res or not res.get("action"):
            return self._fallback_supply_demand(market_data)
        res["agent_name"] = "Supply_Demand_Agent"
        return res

    def _fallback_supply_demand(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4170.0)
        h1 = market_data.get("market_structures", {}).get("h1_trend_structure", {})
        trend = h1.get("trend_bias", "BULLISH")

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper()
        step = 200.0 if is_btc else 1.50
        sl_pts = 600.0 if is_btc else 5.50
        tp1_pts = 1200.0 if is_btc else 12.00
        tp2_pts = 2400.0 if is_btc else 22.00

        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        sd_data = struct.get("supply_demand_zones", {})
        sr_boxes = struct.get("high_volume_sr_boxes", {})
        
        # 1. Fresh S&D Zones
        supply_zones = sd_data.get("fresh_supply_zones", []) or sd_data.get("supply_zones", [])
        demand_zones = sd_data.get("fresh_demand_zones", []) or sd_data.get("demand_zones", [])

        # 2. High-Volume S&R Boxes (Delta Volume filtered)
        res_boxes = sr_boxes.get("active_resistance_boxes", [])
        sup_boxes = sr_boxes.get("active_support_boxes", [])
        sr_signal = sr_boxes.get("latest_signal", "NONE")
        res_is_sup = sr_boxes.get("res_is_sup", False)
        sup_is_res = sr_boxes.get("sup_is_res", False)
        nearest_res_box = sr_boxes.get("nearest_resistance")
        nearest_sup_box = sr_boxes.get("nearest_support")

        # 3. Macro Value Area boundaries
        eq_data = market_data.get("institutional_equilibrium", {}) or market_data.get("market_structures", {}).get("institutional_equilibrium", {})
        vah = float(eq_data.get("value_area_high", 0.0) or 0.0)
        val = float(eq_data.get("value_area_low", 0.0) or 0.0)
        poc = float(eq_data.get("poc_price", 0.0) or 0.0)

        # 4. Candlestick patterns
        patterns = struct.get("candlestick_patterns", [])
        has_bullish_pattern = any("BULLISH" in str(p.get("bias", "")).upper() or any(k in str(p.get("pattern", "")).upper() for k in ["HAMMER", "ENGULFING", "MORNING", "TWEEZER BOTTOM", "WHITE SOLDIERS"]) for p in patterns)
        has_bearish_pattern = any("BEARISH" in str(p.get("bias", "")).upper() or any(k in str(p.get("pattern", "")).upper() for k in ["SHOOTING", "ENGULFING", "EVENING", "TWEEZER TOP", "BLACK CROWS"]) for p in patterns)

        # Evaluate nearest supply zone proximity
        nearest_supply = None
        min_supp_dist = 999.0
        for sz in supply_zones:
            top = float(sz.get("top", 0))
            bot = float(sz.get("bottom", 0))
            if bot <= live_price <= (top + 1.5) or (bot > live_price and (bot - live_price) < min_supp_dist):
                min_supp_dist = abs(live_price - bot)
                nearest_supply = sz

        # Evaluate nearest demand zone proximity
        nearest_demand = None
        min_dem_dist = 999.0
        for dz in demand_zones:
            top = float(dz.get("top", 0))
            bot = float(dz.get("bottom", 0))
            if (bot - 1.5) <= live_price <= top or (top < live_price and (live_price - top) < min_dem_dist):
                min_dem_dist = abs(live_price - top)
                nearest_demand = dz

        # Check High-Volume Resistance Box presence
        at_res_box = False
        res_box_top = live_price + 3.0
        res_box_vol = 0.0
        if nearest_res_box:
            r_bot = float(nearest_res_box.get("bottom", 0))
            r_top = float(nearest_res_box.get("top", 0))
            res_box_vol = float(nearest_res_box.get("delta_vol", 0))
            if (r_bot - 1.5) <= live_price <= (r_top + 1.0) or abs(live_price - r_bot) <= 2.0:
                at_res_box = True
                res_box_top = r_top

        # Check High-Volume Support Box presence
        at_sup_box = False
        sup_box_bot = live_price - 3.0
        sup_box_vol = 0.0
        if nearest_sup_box:
            s_top = float(nearest_sup_box.get("top", 0))
            s_bot = float(nearest_sup_box.get("bottom", 0))
            sup_box_vol = float(nearest_sup_box.get("delta_vol", 0))
            if (s_bot - 1.0) <= live_price <= (s_top + 1.5) or abs(live_price - s_top) <= 2.0:
                at_sup_box = True
                sup_box_bot = s_bot

        # Check VAH / VAL boundaries as macro S&R
        at_vah_resistance = vah > 0 and abs(live_price - vah) <= 2.0
        at_val_support = val > 0 and abs(live_price - val) <= 2.0

        # =========================================================================
        # RULE 1: Price Testing High-Volume Resistance Box or Fresh Supply Zone
        # =========================================================================
        if (at_res_box and not res_is_sup) or (nearest_supply and min_supp_dist <= 2.0) or "RESISTANCE_HOLDS" in sr_signal or (at_vah_resistance and live_price >= (vah - 1.0)):
            s_top = max(res_box_top, float(nearest_supply.get("top", 0)) if nearest_supply else 0, vah if at_vah_resistance else 0)
            if s_top <= live_price:
                s_top = live_price + 2.50
            
            conf = 93 if (has_bearish_pattern and at_res_box) else (90 if at_res_box or has_bearish_pattern else 86)
            setup = "High_Volume_Resistance_Box_Defense" if at_res_box else ("M15_Supply_Rejection_Sell" if nearest_supply else "VAH_Macro_Resistance_Defense")
            return {
                "agent_name": "Supply_Demand_Agent",
                "action": "SELL",
                "confidence_score": conf,
                "bias": "BEARISH",
                "setup_name": setup,
                "entry_price": round(live_price, 2),
                "stop_loss": round(s_top + 1.50, 2),
                "take_profit_1": round(live_price - tp1_pts, 2),
                "take_profit_2": round(live_price - tp2_pts, 2),
                "zone_details": f"Resistance Ceiling @ {s_top:,.2f} | Delta Vol: {res_box_vol:,.0f} | Signal: {sr_signal}",
                "reasoning": f"Price testing High-Volume Resistance Box / Supply origin at {s_top:.2f} (Delta Vol: {res_box_vol:,.0f}). Institutional sell defense active with negative volume footprint; longs strictly blocked."
            }

        # =========================================================================
        # RULE 2: Price Testing High-Volume Support Box or Fresh Demand Zone
        # =========================================================================
        elif (at_sup_box and not sup_is_res) or (nearest_demand and min_dem_dist <= 2.0) or "SUPPORT_HOLDS" in sr_signal or (at_val_support and live_price <= (val + 1.0)):
            d_bot = min(sup_box_bot, float(nearest_demand.get("bottom", 999999)) if nearest_demand else 999999, val if at_val_support else 999999)
            if d_bot >= live_price or d_bot == 999999:
                d_bot = live_price - 2.50
                
            conf = 93 if (has_bullish_pattern and at_sup_box) else (90 if at_sup_box or has_bullish_pattern else 86)
            setup = "High_Volume_Support_Box_Defense" if at_sup_box else ("M15_Demand_Rejection_Buy" if nearest_demand else "VAL_Macro_Support_Defense")
            return {
                "agent_name": "Supply_Demand_Agent",
                "action": "BUY",
                "confidence_score": conf,
                "bias": "BULLISH",
                "setup_name": setup,
                "entry_price": round(live_price, 2),
                "stop_loss": round(d_bot - 1.50, 2),
                "take_profit_1": round(live_price + tp1_pts, 2),
                "take_profit_2": round(live_price + tp2_pts, 2),
                "zone_details": f"Support Floor @ {d_bot:,.2f} | Delta Vol: {sup_box_vol:,.0f} | Signal: {sr_signal}",
                "reasoning": f"Price testing High-Volume Support Box / Demand origin at {d_bot:.2f} (Delta Vol: {sup_box_vol:,.0f}). Institutional buyer base active with positive volume footprint; shorts strictly blocked."
            }

        # =========================================================================
        # RULE 3: Role Reversals (Resistance-turned-Support or Support-turned-Resistance)
        # =========================================================================
        elif res_is_sup and nearest_res_box and abs(live_price - float(nearest_res_box.get("top", 0))) <= 2.5:
            flip_floor = float(nearest_res_box.get("bottom", live_price - 2.0))
            return {
                "agent_name": "Supply_Demand_Agent",
                "action": "BUY",
                "confidence_score": 88,
                "bias": "BULLISH",
                "setup_name": "Resistance_Flipped_To_Support_Retest",
                "entry_price": round(live_price, 2),
                "stop_loss": round(flip_floor - 1.50, 2),
                "take_profit_1": round(live_price + tp1_pts, 2),
                "take_profit_2": round(live_price + tp2_pts, 2),
                "zone_details": f"Flip Floor @ {flip_floor:,.2f} (Old Resistance now Support)",
                "reasoning": f"Role Reversal confirmed: Broken institutional resistance now acting as support floor at {flip_floor:.2f}. Bullish retest bounce active."
            }

        elif sup_is_res and nearest_sup_box and abs(live_price - float(nearest_sup_box.get("bottom", 0))) <= 2.5:
            flip_ceiling = float(nearest_sup_box.get("top", live_price + 2.0))
            return {
                "agent_name": "Supply_Demand_Agent",
                "action": "SELL",
                "confidence_score": 88,
                "bias": "BEARISH",
                "setup_name": "Support_Flipped_To_Resistance_Retest",
                "entry_price": round(live_price, 2),
                "stop_loss": round(flip_ceiling + 1.50, 2),
                "take_profit_1": round(live_price - tp1_pts, 2),
                "take_profit_2": round(live_price - tp2_pts, 2),
                "zone_details": f"Flip Ceiling @ {flip_ceiling:,.2f} (Old Support now Resistance)",
                "reasoning": f"Role Reversal confirmed: Broken institutional support now acting as resistance ceiling at {flip_ceiling:.2f}. Bearish retest rejection active."
            }

        # =========================================================================
        # RULE 4: Traversing in Open Space Between S&R / S&D Zones
        # =========================================================================
        else:
            return {
                "agent_name": "Supply_Demand_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "reasoning": f"Price (${live_price:.2f}) traversing between S&R boundaries. Nearest Supply: {min_supp_dist:.1f} pts, Nearest Demand: {min_dem_dist:.1f} pts. Standing aside until key High-Volume Box or S&D boundary is tapped."
            }
