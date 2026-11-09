"""
Stage 3: M5 Candle Confirmation, Microstructure Order Flow & No-Chase Trigger Engine.

Non-negotiable institutional execution rules:
1. Closed M5 Candle Confirmation Only:
   Never enters on a forming, unclosed candle. Evaluates the most recent closed M5 candle.
   Requires price-action structure (Engulfing, Pinbar/Rejection Wick >= 40%, CHoCH/MSS, or Solid Body Rebound).
2. Volume Confirmation:
   Closed candle volume >= 1.25x rolling 20-period average M5 volume.
3. Order Flow Imbalance:
   BUY requires ask-lifters >= 55% and bid-hitters < 60%.
   SELL requires bid-hitters >= 55% and ask-lifters < 60%.
   Opposing aggressive order flow vetoes entry.
4. Strict No-Chase Rule:
   Price must not have run more than 0.30 * ATR away from the planned entry level.
   If price drifted beyond 0.30 ATR, entry is skipped/aborted.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd

from config import CONFIG
from core.trade_plan import TradePlan, TradeDirection

logger = logging.getLogger(__name__)


class M5TriggerEngine:
    """
    Evaluates Stage 3 trigger conditions on closed M5 candle and live tick flow.
    """

    def __init__(
        self,
        max_chase_atr: Optional[float] = None,
        min_lifters_pct: Optional[float] = None,
        min_hitters_pct: Optional[float] = None,
        min_vol_mult: float = 1.25,
        min_wick_ratio: float = 0.40,
    ):
        self.max_chase_atr: float = (
            max_chase_atr if max_chase_atr is not None else float(getattr(CONFIG, "MAX_ENTRY_CHASE_ATR", 0.30))
        )
        self.min_lifters_pct: float = (
            min_lifters_pct if min_lifters_pct is not None else float(getattr(CONFIG, "MIN_ORDERFLOW_LIFTERS_PCT", 55.0))
        )
        self.min_hitters_pct: float = (
            min_hitters_pct if min_hitters_pct is not None else float(getattr(CONFIG, "MIN_ORDERFLOW_HITTERS_PCT", 55.0))
        )
        self.min_vol_mult: float = min_vol_mult
        self.min_wick_ratio: float = min_wick_ratio

    def check_no_chase(self, live_price: float, planned_entry: float, atr: float) -> Tuple[bool, str, float]:
        """
        Validates that live price has not run more than max_chase_atr * ATR away from planned entry.
        Returns: (passed: bool, reason: str, chase_distance: float)
        """
        chase_dist = abs(live_price - planned_entry)
        max_allowed = round(self.max_chase_atr * atr, 2)
        if chase_dist > max_allowed:
            return (
                False,
                f"No-Chase Violation: Price {live_price:.2f} drifted {chase_dist:.2f} pts from planned entry {planned_entry:.2f} (max {self.max_chase_atr:.2f} ATR = {max_allowed:.2f} pts). Never chase!",
                chase_dist,
            )
        return True, f"Within allowed chase band ({chase_dist:.2f} <= {max_allowed:.2f} pts)", chase_dist

    def check_order_flow(self, tick_flow_data: Dict[str, Any], direction: str) -> Tuple[bool, str]:
        """
        Validates microstructure order flow:
        - BUY needs ask_lifters >= min_lifters_pct and no heavy aggressive selling.
        - SELL needs bid_hitters >= min_hitters_pct and no heavy aggressive buying.
        """
        direction = direction.upper()
        lifters = float(tick_flow_data.get("ask_lifters_pct", 50.0) or 50.0)
        hitters = float(tick_flow_data.get("bid_hitters_pct", 50.0) or 50.0)

        if direction == "BUY":
            if lifters < self.min_lifters_pct:
                return (
                    False,
                    f"Insufficient buy aggressors: Ask-lifters {lifters:.1f}% < minimum {self.min_lifters_pct:.1f}%",
                )
            if hitters >= 60.0:
                return (
                    False,
                    f"Opposing aggressive selling: Bid-hitters {hitters:.1f}% >= 60% vetoes BUY",
                )
        elif direction == "SELL":
            if hitters < self.min_hitters_pct:
                return (
                    False,
                    f"Insufficient sell aggressors: Bid-hitters {hitters:.1f}% < minimum {self.min_hitters_pct:.1f}%",
                )
            if lifters >= 60.0:
                return (
                    False,
                    f"Opposing aggressive buying: Ask-lifters {lifters:.1f}% >= 60% vetoes SELL",
                )
        return True, f"Order flow confirmed ({direction}: lifters={lifters:.1f}%, hitters={hitters:.1f}%)"

    def check_closed_candle_confirmation(
        self,
        df_m5: pd.DataFrame,
        direction: str,
        entry_zone_low: float = 0.0,
        entry_zone_high: float = 0.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates the most recently closed M5 candle (df_m5.iloc[-2]) against the prior closed candle (iloc[-3]).
        Checks:
        1. Bullish/Bearish pattern (Engulfing, Pinbar/Rejection Wick >= 40%, MSS/CHoCH, Solid Rebound).
        2. Candle tested/touched the planned entry zone (if zone provided).
        3. Volume >= 1.25x rolling 20-period average volume.
        """
        direction = direction.upper()
        if df_m5 is None or len(df_m5) < 3:
            return False, "Insufficient M5 candle history", {}

        # iloc[-1] is active forming candle; iloc[-2] is the last completed/closed candle
        c_closed = df_m5.iloc[-2]
        c_prev = df_m5.iloc[-3] if len(df_m5) >= 3 else c_closed

        o = float(c_closed["open"])
        h = float(c_closed["high"])
        l = float(c_closed["low"])
        c = float(c_closed["close"])
        candle_range = max(0.01, h - l)

        prev_o = float(c_prev["open"])
        prev_h = float(c_prev["high"])
        prev_l = float(c_prev["low"])
        prev_c = float(c_prev["close"])

        # Volume calculation using prior closed candles
        vol_col = "tick_volume" if "tick_volume" in df_m5.columns else ("volume" if "volume" in df_m5.columns else None)
        curr_vol = float(c_closed[vol_col]) if vol_col else 100.0
        if vol_col and len(df_m5) > 2:
            prior_vols = df_m5[vol_col].iloc[:-2]
            window_vols = prior_vols.iloc[-20:] if len(prior_vols) >= 20 else prior_vols
            avg_vol = float(window_vols.mean()) if len(window_vols) > 0 else max(1.0, curr_vol)
        else:
            avg_vol = max(1.0, curr_vol)

        vol_ratio = curr_vol / max(1.0, avg_vol)
        vol_confirmed = vol_ratio >= self.min_vol_mult

        # Wicks
        lower_wick = max(0.0, min(o, c) - l)
        upper_wick = max(0.0, h - max(o, c))
        lower_wick_ratio = lower_wick / candle_range
        upper_wick_ratio = upper_wick / candle_range

        pattern_name = "NONE"
        pattern_confirmed = False

        if direction == "BUY":
            # 1. Bullish Engulfing
            if (c > o) and (prev_c <= prev_o) and (c >= prev_o) and (o <= prev_c):
                pattern_name = "BULLISH_ENGULFING"
                pattern_confirmed = True
            # 2. Hammer / Lower Rejection Wick (buyers stepped in from lows)
            elif lower_wick_ratio >= self.min_wick_ratio and (c >= o or abs(c - o) <= (candle_range * 0.35)):
                pattern_name = f"BULLISH_PINBAR_HAMMER (Lower Wick {lower_wick_ratio*100:.0f}%)"
                pattern_confirmed = True
            # 3. Bullish CHoCH / MSS (close above prior high)
            elif c > prev_h and c > o:
                pattern_name = "BULLISH_MSS_CHOCH"
                pattern_confirmed = True
            # 4. Bullish solid expansion bar
            elif c > o and ((c - o) >= (candle_range * 0.50)) and c > prev_c:
                pattern_name = "BULLISH_EXPANSION_BAR"
                pattern_confirmed = True
        else:
            # 1. Bearish Engulfing
            if (c < o) and (prev_c >= prev_o) and (c <= prev_o) and (o >= prev_c):
                pattern_name = "BEARISH_ENGULFING"
                pattern_confirmed = True
            # 2. Shooting Star / Upper Rejection Wick (sellers slammed highs)
            elif upper_wick_ratio >= self.min_wick_ratio and (c <= o or abs(c - o) <= (candle_range * 0.35)):
                pattern_name = f"BEARISH_SHOOTING_STAR (Upper Wick {upper_wick_ratio*100:.0f}%)"
                pattern_confirmed = True
            # 3. Bearish CHoCH / MSS (close below prior low)
            elif c < prev_l and c < o:
                pattern_name = "BEARISH_MSS_CHOCH"
                pattern_confirmed = True
            # 4. Bearish solid expansion bar
            elif c < o and ((o - c) >= (candle_range * 0.50)) and c < prev_c:
                pattern_name = "BEARISH_EXPANSION_BAR"
                pattern_confirmed = True

        # Zone Touch Check (Candle must test the planned zone)
        zone_touched = True
        if entry_zone_low > 0 and entry_zone_high > 0:
            zone_touched = not (h < entry_zone_low or l > entry_zone_high)

        meta = {
            "closed_open": o,
            "closed_high": h,
            "closed_low": l,
            "closed_close": c,
            "pattern_name": pattern_name,
            "volume_ratio": round(vol_ratio, 2),
            "vol_confirmed": vol_confirmed,
            "lower_wick_ratio": round(lower_wick_ratio, 2),
            "upper_wick_ratio": round(upper_wick_ratio, 2),
            "zone_touched": zone_touched,
        }

        if entry_zone_low > 0 and entry_zone_high > 0 and not zone_touched:
            return False, f"M5 closed candle did not test planned zone [{entry_zone_low:.2f} - {entry_zone_high:.2f}] (High: {h:.2f}, Low: {l:.2f})", meta

        if not pattern_confirmed:
            return False, f"M5 closed candle did not form confirming {direction} pattern (Detected: {pattern_name})", meta

        if not vol_confirmed:
            return False, f"M5 closed candle volume {vol_ratio:.2f}x < required {self.min_vol_mult:.2f}x rolling average", meta

        return True, f"M5 closed candle confirmed: {pattern_name} with {vol_ratio:.2f}x volume", meta

    def evaluate_full_trigger(
        self,
        df_m5: pd.DataFrame,
        tick_flow_data: Dict[str, Any],
        live_price: float,
        planned_entry: float,
        direction: str,
        atr: float,
        entry_zone_low: float = 0.0,
        entry_zone_high: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Unified Stage 3 trigger evaluation executing all deterministic checks in sequence:
        1. No-Chase Rule (<= 0.3 ATR away)
        2. Microstructure Order Flow Imbalance (>= 55%)
        3. Closed M5 Candle Confirmation (Pattern + Zone Touch + Volume >= 1.25x)
        """
        direction = direction.upper()

        # 1. No-Chase Rule
        no_chase_ok, no_chase_reason, chase_dist = self.check_no_chase(live_price, planned_entry, atr)
        if not no_chase_ok:
            return {
                "trigger_ready": False,
                "failed_check": "NO_CHASE",
                "reason": no_chase_reason,
                "chase_distance": chase_dist,
                "order_type": "NONE",
            }

        # 2. Microstructure Order Flow Imbalance
        flow_ok, flow_reason = self.check_order_flow(tick_flow_data, direction)
        if not flow_ok:
            return {
                "trigger_ready": False,
                "failed_check": "ORDER_FLOW",
                "reason": flow_reason,
                "chase_distance": chase_dist,
                "order_type": "NONE",
            }

        # 3. Closed M5 Candle Confirmation
        candle_ok, candle_reason, candle_meta = self.check_closed_candle_confirmation(
            df_m5, direction, entry_zone_low, entry_zone_high
        )
        if not candle_ok:
            return {
                "trigger_ready": False,
                "failed_check": "CLOSED_M5_CANDLE",
                "reason": candle_reason,
                "chase_distance": chase_dist,
                "candle_meta": candle_meta,
                "order_type": "LIMIT_ONLY",  # Price is at zone without chase; pending limit can be placed
            }

        return {
            "trigger_ready": True,
            "failed_check": None,
            "reason": f"Stage 3 Trigger Verified: {candle_reason} | {flow_reason} | {no_chase_reason}",
            "chase_distance": chase_dist,
            "candle_meta": candle_meta,
            "order_type": "MARKET_OR_LIMIT",
        }
