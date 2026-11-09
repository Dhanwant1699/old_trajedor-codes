"""
Institutional Active Position & Trade Lifecycle Manager.
NOW POWERED BY AI: Uses LLM-driven GoldPositionManagerAgent to evaluate positions
like a human pro trader instead of hardcoded R-multiple sentry thresholds.

Safety Floor: If LLM is unavailable, minimal hardcoded rules (hard SL, news defense) still protect capital.
Sentry 4 (Volatility Spike) and Sentry 5 (Time Decay) and Sentry 6 (News Defense) remain as safety guardrails.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from config import CONFIG
from core.execution_engine import MT5ExecutionEngine
from agents.xauusd.xauusd_position_manager_agent import GoldPositionManagerAgent
from agents.btcusd.btcusd_position_manager_agent import CryptoPositionManagerAgent


class ProTradeManager:
    """
    AI-Driven position management engine.
    Uses GoldPositionManagerAgent and CryptoPositionManagerAgent (LLM) for intelligent
    partial profit, breakeven, and trailing decisions on Gold and Bitcoin.
    Keeps hard safety guardrails (news defense, time decay, hard SL) as fallback protection.
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
        # AI Position Manager Agents (LLM-powered for both Gold & Crypto)
        self.gold_position_agent = GoldPositionManagerAgent()
        self.crypto_position_agent = CryptoPositionManagerAgent()
        self.ai_position_agent = self.crypto_position_agent if ("BTC" in self.symbol.upper() or "BITCOIN" in self.symbol.upper()) else self.gold_position_agent

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

        is_btc = "BTC" in str(self.symbol).upper() or "BITCOIN" in str(self.symbol).upper()
        
        # Asset-calibrated default ATR & thresholds
        default_atr = 1500.0 if is_btc else 6.50
        atr = float(struct.get("atr_14", default_atr) or default_atr)
        rsi = float(struct.get("rsi_14", 50.0) or 50.0)
        m5_rsi = float(m5_struct.get("rsi_14", 50.0) or 50.0)
        patterns = struct.get("candlestick_patterns", [])
        
        # Microstructure signals
        ask_lifters = float(tick_flow.get("ask_lifters_pct", 50.0) or 50.0)
        bid_hitters = float(tick_flow.get("bid_hitters_pct", 50.0) or 50.0)
        spread_ratio = float(liq_info.get("spread_ratio", 1.0) or 1.0)

        # Volatility Spike Detection (Sentry 4)
        # Volatility Spike Detection (Sentry 4)
        vol_threshold = 2800.0 if is_btc else 11.0
        is_volatility_spike = (atr >= vol_threshold) or (spread_ratio >= 1.8)

        news_blackout = news_payload.get("news_blackout_active", False)
        minutes_to_news = news_payload.get("minutes_to_next_impact", 999)

        # Asset-specific calibration parameters
        # Gold: Linear movement, tighter BE (+0.65R / +$0.40 buffer) & 1.35x ATR trail
        # Bitcoin: High-beta expansion, wide BE (+1.25R / +$75.00 buffer) & 2.75x ATR trail
        be_trigger_r = CONFIG.BTC_TRAILING_BE_TRIGGER_R if is_btc else CONFIG.TRAILING_BE_TRIGGER_R
        be_profit_lock_price = CONFIG.BTC_TRAILING_BUFFER_DOLLARS if is_btc else 0.40
        tp1_tolerance = 25.0 if is_btc else 0.35
        min_trail_dist = CONFIG.BTC_MIN_TRAIL_DISTANCE if is_btc else 4.80
        fallback_r_dist = 1000.0 if is_btc else 7.50
        min_step = CONFIG.BTC_MIN_TRAIL_STEP if is_btc else 0.30

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
                initial_r_dist = max(atr * (2.0 if is_btc else 1.25), fallback_r_dist)

            if initial_r_dist <= 0:
                initial_r_dist = fallback_r_dist

            # Calculate Current R-Multiple and Price Gain
            if pos_type == "BUY":
                price_gain = current_price - open_price
                r_multiple = price_gain / initial_r_dist
            else:
                price_gain = open_price - current_price
                r_multiple = price_gain / initial_r_dist

            # =========================================================================
            # SENTRY 6: NEWS / SHOCK FLASH SENTRY (High-Impact Event or Spread Blowout)
            # =========================================================================
            if (news_blackout or minutes_to_news <= 10 or spread_ratio >= 2.2) and r_multiple >= 0.50:
                if ticket not in self.partially_closed_tickets and volume >= (CONFIG.MIN_LOT_SIZE * 2):
                    close_vol = max(CONFIG.MIN_LOT_SIZE, round(volume * 0.5, 2))
                    success, msg = self.exec_engine.close_partial_position(
                        ticket=ticket,
                        volume_to_close=close_vol,
                        comment="Chanakya_News_Shield"
                    )
                    if success:
                        self.partially_closed_tickets.add(ticket)
                        self.exec_engine.move_to_breakeven(ticket, buffer_price=be_profit_lock_price)
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
            # 🧠 AI POSITION MANAGEMENT AGENT (Gold & Bitcoin Human AI Pro Trader)
            # Observes live candle structure, ticks, momentum, flow, and CVD.
            # Decides dynamically when to take partial profit, move BE, or trail.
            # =========================================================================
            active_position_agent = self.crypto_position_agent if is_btc else self.gold_position_agent
            agent_tag = "BTC AI Position Agent" if is_btc else "Gold AI Position Agent"

            position_context = {
                "ticket": ticket,
                "symbol": pos_symbol,
                "type": pos_type,
                "entry_price": open_price,
                "current_price": current_price,
                "sl": current_sl,
                "tp": tp1,
                "volume": volume,
                "profit_pnl": profit_pnl,
                "price_gain": price_gain,
                "r_multiple": r_multiple,
                "time_in_trade_mins": time_in_trade_mins,
                "already_partial_closed": ticket in self.partially_closed_tickets,
                "already_breakeven_locked": ticket in self.breakeven_locked_tickets,
                "currency": "EUR"
            }
            market_snapshot = {
                "m5_structure": m5_struct,
                "m15_structure": struct,
                "tick_order_flow": tick_flow,
                "volume_delta": vdelta,
                "regime": regime_info
            }

            ai_decision = active_position_agent.evaluate_position(position_context, market_snapshot)
            ai_action = ai_decision.get("action", "HOLD_POSITION")
            ai_confidence = int(ai_decision.get("confidence", 0))
            ai_reasoning = ai_decision.get("reasoning", "")

            # Execute the AI's decision
            if ai_action == "TAKE_PARTIAL_PROFIT" and ticket not in self.partially_closed_tickets:
                if volume >= (CONFIG.MIN_LOT_SIZE * 2):
                    close_pct = ai_decision.get("partial_close_pct", 50) / 100.0
                    close_pct = max(0.20, min(0.80, close_pct))
                    close_vol = max(CONFIG.MIN_LOT_SIZE, round(volume * close_pct, 2))
                    success, msg = self.exec_engine.close_partial_position(
                        ticket=ticket,
                        volume_to_close=close_vol,
                        comment=f"{'BTC' if is_btc else 'Gold'}_AI_Partial"
                    )
                    if success:
                        self.partially_closed_tickets.add(ticket)
                        self.exec_engine.move_to_breakeven(ticket, buffer_price=be_profit_lock_price)
                        self.breakeven_locked_tickets.add(ticket)
                        actions_log.append({
                            "type": "AI_PARTIAL_PROFIT",
                            "ticket": ticket,
                            "thought": f"🧠 {agent_tag}: Banked {int(close_pct*100)}% ({close_vol} lots @ +{r_multiple:.2f}R / +${price_gain:.2f}). {ai_reasoning[:100]}",
                            "result": msg
                        })
                        self._update_telemetry(ticket, r_multiple, time_in_trade_mins, "AI_PARTIAL_BANKED", "RUNNER_ACTIVE")
                        continue
                else:
                    # Micro lot: can't split, lock BE instead
                    if ticket not in self.breakeven_locked_tickets:
                        self.exec_engine.move_to_breakeven(ticket, buffer_price=be_profit_lock_price)
                        self.breakeven_locked_tickets.add(ticket)

            elif ai_action == "MOVE_TO_BREAKEVEN" and ticket not in self.breakeven_locked_tickets:
                new_sl = ai_decision.get("new_sl_price")
                if new_sl and new_sl > 0:
                    success, msg = self.exec_engine.update_stop_loss(ticket, float(new_sl))
                else:
                    success, msg = self.exec_engine.move_to_breakeven(ticket, buffer_price=be_profit_lock_price)
                if success:
                    self.breakeven_locked_tickets.add(ticket)
                    actions_log.append({
                        "type": "AI_BREAKEVEN_LOCK",
                        "ticket": ticket,
                        "thought": f"🧠 {agent_tag}: Locked Breakeven @ +{r_multiple:.2f}R. {ai_reasoning[:100]}",
                        "result": msg
                    })

            elif ai_action == "TIGHTEN_TRAIL":
                new_sl = ai_decision.get("new_sl_price")
                if new_sl and new_sl > 0:
                    # Safety: only tighten, never widen
                    valid_tighten = (pos_type == "BUY" and new_sl > current_sl) or \
                                    (pos_type == "SELL" and (current_sl <= 0 or new_sl < current_sl))
                    if valid_tighten:
                        success, msg = self.exec_engine.update_stop_loss(ticket, float(new_sl))
                        if success:
                            self.trailing_sl_cache[ticket] = new_sl
                            actions_log.append({
                                "type": "AI_TRAIL_TIGHTEN",
                                "ticket": ticket,
                                "thought": f"🧠 {agent_tag}: Tightened SL to {new_sl:,.2f}. {ai_reasoning[:100]}",
                                "result": msg
                            })

            elif ai_action == "CLOSE_FULL":
                success, msg = self.exec_engine.close_position(
                    ticket=ticket,
                    comment=f"{'BTC' if is_btc else 'Gold'}_AI_Exit"
                )
                if success:
                    actions_log.append({
                        "type": "AI_FULL_EXIT",
                        "ticket": ticket,
                        "thought": f"🧠 {agent_tag}: Full exit @ +{r_multiple:.2f}R (+${profit_pnl:.2f}). {ai_reasoning[:100]}",
                        "result": msg
                    })
                    self._update_telemetry(ticket, r_multiple, time_in_trade_mins, "AI_EXIT", "CLOSED")
                    continue

            # else: HOLD_POSITION — AI says let it ride

            # =========================================================================
            # SENTRY 5: TIME-IN-TRADE DECAY SENTRY (Exits Stagnant Trades > 45 mins)
            # =========================================================================
            max_stagnant_mins = 60.0 if is_btc else 45.0
            if time_in_trade_mins >= max_stagnant_mins and abs(r_multiple) <= 0.25:
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
            if is_btc:
                trail_multiplier = 1.85 if is_volatility_spike else CONFIG.BTC_TRAILING_ATR_MULTIPLIER
                trail_trigger_r = CONFIG.BTC_TRAILING_LOCK_TRIGGER_R
            else:
                trail_multiplier = 0.85 if is_volatility_spike else CONFIG.TRAILING_ATR_MULTIPLIER
                trail_trigger_r = 1.00

            trail_distance = max(min_trail_dist, atr * trail_multiplier)

            if r_multiple >= trail_trigger_r:
                target_new_sl = None
                if pos_type == "BUY":
                    calc_sl = round(current_price - trail_distance, 2)
                    # Ratchet Rule: Only advance upward, never widen
                    if calc_sl > current_sl and calc_sl > (open_price + min_step):
                        target_new_sl = calc_sl
                else:
                    calc_sl = round(current_price + trail_distance, 2)
                    # Ratchet Rule: Only advance downward, never widen
                    if (current_sl <= 0 or calc_sl < current_sl) and calc_sl < (open_price - min_step):
                        target_new_sl = calc_sl

                if target_new_sl and abs(target_new_sl - current_sl) >= min_step:
                    success, msg = self.exec_engine.update_stop_loss(ticket, target_new_sl)
                    if success:
                        self.trailing_sl_cache[ticket] = target_new_sl
                        actions_log.append({
                            "type": "ATR_RATCHET_TRAILING_UPDATE",
                            "ticket": ticket,
                            "thought": f"📈 ATR Ratchet Trailing Sentry: SL advanced to {target_new_sl:,.2f} ({trail_multiplier:.2f}x ATR Trail). Accrued gain secured.",
                            "result": msg
                        })

            # Derive momentum health from AI decision cache or order flow
            cached_ai = self.ai_position_agent._last_decision_cache.get(ticket, {}) if not is_btc else {}
            ai_says_close = cached_ai.get("action") in ("CLOSE_FULL", "TAKE_PARTIAL_PROFIT")
            mom_health = "REVERSAL_HAZARD" if ai_says_close else "STRONG_CONTINUATION" if (ask_lifters > 55 if pos_type == "BUY" else bid_hitters > 55) else "BALANCED_FLOW"

            # Telemetry status strings
            be_status = f"LOCKED (+${be_profit_lock_price:.2f})" if ticket in self.breakeven_locked_tickets else f"AI Managed (R: {r_multiple:+.2f})"
            trail_status = f"${self.trailing_sl_cache.get(ticket, current_sl):,.2f}" if ticket in self.trailing_sl_cache else "AI Managed"
            
            self._update_telemetry(
                ticket=ticket,
                r_mult=r_multiple,
                duration_m=time_in_trade_mins,
                state="PROTECTED" if ticket in self.breakeven_locked_tickets else "AI_MONITORED",
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
