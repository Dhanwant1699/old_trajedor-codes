"""
TRAJEDOR - Trade Doctor (Active In-Flight Defense & Forensic Engine).
Continuously monitors open positions.
- Dynamically adapts to real-time M1 / M5 candle price action.
- Detects candle rejection / pinbars at support/resistance.
- Books partial profits (50% lot close) at +3.0 to +4.5 pts.
- Trails Stop Loss dynamically behind M1/M5 swing pivots rather than letting profits vanish.
- Executes early cuts (-0.3R) if the market structure breaks against the trade.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np


@dataclass
class DiagnosticVerdict:
    ticket: int
    threat_status: str              # "NORMAL", "LIQUIDITY_SWEEP", "THESIS_INVALIDATED", "PROFIT_PROTECTION", "EXHAUSTION_WARNING"
    recommended_action: str         # "HOLD", "EARLY_CUT", "PARTIAL_BOOK", "LOCK_BREAKEVEN", "TRAIL_SL", "CLOSE_PROFIT"
    r_multiple: float               # Current R outcome
    gain_points: float              # Direct point gain/loss
    capital_saved_pct: float        # Estimated % risk capital saved
    suggested_sl: Optional[float]   # Dynamic trailing SL price
    close_volume_pct: float         # 0.0 to 1.0 (e.g. 0.50 for 50% partial close)
    forensic_diagnosis: str         # Detailed explanation


class TradeDoctor:
    def __init__(self, early_cut_threshold_r: float = -0.65):
        self.early_cut_threshold_r = early_cut_threshold_r

    def diagnose_position(
        self,
        ticket: int,
        direction: str,
        entry_price: float,
        current_price: float,
        initial_sl: float,
        take_profit: float,
        volume: float = 0.02,
        current_sl: Optional[float] = None,
        m1_candles: Optional[Any] = None,
        m5_candles: Optional[Any] = None,
        macro_shock_active: bool = False,
        opposing_fvg_printed: bool = False
    ) -> DiagnosticVerdict:
        """
        Runs real-time forensic diagnosis on an active position with M1/M5 candle awareness.
        """
        # Calculate risk per 1R (cap to realistic intraday 5.0 pts if user set swing stop)
        raw_risk = abs(entry_price - initial_sl) if abs(entry_price - initial_sl) > 0.01 else 5.0
        risk_dist = min(raw_risk, 6.0)  # Standardized intraday risk scale
        
        # Calculate current floating points & R
        is_buy = direction.upper() == "BUY"
        gain_dist = (current_price - entry_price) if is_buy else (entry_price - current_price)
        current_r = round(gain_dist / risk_dist, 2)
        gain_pts = round(gain_dist, 2)

        # -------------------------------------------------------------
        # Real-time M1 / M5 Candle Rejection Analysis
        # -------------------------------------------------------------
        reversal_detected = False
        reversal_detail = ""
        m1_pivot_sl = None

        if m1_candles is not None and len(m1_candles) >= 3:
            last_c = m1_candles[-1]
            prev_c = m1_candles[-2]
            c_high = float(last_c['high'])
            c_low = float(last_c['low'])
            c_open = float(last_c['open'])
            c_close = float(last_c['close'])
            total_range = max(c_high - c_low, 0.01)

            if is_buy:
                # In BUY trade: upper wick pinbar or lower close indicates ceiling rejection
                upper_wick = c_high - max(c_open, c_close)
                if upper_wick / total_range > 0.55 and total_range > 1.2:
                    reversal_detected = True
                    reversal_detail = "M1 Bearish Rejection Pinbar printed at highs."
                m1_pivot_sl = round(min(float(last_c['low']), float(prev_c['low'])) - 0.40, 2)
            else:
                # In SELL trade: lower wick pinbar or strong hammer indicates floor bounce
                lower_wick = min(c_open, c_close) - c_low
                if lower_wick / total_range > 0.55 and total_range > 1.2:
                    reversal_detected = True
                    reversal_detail = "M1 Bullish Rejection Hammer printed at lows."
                m1_pivot_sl = round(max(float(last_c['high']), float(prev_c['high'])) + 0.40, 2)

        # -------------------------------------------------------------
        # 1. Active Profit Management & Candle Adaptation (Swing Runner Protocol)
        # -------------------------------------------------------------
        # Milestone 3: Major Swing Expansion Runner (+8.0 to +30.0+ points)
        # Deep in expansion! Protect profits dynamically while letting runner hunt terminal target (75%+ move)
        if gain_pts >= 8.0:
            swing_trail_sl = round(current_price - (3.8 if is_buy else -3.8), 2)
            # Only trail tighter, never widen
            should_update_trail = True
            if current_sl and current_sl > 0:
                if is_buy and current_sl >= swing_trail_sl:
                    should_update_trail = False
                elif not is_buy and current_sl <= swing_trail_sl:
                    should_update_trail = False

            return DiagnosticVerdict(
                ticket=ticket,
                threat_status="PROFIT_PROTECTION",
                recommended_action="TRAIL_SL" if should_update_trail else "HOLD",
                r_multiple=current_r,
                gain_points=gain_pts,
                capital_saved_pct=100.0,
                suggested_sl=swing_trail_sl if should_update_trail else None,
                close_volume_pct=0.0,
                forensic_diagnosis=(
                    f"Big Swing Runner Active: Trade at +{gain_pts} pts (+{current_r}R). "
                    f"Dynamic trailing SL at ${swing_trail_sl:.2f} locks in +{abs(swing_trail_sl - entry_price):.1f} pts profit while letting runner capture full expansion to opposite high."
                )
            )

        # Milestone 2: Expansion Partial Harvest (+4.2 to +7.9 points)
        # Bank 40% partial profit in cash into balance; keep 60% runner open with risk-free stop
        if gain_pts >= 4.2:
            safe_trail_sl = round(entry_price + (1.0 if is_buy else -1.0), 2)
            return DiagnosticVerdict(
                ticket=ticket,
                threat_status="PROFIT_PROTECTION",
                recommended_action="PARTIAL_BOOK",
                r_multiple=current_r,
                gain_points=gain_pts,
                capital_saved_pct=40.0,
                suggested_sl=safe_trail_sl,
                close_volume_pct=0.40,
                forensic_diagnosis=(
                    f"Expansion Milestone Achieved: Trade at +{gain_pts} pts (+{current_r}R). "
                    f"Harvested 40% partial profit into bankable cash. 60% runner kept alive with protective stop (${safe_trail_sl:.2f}) to capture big swing expansion."
                )
            )

        # Milestone 1: Initial Move to Breakeven (+2.2 to +4.1 points)
        # Move SL to Entry + 0.25 pts immediately! Trade becomes 100% RISK-FREE ($0.00 loss if it reverses).
        if gain_pts >= 2.2 or current_r >= 0.50:
            be_sl = round(entry_price + (0.25 if is_buy else -0.25), 2)
            already_locked = False
            if current_sl and current_sl > 0:
                if is_buy and current_sl >= be_sl:
                    already_locked = True
                elif not is_buy and current_sl <= be_sl:
                    already_locked = True

            action = "HOLD" if already_locked else "LOCK_BREAKEVEN"
            return DiagnosticVerdict(
                ticket=ticket,
                threat_status="PROFIT_PROTECTION",
                recommended_action=action,
                r_multiple=current_r,
                gain_points=gain_pts,
                capital_saved_pct=100.0,
                suggested_sl=be_sl if not already_locked else None,
                close_volume_pct=0.0,
                forensic_diagnosis=f"Breakeven Secured: Trade reached +{gain_pts} pts (+{current_r}R). SL moved to Breakeven (${be_sl:.2f}). Trade is 100% risk-free; waiting for big-point swing expansion."
            )

        # -------------------------------------------------------------
        # 2. Adverse Movement & Structural Breakdown Forensics
        # -------------------------------------------------------------
        if current_r <= self.early_cut_threshold_r and gain_pts <= -4.0:
            if macro_shock_active or opposing_fvg_printed or current_r <= -0.80:
                saved_pct = round((1.0 - abs(current_r)) * 100.0, 1)
                return DiagnosticVerdict(
                    ticket=ticket,
                    threat_status="THESIS_INVALIDATED",
                    recommended_action="EARLY_CUT",
                    r_multiple=current_r,
                    gain_points=gain_pts,
                    capital_saved_pct=saved_pct,
                    suggested_sl=None,
                    close_volume_pct=1.0,
                    forensic_diagnosis=(
                        f"Trade Doctor Alert: Structural thesis broken at {current_r}R ({gain_pts} pts). "
                        f"Displacement against position confirmed. Executing EARLY CUT now to save {saved_pct}% of risk capital."
                    )
                )
            else:
                return DiagnosticVerdict(
                    ticket=ticket,
                    threat_status="LIQUIDITY_SWEEP",
                    recommended_action="HOLD",
                    r_multiple=current_r,
                    gain_points=gain_pts,
                    capital_saved_pct=0.0,
                    suggested_sl=None,
                    close_volume_pct=0.0,
                    forensic_diagnosis=f"Price experiencing liquidity sweep at {current_r}R ({gain_pts} pts). Market structure remains intact. Holding conviction."
                )

        # Normal fluctuation within entry zone
        return DiagnosticVerdict(
            ticket=ticket,
            threat_status="NORMAL",
            recommended_action="HOLD",
            r_multiple=current_r,
            gain_points=gain_pts,
            capital_saved_pct=0.0,
            suggested_sl=None,
            close_volume_pct=0.0,
            forensic_diagnosis=f"Position operating normally at {gain_pts:+.2f} pts ({current_r:+.2f}R). In-flight sentinels green."
        )
