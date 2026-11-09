"""
TRAJEDOR - Master Jarvis Executive Engine.
Maintains the autonomous cognitive deliberation loop:
1. Gathers 360° Macro Intelligence & Google News
2. Synthesizes Smart Money Concepts (Order Blocks, FVGs, Liquidity Sweeps)
3. Consults Episodic Memory Bank before order dispatch
4. Trade Doctor: In-flight diagnostics, early cuts (-0.3R saves 70% risk)
5. Multi-account risk execution across the 3 MT5 accounts.
"""

import os
import sys
import time
from datetime import datetime, timezone

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trajedor.config.settings import SETTINGS, load_accounts_config
from trajedor.src.macro_sentinel import MacroSentinel
from trajedor.src.cognitive_brain import CognitiveBrain
from trajedor.src.trade_doctor import TradeDoctor
from trajedor.src.mt5_multi_account import MT5MultiAccountBridge
from trajedor.src.memory_journal import MemoryJournal


class JarvisExecutive:
    def __init__(self):
        self.settings = SETTINGS
        self.macro_sentinel = MacroSentinel()
        self.brain = CognitiveBrain(symbol=self.settings.PRIMARY_SYMBOL)
        self.doctor = TradeDoctor(early_cut_threshold_r=self.settings.EARLY_CUT_R_THRESHOLD)
        self.mt5_bridge = MT5MultiAccountBridge()
        self.journal = MemoryJournal()
        self.is_running = False
        self.last_order_time = {}
        self.min_order_interval_secs = 600  # 10 minutes interval between auto-entries to stop back-to-back scalping
        self.loss_cooldown_secs = 900       # 15 minutes mandatory post-loss directional block
        self.account_loss_cooldown = {}     # acc_id -> {"time": float, "direction": str, "ticket": int, "pnl": float}
        self.account_last_exit = {}         # acc_id -> {"time": float, "exit_price": float, "direction": str, "pnl": float, "ticket": int}
        self.processed_closed_tickets = set()
        self._init_processed_tickets()

    def _init_processed_tickets(self):
        """Seeds processed closed tickets and recent account exits from SQLite history."""
        try:
            history = self.journal.get_trade_history(limit=200)
            for h in history:
                if h.get("ticket"):
                    self.processed_closed_tickets.add(h["ticket"])
            # Seed last exit info per account to enforce anti-churn across restarts
            for h in history:
                acc = h.get("account_id")
                if acc and acc not in self.account_last_exit and h.get("exit_price"):
                    exit_time_str = h.get("exit_time") or ""
                    try:
                        dt = datetime.fromisoformat(exit_time_str.replace("Z", "+00:00"))
                        exit_ts = dt.timestamp()
                    except Exception:
                        exit_ts = time.time() - 300
                    self.account_last_exit[acc] = {
                        "time": exit_ts,
                        "exit_price": float(h.get("exit_price")),
                        "entry_price": float(h.get("entry_price") or h.get("exit_price")),
                        "direction": h.get("direction", ""),
                        "pnl": float(h.get("realized_pnl") or 0.0),
                        "ticket": h.get("ticket")
                    }
        except Exception:
            pass

    def check_closed_trades_and_autopsy(self, macro: dict, range_pct: float, session_low: float, session_high: float):
        """
        AUTONOMOUS POST-TRADE AUTOPSY ENGINE:
        Inspects all MT5 accounts for closed pure-AI positions.
        When any trade closes with a LOSS:
        - Autonomously diagnoses WHY the trade lost (e.g. sold at floor, bought at ceiling, macro clash).
        - Extracts a tactical rule and permanently saves it to lessons_learned.json & SQLite.
        - Activates a 15-minute directional cooldown to eliminate revenge scalping.
        """
        import MetaTrader5 as mt5
        from datetime import timedelta
        accounts_cfg = load_accounts_config()
        ai_magics = (888991, 888992, 888993, self.settings.MAGIC_NUMBER)

        for acc_id, cfg in accounts_cfg.items():
            if not cfg.get("is_active", True):
                continue
            term_path = cfg.get("terminal_path")
            if not term_path or not os.path.exists(term_path):
                continue

            try:
                if not mt5.initialize(path=term_path, timeout=5000):
                    continue

                now = datetime.now(timezone.utc)
                from_dt = now - timedelta(hours=24)
                deals = mt5.history_deals_get(from_dt, now) or []
                mt5.shutdown()
                time.sleep(0.1)

                pos_map = {}
                for d in deals:
                    if d.magic not in ai_magics:
                        continue
                    if "XAUUSD" not in d.symbol.upper():
                        continue
                    pos_map.setdefault(d.position_id, []).append(d)

                for pid, ds in pos_map.items():
                    if pid in self.processed_closed_tickets:
                        continue

                    entry_deal = next((d for d in ds if d.entry == 0), None)
                    exit_deal = next((d for d in ds if d.entry == 1), None)

                    if entry_deal and exit_deal:
                        self.processed_closed_tickets.add(pid)
                        pnl = round(sum(d.profit + d.swap + d.commission for d in ds), 2)
                        entry_price = round(float(entry_deal.price), 2)
                        exit_price = round(float(exit_deal.price), 2)
                        direction = "BUY" if entry_deal.type == 0 else "SELL"
                        volume = round(float(entry_deal.volume), 2)
                        duration_mins = round((exit_deal.time - entry_deal.time) / 60.0, 1)
                        exit_reason = exit_deal.comment or ("STOP_LOSS" if pnl < 0 else "TAKE_PROFIT")

                        trade_data = {
                            "direction": direction,
                            "entry_price": entry_price,
                            "range_pct": range_pct,
                            "session_low": session_low,
                            "session_high": session_high,
                            "duration_mins": duration_mins,
                            "volume": volume,
                            "symbol": entry_deal.symbol,
                            "account_id": acc_id,
                            "setup_type": "TRAJEDOR_SNIPER"
                        }

                        res = self.journal.record_exit(
                            ticket=pid,
                            exit_price=exit_price,
                            realized_pnl=pnl,
                            exit_reason=exit_reason,
                            macro_context=macro,
                            sentiment_context={"retail_long_pct": 70.0},
                            trade_data=trade_data
                        )

                        # Record exit details for Anti-Churn Same-Price Protection
                        self.account_last_exit[acc_id] = {
                            "time": time.time(),
                            "exit_price": exit_price,
                            "entry_price": entry_price,
                            "direction": direction,
                            "pnl": pnl,
                            "ticket": pid
                        }
                        # Universal post-exit pacing cooldown: reset timer upon trade exit
                        self.last_order_time[acc_id] = time.time()

                        if pnl < 0:
                            # Activate 15-minute post-loss cooldown
                            self.account_loss_cooldown[acc_id] = {
                                "time": time.time(),
                                "direction": direction,
                                "ticket": pid,
                                "pnl": pnl,
                                "entry_price": entry_price
                            }

                            # High-visibility Autonomous Forensic Autopsy Output
                            print("\n" + "=" * 90, flush=True)
                            print(f"🧠 [JARVIS AUTONOMOUS POST-TRADE LOSS AUTOPSY] 🧠", flush=True)
                            print(f"   Account: {acc_id} | Ticket: #{pid} | Direction: {direction} | P&L: -${abs(pnl):.2f}", flush=True)
                            print(f"   Entry: ${entry_price:.2f} -> Exit: ${exit_price:.2f} | Duration: {duration_mins:.1f} mins", flush=True)
                            print("-" * 90, flush=True)
                            print(f"🔍 WHERE PRE-TRADE ANALYSIS WAS WRONG:", flush=True)
                            print(f"   {res.get('post_mortem')}", flush=True)
                            print(f"💡 LESSON LEARNED & EXTRACTED:", flush=True)
                            print(f"   {res.get('learned_rule')}", flush=True)
                            print(f"🛡️ CORRECTIVE ACTION SAVED TO PERSISTENT MEMORY:", flush=True)
                            print(f"   Rule recorded in lessons_learned.json & trade_history.db!", flush=True)
                            print(f"🔒 DEFENSE PROTOCOL ACTIVATED:", flush=True)
                            print(f"   Mandatory 15-minute directional cooldown enforced for {direction} on {acc_id}.", flush=True)
                            print("=" * 90 + "\n", flush=True)
                        else:
                            print(f"  >>> [AI TRADE HARVEST] Ticket #{pid} ({direction}) closed with PROFIT: +${pnl:.2f} on {acc_id} ({duration_mins:.1f}m duration).", flush=True)
            except Exception as e:
                pass

    def run_cycle(self):
        """Executes one complete cognitive perception-action-defense cycle."""
        print(f"\n[JARVIS MARK-85] === Perception & Deliberation Cycle at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} ===")
        
        # 1. Market & Macro Telemetry
        print("  - Connecting to MT5 and Macro Sentinels...", flush=True)
        tick = self.mt5_bridge.get_live_gold_tick()
        price = float(tick.get("bid", 4139.52))
        macro = self.macro_sentinel.get_live_macro_suite()
        print(f"  - Gold Spot: ${price:.2f} (Spread: {tick.get('spread')} pts)", flush=True)
        print(f"  - DXY: {macro['dxy']['price']} ({macro['dxy']['change_pct']:+.2f}%) | US 10Y: {macro['us10y_yield']['price']}%", flush=True)
        print(f"  - Macro Bias: {macro['gold_bias']} (Pressure Score: {macro['gold_macro_impact_score']}/100)", flush=True)

        # 2. Extract Full Multi-Timeframe Suite (1W, 1D, 4H, 1H, 30M, 15M, 5M, 1M)
        mtf_suite = {}
        session_high = price + 15.0
        session_low = price - 15.0
        range_pct = 0.50

        try:
            import MetaTrader5 as mt5
            sym = self.settings.PRIMARY_SYMBOL
            if not mt5.symbol_info(sym):
                sym = "XAUUSD.ecn"

            # Bigger Timeframes: 50-100 candles (Macro Structure & Swing Targets)
            w1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_W1, 0, 75)
            d1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 100)
            h4_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H4, 0, 100)
            h1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 100)

            # Lower / Intermediate Timeframes: 180-300 candles (Liquidity Sweeps & Execution)
            m30_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M30, 0, 200)
            m15_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 250)
            m5_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 280)
            m1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)

            mtf_suite = {
                "w1": w1_rates,
                "d1": d1_rates,
                "h4": h4_rates,
                "h1": h1_rates,
                "m30": m30_rates,
                "m15": m15_rates,
                "m5": m5_rates,
                "m1": m1_rates
            }

            if h1_rates is not None and len(h1_rates) >= 3:
                session_high = max(float(c[2]) for c in h1_rates[-24:])
                session_low = min(float(c[3]) for c in h1_rates[-24:])
            elif m15_rates is not None and len(m15_rates) >= 5:
                session_high = max(float(c[2]) for c in m15_rates[-40:])
                session_low = min(float(c[3]) for c in m15_rates[-40:])

            range_span = max(6.0, session_high - session_low)
            range_pct = (price - session_low) / range_span
        except Exception:
            pass

        print(f"  - Top-Down Multi-Timeframe Telemetry: 1W (75c) | 1D (100c) | 4H (100c) | 1H (100c) | 30M (200c) | 15M (250c) | 5M (280c) | 1M (250c)", flush=True)
        print(f"  - Daily Range Architecture: Floor ${session_low:.2f} | Ceiling ${session_high:.2f} | Current: {range_pct*100:.1f}%", flush=True)

        # 3. Check for recently closed trades and execute autonomous post-loss autopsies
        self.check_closed_trades_and_autopsy(
            macro=macro,
            range_pct=range_pct,
            session_low=session_low,
            session_high=session_high
        )

        # Check if any account has active loss cooldown to feed into memory gate
        active_loss_context = None
        for acc_id, loss_info in self.account_loss_cooldown.items():
            elapsed = time.time() - loss_info["time"]
            if elapsed < self.loss_cooldown_secs:
                active_loss_context = {
                    "in_cooldown": True,
                    "direction": loss_info["direction"],
                    "ticket": loss_info["ticket"],
                    "seconds_remaining": self.loss_cooldown_secs - elapsed
                }
                break

        # 4. Cognitive Deliberation with Full 6-Agent Council Consensus & Strict Confirmation
        thesis = self.brain.deliberate(
            current_price=price,
            mtf_candles=mtf_suite,
            m5_candles=mtf_suite.get("m5"),
            h1_candles=mtf_suite.get("h1"),
            recent_loss_context=active_loss_context
        )
        print(f"  - [COUNCIL CONSENSUS]: {thesis.action} ({thesis.confidence_score}% Conviction | {thesis.council_consensus_pct}% Agreement)", flush=True)
        if hasattr(thesis, "roundtable_transcript") and thesis.roundtable_transcript:
            print("  - [COUNCIL ROUNDTABLE CROSS-EXAMINATION & TESTIMONY]:", flush=True)
            for entry in thesis.roundtable_transcript:
                print(f"    * [{entry['speaker']}]: {entry['statement']}", flush=True)
        elif hasattr(thesis, "council_rationale") and thesis.council_rationale:
            for r in thesis.council_rationale:
                print(f"    * {r}", flush=True)
        print(f"  - Session: {thesis.session_phase} | Regime: {thesis.regime} | Setup: {thesis.metamorphosis_mode}", flush=True)
        print(f"  - Crowd Sentiment: {thesis.retail_long_pct}% Long / {thesis.retail_short_pct}% Short | Smart Money: {thesis.smart_money_bias}", flush=True)
        print(f"  - Memory Gate: {'APPROVED' if thesis.memory_gate_approved else 'VETOED / BLOCKED BY MEMORY'}", flush=True)
        if thesis.memory_warnings:
            for w in thesis.memory_warnings:
                print(f"    [MEMORY WARNING] {w}", flush=True)
        print(f"  - Sniper Plan: Entry ${thesis.entry_price} | SL ${thesis.stop_loss} | TP1 ${thesis.take_profit_1} (R:R {thesis.risk_reward_ratio}:1)", flush=True)
        print(f"  - Jarvis Monologue: {thesis.reasoning_monologue}", flush=True)

        # Sync live thesis & 4 Chambers briefing directly to Cockpit UI cache
        try:
            from trajedor.src.jarvis_server import update_status_thesis
            update_status_thesis(thesis)
        except Exception:
            pass

        # 5. Trade Doctor In-Flight Active Defense (Real-time M1 Adaptation, Partials & Dynamic Trailing)
        accounts = self.mt5_bridge.get_live_telemetry()
        for acc_id, acc_data in accounts.items():
            positions = acc_data.get("open_positions", [])
            for p in positions:
                if p.get("is_ai"):
                    ticket = p.get("ticket")
                    verdict = self.doctor.diagnose_position(
                        ticket=ticket,
                        direction=p.get("type", "BUY"),
                        entry_price=p.get("open_price", price),
                        current_price=price,
                        initial_sl=p.get("sl", price - 8.0),
                        take_profit=p.get("tp", price + 15.0),
                        volume=p.get("volume", 0.02),
                        current_sl=p.get("sl"),
                        m1_candles=m1_rates,
                        m5_candles=m5_rates
                    )
                    print(f"  [DEFENSE] [Trade Doctor #{acc_id}] Ticket #{ticket}: {verdict.threat_status} -> {verdict.recommended_action} ({verdict.forensic_diagnosis})")

                    # Live MT5 Action Execution
                    if verdict.recommended_action in ("CLOSE_PROFIT", "EARLY_CUT"):
                        close_res = self.mt5_bridge.close_position(acc_id=acc_id, ticket=ticket, comment=verdict.recommended_action)
                        print(f"    >>> [ACTIVE DEFENSE] Position #{ticket} CLOSED ({verdict.recommended_action}): {close_res}")
                    elif verdict.recommended_action == "PARTIAL_BOOK" and verdict.close_volume_pct > 0:
                        pos_vol = p.get("volume", 0.02)
                        partial_lot = round(pos_vol * verdict.close_volume_pct, 2)
                        if partial_lot >= 0.01 and pos_vol > 0.01:
                            close_res = self.mt5_bridge.close_position(acc_id=acc_id, ticket=ticket, volume=partial_lot, comment="PARTIAL_PROFIT")
                            print(f"    >>> [ACTIVE DEFENSE] Harvested {partial_lot} lots partial profit on #{ticket}: {close_res}")
                        if verdict.suggested_sl:
                            mod_res = self.mt5_bridge.modify_position_sl_tp(acc_id=acc_id, ticket=ticket, sl=verdict.suggested_sl)
                            print(f"    >>> [ACTIVE DEFENSE] Trailed SL to ${verdict.suggested_sl} for #{ticket}: {mod_res}")
                    elif verdict.recommended_action in ("LOCK_BREAKEVEN", "TRAIL_SL") and verdict.suggested_sl:
                        mod_res = self.mt5_bridge.modify_position_sl_tp(acc_id=acc_id, ticket=ticket, sl=verdict.suggested_sl)
                        print(f"    >>> [ACTIVE DEFENSE] Trailed SL to ${verdict.suggested_sl} for #{ticket}: {mod_res}")

        # 6. Autonomous Institutional Order Dispatch (Strict Multi-Agent Confirmation Only)
        min_confidence = 80
        if thesis.action in ("BUY", "SELL") and thesis.confidence_score >= min_confidence and thesis.memory_gate_approved:
            for acc_id, acc_data in accounts.items():
                if not acc_data.get("is_active", True):
                    continue

                # Check Post-Loss Directional Cooldown (Mandatory 15-min block after any loss)
                loss_info = self.account_loss_cooldown.get(acc_id)
                if loss_info:
                    elapsed = time.time() - loss_info["time"]
                    if elapsed < self.loss_cooldown_secs and thesis.action == loss_info["direction"]:
                        time_left = int(self.loss_cooldown_secs - elapsed)
                        print(f"  [DISPATCH BLOCKED] {acc_id} is in 15-minute Post-Loss Cooldown after Ticket #{loss_info['ticket']} loss ({time_left}s remaining). Skipping {thesis.action}.", flush=True)
                        continue

                # Anti-Churn Same-Price Protection Gate
                # Strictly prevents re-entering in the same direction within 6.0 points of prior trade exit for 30 minutes
                last_exit = self.account_last_exit.get(acc_id)
                if last_exit:
                    exit_elapsed = time.time() - last_exit.get("time", 0.0)
                    exit_price = last_exit.get("exit_price", 0.0)
                    exit_dir = last_exit.get("direction", "")
                    price_dist = abs(price - exit_price)
                    if exit_elapsed < 1800 and thesis.action == exit_dir and price_dist < 6.0:
                        remain_exit = int(1800 - exit_elapsed)
                        print(
                            f"  [DISPATCH BLOCKED] {acc_id}: Anti-Churn Same-Price Protection Active!\n"
                            f"    Prior {exit_dir} trade #{last_exit.get('ticket')} exited at ${exit_price:.2f} ({int(exit_elapsed)}s ago).\n"
                            f"    Current price ${price:.2f} is within {price_dist:.2f} pts of prior exit price.\n"
                            f"    Re-entering same direction at the same point is blocked for {remain_exit}s.",
                            flush=True
                        )
                        continue

                # Check minimum interval between orders to eliminate back-to-back scalping
                last_time = self.last_order_time.get(acc_id, 0.0)
                if time.time() - last_time < self.min_order_interval_secs:
                    remain = int(self.min_order_interval_secs - (time.time() - last_time))
                    print(f"  [DISPATCH THROTTLED] {acc_id}: Pacing gate active ({remain}s remaining before next allowed entry).", flush=True)
                    continue

                current_ai_pos = acc_data.get("current_ai_pos_count", 0)
                max_pos = acc_data.get("max_concurrent_positions", 3)
                if current_ai_pos >= max_pos:
                    continue

                # Anti-Clustering Gate: Strictly prevent opening multiple positions in the same 8-point zone
                open_ai_positions = [p for p in acc_data.get("open_positions", []) if p.get("is_ai")]
                if open_ai_positions:
                    too_close = False
                    for op in open_ai_positions:
                        open_p = float(op.get("open_price", 0.0))
                        if abs(price - open_p) < 8.0:  # Must be at least 8.0 points apart
                            too_close = True
                            break
                    if too_close:
                        print(f"  [DISPATCH SKIPPED] {acc_id}: Position already active within 8.0 pts of ${price:.2f}.", flush=True)
                        continue

                requested_lot = acc_data.get("max_single_trade_lot", 0.05)
                target_tp = thesis.take_profit_2 if thesis.take_profit_2 else thesis.take_profit_1
                res = self.mt5_bridge.dispatch_order(
                    acc_id=acc_id,
                    action=thesis.action,
                    requested_lot=requested_lot,
                    sl=thesis.stop_loss,
                    tp=target_tp,
                    comment="TRAJEDOR_SWING"
                )
                if res.get("success"):
                    self.last_order_time[acc_id] = time.time()
                    ticket_num = res.get("ticket")
                    print(f"  >>> [AUTO-DISPATCH SUCCESS] Fired {thesis.action} {res.get('volume')} lots on {acc_id} | Ticket: #{ticket_num} @ ${res.get('price'):.2f} (SL: ${thesis.stop_loss}, Major TP: ${target_tp} | R:R 1:{thesis.risk_reward_ratio})", flush=True)
                    
                    # Record entry in SQLite database for lifetime tracking
                    if ticket_num:
                        self.journal.record_entry(
                            ticket=ticket_num,
                            symbol=res.get("symbol", self.settings.PRIMARY_SYMBOL),
                            account_id=acc_id,
                            direction=thesis.action,
                            volume=float(res.get("volume", requested_lot)),
                            entry_price=float(res.get("price", price)),
                            sl=thesis.stop_loss,
                            tp=target_tp,
                            setup_type=thesis.metamorphosis_mode
                        )
                else:
                    reason = res.get('reason', 'Order rejected')
                    print(f"  >>> [AUTO-DISPATCH NOTICE / REJECTED] {acc_id}: {reason}", flush=True)
                    if "10027" in str(reason) or "AutoTrading" in str(reason):
                        print(f"      [BROKER PERMISSION REQUIRED]: Algo Trading is toggled OFF on {acc_id} terminal. Press Ctrl+E or click 'Algo Trading' in MT5 toolbar.", flush=True)
                    print(f"  >>> [MULTI-TIMEFRAME RE-SCREENING TRIGGERED]: Order rejected on {acc_id}. Calling all 6 agents to re-scan all 8 timeframes (1W to M1) for new opportunities...", flush=True)
                    if hasattr(thesis, "opportunity_hunt_plans") and thesis.opportunity_hunt_plans:
                        for p in thesis.opportunity_hunt_plans:
                            print(f"      * [{p['agent']} // {p['timeframes']}]: {p['plan']}", flush=True)

        print("[JARVIS MARK-85] Cycle complete. Standing by for next cognitive pulse.\n")

    def run_loop(self, poll_interval_secs: int = 10):
        self.is_running = True
        print("=" * 80)
        print("[TRAJEDOR] JARVIS MARK-85 AUTONOMOUS EXECUTIVE INITIALIZED")
        print("=" * 80)
        try:
            while self.is_running:
                self.run_cycle()
                time.sleep(poll_interval_secs)
        except KeyboardInterrupt:
            print("\n[JARVIS] Autonomous loop stopped by user.")


if __name__ == "__main__":
    executive = JarvisExecutive()
    executive.run_cycle()

