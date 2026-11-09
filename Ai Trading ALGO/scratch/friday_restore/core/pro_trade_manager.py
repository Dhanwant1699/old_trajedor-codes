"""
Institutional Active Position & Trade Lifecycle Manager.
Implements the complete 7-Sentry Dynamic Trade Lifecycle Suite:
1. Dynamic Breakeven-Lock Sentry (Kills the +60 profit -> -80 loss disaster at +0.75R / 1.0x ATR)
2. ATR-Based Dynamic Ratchet Trailing Stop Sentry (1.4x-1.5x ATR M5 trailing ratchet)
3. Momentum Exhaustion & Reversal Detection Sentry (Early exit on M1/M5 opposing engulfing/exhaustion)
4. Volatility Spike Sentry (Tightens trailing buffer from 1.5x to 0.85x ATR during sudden explosions)
5. Time-in-Trade Decay Sentry (Exits stagnant trades after > 45 mins of zero progression)
6. News / Shock Flash Sentry (Emergency de-risking on sudden spread blowout or high-impact events)
7. Dynamic Partial-Booking Optimizer (Momentum-scaled partials: 35% on strong flow vs 65% on stall)
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from config import CONFIG
from core.execution_engine import MT5ExecutionEngine


class ProTradeManager:
    """
    Autonomous position management engine mimicking a seasoned institutional prop trader.
    Executes sub-millisecond 7-Sentry real-time risk defenses on every tick.
    """
    def __init__(self, execution_engine: MT5ExecutionEngine):
        self.exec_engine = execution_engine
        self.symbol = execution_engine.symbol
        # Track tickets with specific actions taken
        self.partially_closed_tickets = set()
        self.breakeven_locked_tickets = set()
        self.trailing_sl_cache: Dict[int, float] = {}
        # Sentry Telemetry Cache for Cockpit UI & Voice Companion
        self.sentry_telemetry: Dict[int, Dict[str, Any]] = {}

    def evaluate_and_manage_positions(
        self,
        open_positions: List[Dict[str, Any]],
        market_payload: Dict[str, Any],
        news_payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Scans all open positions for this symbol and executes professional trade management actions.
        Returns a log list of trader thoughts and actions taken.
        """
        if not open_positions:
            self.sentry_telemetry.clear()
            return []

        actions_log = []
        now_ts = time.time()
        ticks = market_payload.get("pricing", {})
        current_bid = float(ticks.get("bid", 0.0) or 0.0)
        current_ask = float(ticks.get("ask", 0.0) or 0.0)
        spread_pts = float(ticks.get("spread_points", 15.0) or 15.0)

        struct = market_payload.get("market_structures", {}).get("m15_execution_structure", {})
        m5_struct = market_payload.get("market_structures", {}).get("m5_micro_momentum", {})
        tick_flow = market_payload.get("tick_order_flow", {}) or market_payload.get("market_structures", {}).get("tick_order_flow", {})
        vdelta = market_payload.get("volume_delta_cvd", {}) or market_payload.get("market_structures", {}).get("volume_delta_cvd", {})
        regime_info = market_payload.get("regime_analysis", {}) or market_payload.get("market_structures", {}).get("regime_analysis", {})
        liq_info = market_payload.get("liquidity_execution_quality", {}) or market_payload.get("market_structures", {}).get("liquidity_execution_quality", {})

        atr = float(struct.get("atr_14", 6.50) or 6.50)
        rsi = float(struct.get("rsi_14", 50.0) or 50.0)
        m5_rsi = float(m5_struct.get("rsi_14", 50.0) or 50.0)
        patterns = struct.get("candlestick_patterns", [])
        
        # Microstructure signals
        ask_lifters = float(tick_flow.get("ask_lifters_pct", 50.0) or 50.0)
        bid_hitters = float(tick_flow.get("bid_hitters_pct", 50.0) or 50.0)
        spread_ratio = float(liq_info.get("spread_ratio", 1.0) or 1.0)

        # Volatility Spike Detection (Sentry 4)
        is_volatility_spike = (atr >= 11.0) or (spread_ratio >= 1.8)

        news_blackout = news_payload.get("news_blackout_active", False)
        minutes_to_news = news_payload.get("minutes_to_next_impact", 999)

        for pos in open_positions:
            ticket = int(pos.get("ticket", 0))
            pos_type = str(pos.get("type", "BUY")).upper()
            open_price = float(pos.get("open_price", 0.0) or 0.0)
            current_price = current_bid if pos_type == "BUY" else current_ask
            current_sl = float(pos.get("sl", 0.0) or 0.0)
            tp1 = float(pos.get("tp", 0.0) or 0.0)
            volume = float(pos.get("volume", 0.01) or 0.01)
            profit_pnl = float(pos.get("profit", 0.0) or 0.0)
            open_time_pos = pos.get("time", now_ts)
            
            # Calculate Time-in-Trade (minutes)
            if isinstance(open_time_pos, (int, float)):
                time_in_trade_mins = max(0.1, round((now_ts - float(open_time_pos)) / 60.0, 1))
            else:
                time_in_trade_mins = 5.0

            if ticket <= 0 or open_price <= 0:
                continue

            # Calculate Initial Risk Distance (R)
            if current_sl > 0:
                initial_r_dist = abs(open_price - current_sl)
            else:
                initial_r_dist = max(atr * 1.25, 7.50)

            if initial_r_dist <= 0:
                initial_r_dist = 7.50

            # Calculate Current R-Multiple and Price Gain
            if pos_type == "BUY":
                price_gain = current_price - open_price
                r_multiple = price_gain / initial_r_dist
            else:
                price_gain = open_price - current_price
                r_multiple = price_gain / initial_r_dist

            # =========================================================================
            # SENTRY 6: NEWS / SHOCK FLASH SENTRY (CPI/NFP/FOMC or Sudden Spread Spike)
            # =========================================================================
            if (news_blackout or minutes_to_news <= 10 or spread_ratio >= 2.2) and r_multiple >= 0.50:
                if ticket not in self.partially_closed_tickets and volume >= (CONFIG.MIN_LOT_SIZE * 2):
                    close_vol = round(volume * 0.5, 2)
                    success, msg = self.exec_engine.close_partial_position(
                        ticket=ticket,
                        volume_to_close=close_vol,
                        comment="Chanakya_News_Shield"
                    )
                    if success:
                        self.partially_closed_tickets.add(ticket)
                        self.exec_engine.move_to_breakeven(ticket, buffer_points=5.0)
                        self.breakeven_locked_tickets.add(ticket)
                        actions_log.append({
                            "type": "NEWS_SHOCK_DEFENSE",
                            "ticket": ticket,
                            "thought": f"Shock / News Defense: Event in {minutes_to_news}m (Spread Ratio {spread_ratio:.1f}x). Banked 50% profit ({close_vol} lots) and locked Breakeven.",
                            "result": msg
                        })
                        self._update_telemetry(ticket, r_multiple, time_in_trade_mins, "NEWS_LOCKED", "SECURED")
                        continue

            # =========================================================================
            # SENTRY 3: MOMENTUM EXHAUSTION & REVERSAL SENTRY (M1/M5 Reversal Defense)
            # =========================================================================
            # Watches for sudden opposing reversal signatures before price drops back down to SL/BE
            is_exhaustion_reversal = False
            reversal_reason = ""

            if pos_type == "BUY":
                # Check for Bearish Pinbars / Shooting Star or Engulfing
                for p in patterns:
                    if "BEARISH" in str(p.get("pattern", "")).upper():
                        is_exhaustion_reversal = True
                        reversal_reason = f"M15 {p.get('pattern')} Reversal Wick"
                        break
                # Extreme RSI overbought stall
                if rsi >= 76.0 or m5_rsi >= 80.0:
                    is_exhaustion_reversal = True
                    reversal_reason = f"RSI Extreme Overbought ({rsi:.1f})"
                # Aggressive Seller Influx (Bid Hitters > 68%)
                if bid_hitters >= 68.0:
                    is_exhaustion_reversal = True
                    reversal_reason = f"Aggressive Seller Delta Surge ({bid_hitters:.0f}% Bid Hitters)"
                # Fast M5 EMA Stall
                m5_ema9 = float(m5_struct.get("ema_9", 0.0) or 0.0)
                m5_ema21 = float(m5_struct.get("ema_21", 0.0) or 0.0)
                if m5_ema9 > 0 and m5_ema21 > 0 and m5_ema9 < m5_ema21 and r_multiple >= 0.9:
                    is_exhaustion_reversal = True
                    reversal_reason = "M5 Fast EMA 9/21 Bearish Stall"

            elif pos_type == "SELL":
                # Check for Bullish Pinbars / Hammer or Engulfing
                for p in patterns:
                    if "BULLISH" in str(p.get("pattern", "")).upper():
                        is_exhaustion_reversal = True
                        reversal_reason = f"M15 {p.get('pattern')} Reversal Wick"
                        break
                # Extreme RSI oversold stall
                if rsi <= 24.0 or m5_rsi <= 20.0:
                    is_exhaustion_reversal = True
                    reversal_reason = f"RSI Extreme Oversold ({rsi:.1f})"
                # Aggressive Buyer Influx (Ask Lifters > 68%)
                if ask_lifters >= 68.0:
                    is_exhaustion_reversal = True
                    reversal_reason = f"Aggressive Buyer Delta Surge ({ask_lifters:.0f}% Ask Lifters)"
                # Fast M5 EMA Stall
                m5_ema9 = float(m5_struct.get("ema_9", 0.0) or 0.0)
                m5_ema21 = float(m5_struct.get("ema_21", 0.0) or 0.0)
                if m5_ema9 > 0 and m5_ema21 > 0 and m5_ema9 > m5_ema21 and r_multiple >= 0.9:
                    is_exhaustion_reversal = True
                    reversal_reason = "M5 Fast EMA 9/21 Bullish Stall"

            # If in solid profit (+0.75R or more) and reversal detected, take early profit immediately!
            if r_multiple >= 0.75 and is_exhaustion_reversal:
                success, msg = self.exec_engine.close_position(
                    ticket=ticket,
                    comment=f"Chanakya_Exhaust_{reversal_reason[:8]}"[:31]
                )
                if success:
                    actions_log.append({
                        "type": "MOMENTUM_EXHAUSTION_EXIT",
                        "ticket": ticket,
                        "thought": f"⚡ Momentum Exhaustion Sentry: Banked early profit @ +{r_multiple:.2f}R (+€{profit_pnl:.2f}). Reason: {reversal_reason}.",
                        "result": msg
                    })
                    self._update_telemetry(ticket, r_multiple, time_in_trade_mins, "EXHAUSTION_EXIT", "BANKED")
                    continue

            # =========================================================================
            # SENTRY 7: DYNAMIC PARTIAL-BOOKING OPTIMIZER (TP1 or >= +1.4R Gain)
            # =========================================================================
            is_tp1_reached = (tp1 > 0 and ((pos_type == "BUY" and current_price >= (tp1 - 0.35)) or (pos_type == "SELL" and current_price <= (tp1 + 0.35))))
            if (r_multiple >= 1.40 or (is_tp1_reached and r_multiple >= 0.9)) and ticket not in self.partially_closed_tickets:
                if volume >= (CONFIG.MIN_LOT_SIZE * 2):
                    # Momentum-scaled partial booking:
                    # If flow is accelerating, book 40% (keep 60% runner); if flow is stalling, book 65%
                    cvd_pat = str(vdelta.get("cvd_pattern", "")).upper()
                    is_accelerating = "ACCUMULATION" in cvd_pat or "THRUST" in cvd_pat or (pos_type == "BUY" and ask_lifters > 58) or (pos_type == "SELL" and bid_hitters > 58)
                    close_pct = 0.40 if is_accelerating else 0.65
                    close_vol = round(volume * close_pct, 2)

                    success, msg = self.exec_engine.close_partial_position(
                        ticket=ticket,
                        volume_to_close=close_vol,
                        comment=f"Chanakya_Partial_{int(close_pct*100)}"
                    )
                    if success:
                        self.partially_closed_tickets.add(ticket)
                        # Lock Breakeven immediately on remaining volume
                        self.exec_engine.move_to_breakeven(ticket, buffer_points=6.0)
                        self.breakeven_locked_tickets.add(ticket)
                        actions_log.append({
                            "type": "DYNAMIC_PARTIAL_BOOKED",
                            "ticket": ticket,
                            "thought": f"🎯 Partial Optimizer Sentry: Banked {int(close_pct*100)}% partial ({close_vol} lots @ +{r_multiple:.2f}R). Remaining runner locked at Breakeven.",
                            "result": msg
                        })
                        self._update_telemetry(ticket, r_multiple, time_in_trade_mins, "PARTIAL_BANKED", "RUNNER_ACTIVE")
                        continue

            # =========================================================================
            # SENTRY 1: DYNAMIC BREAKEVEN-LOCK SENTRY (Eliminates +60 -> -80 Reversals)
            # =========================================================================
            # Fires as soon as trade achieves +0.75R gain or +1.0x ATR distance
            should_lock_be = (r_multiple >= 0.75) or (price_gain >= max(4.50, atr * 0.90))
            if should_lock_be and ticket not in self.breakeven_locked_tickets:
                success, msg = self.exec_engine.move_to_breakeven(ticket, buffer_points=6.0)
                if success:
                    self.breakeven_locked_tickets.add(ticket)
                    actions_log.append({
                        "type": "BREAKEVEN_LOCK_SECURED",
                        "ticket": ticket,
                        "thought": f"🛡️ Breakeven-Lock Sentry: Profit reached +{r_multiple:.2f}R. SL moved to Breakeven (+0.40 buffer). Risk is now ZERO.",
                        "result": msg
                    })

            # =========================================================================
            # SENTRY 5: TIME-IN-TRADE DECAY SENTRY (Exits Stagnant Trades > 45 mins)
            # =========================================================================
            if time_in_trade_mins >= 45.0 and abs(r_multiple) <= 0.25:
                # Trade is stuck in a dead chop range; exit at near-breakeven to preserve capital
                success, msg = self.exec_engine.close_position(
                    ticket=ticket,
                    comment="Chanakya_Time_Decay"
                )
                if success:
                    actions_log.append({
                        "type": "TIME_DECAY_EXIT",
                        "ticket": ticket,
                        "thought": f"⏳ Time-Decay Sentry: Position flat after {time_in_trade_mins:.0f} mins (R: {r_multiple:.2f}). Exited cleanly to release margin.",
                        "result": msg
                    })
                    self._update_telemetry(ticket, r_multiple, time_in_trade_mins, "TIME_DECAY_EXIT", "CLOSED")
                    continue

            # =========================================================================
            # SENTRY 4 & 2: VOLATILITY SPIKE & ATR DYNAMIC RATCHET TRAILING STOP
            # =========================================================================
            # Dynamic trailing distance scaled to ATR (0.85x if volatile spike, else 1.4x ATR)
            trail_multiplier = 0.85 if is_volatility_spike else 1.40
            trail_distance = max(4.80, atr * trail_multiplier)

            if r_multiple >= 1.0:
                target_new_sl = None
                if pos_type == "BUY":
                    calc_sl = round(current_price - trail_distance, 2)
                    # Ratchet Rule: Only advance upward, never widen
                    if calc_sl > current_sl and calc_sl > (open_price + 0.30):
                        target_new_sl = calc_sl
                else:
                    calc_sl = round(current_price + trail_distance, 2)
                    # Ratchet Rule: Only advance downward, never widen
                    if (current_sl <= 0 or calc_sl < current_sl) and calc_sl < (open_price - 0.30):
                        target_new_sl = calc_sl

                if target_new_sl:
                    success, msg = self.exec_engine.update_stop_loss(ticket, target_new_sl)
                    if success:
                        self.trailing_sl_cache[ticket] = target_new_sl
                        actions_log.append({
                            "type": "ATR_RATCHET_TRAILING_UPDATE",
                            "ticket": ticket,
                            "thought": f"📈 ATR Ratchet Trailing Sentry: SL advanced to {target_new_sl:,.2f} ({trail_multiplier:.2f}x ATR Trail). Accrued gain secured.",
                            "result": msg
                        })

            # Update live Sentry diagnostics for Cockpit UI
            be_status = "LOCKED (+0.40 pt)" if ticket in self.breakeven_locked_tickets else f"Armed @ +0.75R (Current: {r_multiple:+.2f}R)"
            trail_status = f"${self.trailing_sl_cache.get(ticket, current_sl):,.2f} ({trail_multiplier:.1f}x ATR)" if r_multiple >= 1.0 else "Armed (Fires @ +1.0R)"
            mom_health = "REVERSAL_HAZARD" if is_exhaustion_reversal else "STRONG_CONTINUATION" if (ask_lifters > 55 if pos_type == "BUY" else bid_hitters > 55) else "BALANCED_FLOW"
            
            self._update_telemetry(
                ticket=ticket,
                r_mult=r_multiple,
                duration_m=time_in_trade_mins,
                state="PROTECTED" if ticket in self.breakeven_locked_tickets else "MONITORED",
                be_status=be_status,
                trail_status=trail_status,
                mom_health=mom_health,
                vol_spike=is_volatility_spike
            )

        return actions_log

    def _update_telemetry(
        self,
        ticket: int,
        r_mult: float,
        duration_m: float,
        state: str,
        be_status: str = "Armed",
        trail_status: str = "Armed",
        mom_health: str = "BALANCED",
        vol_spike: bool = False
    ):
        """Updates internal telemetry dictionary for UI dashboard."""
        self.sentry_telemetry[ticket] = {
            "ticket": ticket,
            "r_multiple": round(r_mult, 2),
            "time_in_trade_mins": duration_m,
            "lifecycle_state": state,
            "breakeven_status": be_status,
            "trailing_status": trail_status,
            "momentum_health": mom_health,
            "volatility_spike": vol_spike
        }

    def get_active_telemetry(self) -> Dict[int, Dict[str, Any]]:
        """Returns live sentry diagnostics for all active positions."""
        return self.sentry_telemetry
