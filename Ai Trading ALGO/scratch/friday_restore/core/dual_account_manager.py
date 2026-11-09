"""
Dual-Account Independent Execution, Risk & Daily Target Manager for AI Trading Council.
Features:
1. Per-Account Custom Risk Profiles:
   - Account #1 (Master EUR): Dynamic lot sizing (up to admin max_lot_size), 3-tier trailing stop.
   - Account #2 (GTC Live Micro USD): Micro compounding, strict 0.01 lot, $1.50 SL cap, instant early BE.
2. Daily Profit Target Gate:
   - Monitors each account's closed trades realized P&L for today (since 00:00 UTC).
   - Once Daily Profit Target is reached (e.g. €150 on Acc 1, $3.00 on Acc 2), all new trading on that account is locked/halted for the day.
3. Daily Max Loss Defense:
   - If daily drawdown hits admin limit, trading halts for the day to preserve capital.
4. Live Hot-Reload Admin Config:
   - Reads dynamically from data/admin_config.json on each cycle without requiring engine restarts.
"""

import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config import CONFIG
from core.ai_ledger import AITradeLedger
from core.risk_manager import RiskManager
from core.execution_engine import MT5ExecutionEngine
from core.pro_trade_manager import ProTradeManager

ADMIN_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "admin_config.json")


class AccountProfile:
    def __init__(
        self,
        account_id: str,
        name: str,
        terminal_path: str,
        currency: str,
        magic_number: int,
        mode: str,
        is_active: bool = True,
        max_open_trades: int = 1,
        max_lot_size: float = 0.08,
        min_lot_size: float = 0.01,
        daily_profit_target: float = 150.0,
        daily_max_loss: float = 100.0,
        max_sl_points: float = 6.0,
        early_be_points: float = 0.40,
        quick_tp_points: float = 1.20,
        min_free_margin: float = 5.0
    ):
        self.account_id = account_id
        self.name = name
        self.terminal_path = terminal_path
        self.currency = currency
        self.magic_number = magic_number
        self.mode = mode
        self.is_active = is_active
        self.max_open_trades = max_open_trades
        self.max_lot_size = max_lot_size
        self.min_lot_size = min_lot_size
        self.daily_profit_target = daily_profit_target
        self.daily_max_loss = daily_max_loss
        self.max_sl_points = max_sl_points
        self.early_be_points = early_be_points
        self.quick_tp_points = quick_tp_points
        self.min_free_margin = min_free_margin
        
        self.last_trade_time = 0.0
        self.partially_closed_tickets = set()
        self.breakeven_locked_tickets = set()
        self.risk_manager = RiskManager(symbol=CONFIG.SYMBOL)
        self.today_realized_pnl = 0.0
        self.today_trade_count = 0
        self.target_reached_today = False
        self.max_loss_hit_today = False

    def connect(self) -> bool:
        if not mt5:
            return False
        return mt5.initialize(path=self.terminal_path)

    def shutdown(self):
        # Do not call mt5.shutdown() as it terminates global IPC session for other accounts/threads
        pass


class DualAccountManager:
    def __init__(self, symbol: str = CONFIG.SYMBOL):
        self.symbol = symbol
        self.accounts: List[AccountProfile] = []
        self._last_config_load_time = 0.0
        self.reload_config()

    def reload_config(self):
        """Loads and syncs live configurations from data/admin_config.json."""
        if os.path.exists(ADMIN_CONFIG_PATH):
            try:
                with open(ADMIN_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                acc_dict = data.get("accounts", {})
                new_accounts = []
                for acc_id, conf in acc_dict.items():
                    # Preserve existing memory state (e.g. breakeven tickets, last trade time)
                    existing = next((a for a in self.accounts if a.account_id == acc_id), None)
                    profile = AccountProfile(
                        account_id=acc_id,
                        name=conf.get("name", f"Account ({acc_id})"),
                        terminal_path=conf.get("terminal_path", ""),
                        currency=conf.get("currency", "USD"),
                        magic_number=int(conf.get("magic_number", 777888)),
                        mode=conf.get("mode", "STANDARD_PROP"),
                        is_active=bool(conf.get("is_active", True)),
                        max_open_trades=int(conf.get("max_open_trades", 1)),
                        max_lot_size=float(conf.get("max_lot_size", 0.08)),
                        min_lot_size=float(conf.get("min_lot_size", 0.01)),
                        daily_profit_target=float(conf.get("daily_profit_target", 100.0)),
                        daily_max_loss=float(conf.get("daily_max_loss", 50.0)),
                        max_sl_points=float(conf.get("max_sl_points", 6.0 if conf.get("mode") == "STANDARD_PROP" else 1.5)),
                        early_be_points=float(conf.get("early_be_points", 1.5 if conf.get("mode") == "STANDARD_PROP" else 0.40)),
                        quick_tp_points=float(conf.get("quick_tp_points", 4.0 if conf.get("mode") == "STANDARD_PROP" else 1.20)),
                        min_free_margin=float(conf.get("min_free_margin", 5.0))
                    )
                    if existing:
                        profile.last_trade_time = existing.last_trade_time
                        profile.partially_closed_tickets = existing.partially_closed_tickets
                        profile.breakeven_locked_tickets = existing.breakeven_locked_tickets
                        profile.today_realized_pnl = existing.today_realized_pnl
                    new_accounts.append(profile)
                self.accounts = new_accounts
                self._last_config_load_time = time.time()
            except Exception as e:
                print(f"[DualAccountManager] Error reading admin config: {e}")
        else:
            # Defaults
            self.accounts = [
                AccountProfile(
                    account_id="acc_1",
                    name="Account #1 (Master EUR)",
                    terminal_path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
                    currency="EUR",
                    magic_number=777888,
                    mode="STANDARD_PROP",
                    is_active=True,
                    max_open_trades=1,
                    max_lot_size=0.08,
                    daily_profit_target=150.0,
                    daily_max_loss=100.0
                ),
                AccountProfile(
                    account_id="acc_2",
                    name="Account #2 (GTC Live Micro USD)",
                    terminal_path=r"C:\Program Files\MetaTrader 5 - 1\terminal64.exe",
                    currency="USD",
                    magic_number=777999,
                    mode="MICRO_COMPOUNDING",
                    is_active=True,
                    max_open_trades=1,
                    max_lot_size=0.01,
                    daily_profit_target=3.0,
                    daily_max_loss=2.0
                )
            ]

    def update_daily_target_status(self, profile: AccountProfile):
        """Calculates today's closed deals realized P&L and checks Daily Target status."""
        if not profile.connect():
            return

        try:
            # Start of today in local/UTC time
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            today_end = now + timedelta(days=1)

            deals = mt5.history_deals_get(today_start, today_end)
            if deals:
                ai_magic_numbers = {profile.magic_number, CONFIG.MAGIC_NUMBER, 777888, 777999}
                today_out_deals = [
                    d for d in deals
                    if (d.entry == 1 or d.profit != 0.0)
                    and ((d.magic in ai_magic_numbers) or (d.comment and str(d.comment).upper().startswith("AI_")))
                ]
                profile.today_realized_pnl = round(float(sum(d.profit for d in today_out_deals)), 2)
                profile.today_trade_count = len(today_out_deals)
            else:
                profile.today_realized_pnl = 0.0
                profile.today_trade_count = 0

            # Target checks
            if profile.today_realized_pnl >= profile.daily_profit_target and profile.daily_profit_target > 0:
                if not profile.target_reached_today:
                    profile.target_reached_today = True
                    curr_sym = "€" if profile.currency == "EUR" else "$"
                    print(f"\n   🎉🎯 [{profile.name}] DAILY PROFIT TARGET ACHIEVED! (+{curr_sym}{profile.today_realized_pnl:.2f} / {curr_sym}{profile.daily_profit_target:.2f})")
                    print(f"      🛡️ Profit locked for the day! Halting new entries on this account until tomorrow.\n")
            else:
                profile.target_reached_today = False

            if profile.today_realized_pnl <= -abs(profile.daily_max_loss) and profile.daily_max_loss > 0:
                if not profile.max_loss_hit_today:
                    profile.max_loss_hit_today = True
                    curr_sym = "€" if profile.currency == "EUR" else "$"
                    print(f"\n   🛑⚠️ [{profile.name}] DAILY MAX LOSS REACHED ({curr_sym}{profile.today_realized_pnl:.2f} / -{curr_sym}{profile.daily_max_loss:.2f})")
                    print(f"      🛡️ Capital Preservation Halted! No more trades for this account today.\n")
            else:
                profile.max_loss_hit_today = False

        except Exception as e:
            print(f"[DualAccountManager] Error checking daily target for {profile.name}: {e}")
        finally:
            profile.shutdown()

    def evaluate_and_manage_all_accounts(
        self,
        market_payload: Dict[str, Any],
        news_payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Runs position management (trailing, profit booking) and updates daily target status.
        """
        # Periodic hot-reload check every 5 seconds
        if time.time() - self._last_config_load_time >= 5.0:
            self.reload_config()

        all_actions = []

        for profile in self.accounts:
            # Sync today's realized progress
            self.update_daily_target_status(profile)

            if not profile.connect():
                continue

            try:
                positions = mt5.positions_get(symbol=self.symbol)
                if not positions:
                    continue

                ai_positions = [
                    p for p in positions
                    if (p.magic == profile.magic_number) or (p.comment and str(p.comment).upper().startswith("AI_"))
                ]

                if not ai_positions:
                    continue

                tick = mt5.symbol_info_tick(self.symbol)
                bid = tick.bid if tick else 0.0
                ask = tick.ask if tick else 0.0

                for pos in ai_positions:
                    pos_type = "BUY" if pos.type == 0 else "SELL"
                    open_price = float(pos.price_open)
                    current_price = bid if pos_type == "BUY" else ask
                    profit = float(pos.profit)
                    sl = float(pos.sl or 0.0)
                    volume = float(pos.volume)
                    ticket = pos.ticket

                    price_gain = (current_price - open_price) if pos_type == "BUY" else (open_price - current_price)

                    # Micro account fast breakeven and profit lock
                    if profile.mode == "MICRO_COMPOUNDING":
                        # Early breakeven
                        if price_gain >= profile.early_be_points and ticket not in profile.breakeven_locked_tickets:
                            new_sl = open_price + 0.10 if pos_type == "BUY" else open_price - 0.10
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": self.symbol,
                                "sl": round(new_sl, 2),
                                "tp": round(pos.tp, 2) if pos.tp else 0.0
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                profile.breakeven_locked_tickets.add(ticket)
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "MICRO_EARLY_BREAKEVEN",
                                    "thought": f"Secured +${profit:.2f} ({price_gain:.2f} pts). SL moved to Breakeven @ {new_sl:.2f} to eliminate risk on $17 capital.",
                                    "result": "SL Moved to Breakeven"
                                })

                        # Quick Scalp Profit Lock
                        if price_gain >= profile.quick_tp_points or profit >= 1.00:
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": ticket,
                                "symbol": self.symbol,
                                "volume": volume,
                                "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                "price": bid if pos_type == "BUY" else ask,
                                "deviation": 20,
                                "magic": profile.magic_number,
                                "comment": "Chanakya_Micro_Bank",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "MICRO_PROFIT_BANK",
                                    "thought": f"🎯 Banked quick profit of +${profit:.2f} USD (+{price_gain:.2f} pts). Compounding account balance!",
                                    "result": f"Closed position #{ticket} in profit"
                                })

                    # Standard Prop Account 7-Sentry Lifecycle Management
                    elif profile.mode == "STANDARD_PROP":
                        initial_r = max(abs(open_price - sl), 5.0) if sl > 0 else 6.50
                        r_multiple = price_gain / initial_r
                        struct_m15 = (market_payload or {}).get("market_structures", {}).get("m15_execution_structure", {})
                        atr_val = float(struct_m15.get("atr_14", 6.50) or 6.50)
                        rsi_val = float(struct_m15.get("rsi_14", 50.0) or 50.0)
                        patterns_list = struct_m15.get("candlestick_patterns", [])

                        # SENTRY 1: DYNAMIC BREAKEVEN LOCK (+0.70R or >= 0.9x ATR)
                        if (r_multiple >= 0.70 or price_gain >= (atr_val * 0.9)) and ticket not in profile.breakeven_locked_tickets:
                            be_sl = open_price + 0.35 if pos_type == "BUY" else open_price - 0.35
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": self.symbol,
                                "sl": round(be_sl, 2),
                                "tp": round(pos.tp, 2) if pos.tp else 0.0
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                profile.breakeven_locked_tickets.add(ticket)
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "PROP_BREAKEVEN_LOCK",
                                    "thought": f"🛡️ Sentry 1 (BE Lock): Reached +{r_multiple:.2f}R gain (+{price_gain:.2f} pts). SL locked at Breakeven ({be_sl:.2f}). Risk is now ZERO.",
                                    "result": "SL Moved to Breakeven"
                                })

                        # SENTRY 3: MOMENTUM EXHAUSTION & REVERSAL SENTRY
                        is_exhaustion = False
                        ex_reason = ""
                        if pos_type == "BUY":
                            if rsi_val >= 76.0:
                                is_exhaustion, ex_reason = True, f"RSI Overbought ({rsi_val:.1f})"
                            for p in patterns_list:
                                if "BEARISH" in str(p.get("pattern", "")).upper():
                                    is_exhaustion, ex_reason = True, f"M15 Reversal {p.get('pattern')}"
                                    break
                        elif pos_type == "SELL":
                            if rsi_val <= 24.0:
                                is_exhaustion, ex_reason = True, f"RSI Oversold ({rsi_val:.1f})"
                            for p in patterns_list:
                                if "BULLISH" in str(p.get("pattern", "")).upper():
                                    is_exhaustion, ex_reason = True, f"M15 Reversal {p.get('pattern')}"
                                    break

                        if r_multiple >= 0.75 and is_exhaustion:
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": ticket,
                                "symbol": self.symbol,
                                "volume": volume,
                                "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                "price": bid if pos_type == "BUY" else ask,
                                "deviation": 25,
                                "magic": profile.magic_number,
                                "comment": f"Chanakya_Exhaust_{ex_reason[:10]}"[:31],
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "MOMENTUM_EXHAUSTION_EXIT",
                                    "thought": f"⚡ Sentry 3 (Exhaustion): Banked +{r_multiple:.2f}R profit before reversal. Reason: {ex_reason}.",
                                    "result": "Position closed in profit"
                                })
                                continue

                        # SENTRY 7: DYNAMIC PARTIAL-BOOKING OPTIMIZER (+1.2R or TP1)
                        if r_multiple >= 1.20 and ticket not in profile.partially_closed_tickets and volume >= 0.02:
                            close_vol = round(volume * 0.5, 2)
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": ticket,
                                "symbol": self.symbol,
                                "volume": close_vol,
                                "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                "price": bid if pos_type == "BUY" else ask,
                                "deviation": 25,
                                "magic": profile.magic_number,
                                "comment": "Chanakya_TP1_50",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                profile.partially_closed_tickets.add(ticket)
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "PROP_TP1_PARTIAL_50",
                                    "thought": f"🎯 Sentry 7 (Partial Optimizer): Target 1 hit (+{r_multiple:.2f}R). Closed {close_vol} lots. Runner trailing active.",
                                    "result": f"Partial closed {close_vol} lots"
                                })

                        # SENTRY 2: ATR-BASED DYNAMIC RATCHET TRAILING STOP
                        if r_multiple >= 1.10:
                            trail_dist = max(4.80, atr_val * 1.35)
                            target_sl = round(current_price - trail_dist if pos_type == "BUY" else current_price + trail_dist, 2)
                            should_update = False
                            if pos_type == "BUY" and target_sl > sl and target_sl > (open_price + 0.30):
                                should_update = True
                            elif pos_type == "SELL" and (sl <= 0 or target_sl < sl) and target_sl < (open_price - 0.30):
                                should_update = True

                            if should_update:
                                req = {
                                    "action": mt5.TRADE_ACTION_SLTP,
                                    "position": ticket,
                                    "symbol": self.symbol,
                                    "sl": target_sl,
                                    "tp": round(pos.tp, 2) if pos.tp else 0.0
                                }
                                res = mt5.order_send(req)
                                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                    all_actions.append({
                                        "account": profile.name,
                                        "ticket": ticket,
                                        "type": "PROP_ATR_RATCHET_TRAIL",
                                        "thought": f"📈 Sentry 2 (ATR Trail): SL advanced to {target_sl:,.2f} (1.35x ATR Trail). Accrued profits secured.",
                                        "result": f"SL Ratcheted to {target_sl}"
                                    })

            finally:
                profile.shutdown()

        return all_actions

    def execute_dual_sniper_signal(
        self,
        action: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        consensus_score: int,
        sniper_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Executes a validated sniper signal on both accounts independently,
        strictly respecting:
        - Admin Active toggle (is_active)
        - Daily Profit Target (stops if today's target achieved)
        - Daily Max Loss (stops if max loss breached)
        - Max Open Positions & Max Lot Size caps
        """
        self.reload_config()
        execution_results = []
        now_ts = time.time()

        for profile in self.accounts:
            # 1. Admin Active Check
            if not profile.is_active:
                print(f"   ⏸️ [{profile.name}] Trading PAUSED by Admin. Skipping signal.")
                continue

            # 2. Daily Target / Loss Safety Gates
            if profile.target_reached_today:
                curr_sym = "€" if profile.currency == "EUR" else "$"
                print(f"   🎯 [{profile.name}] Daily Target Achieved (+{curr_sym}{profile.today_realized_pnl:.2f} / {curr_sym}{profile.daily_profit_target:.2f}). No new trades today!")
                continue

            if profile.max_loss_hit_today:
                print(f"   🛑 [{profile.name}] Daily Max Loss Limit reached. Skipping trade.")
                continue

            # Cooldown per account
            if now_ts - profile.last_trade_time < 60.0:
                continue

            if not profile.connect():
                print(f"   ⚠️ [{profile.name}] Failed to connect to terminal: {profile.terminal_path}")
                continue

            try:
                broker_sym = self.resolve_broker_symbol(self.symbol)
                # 3. Check open positions on this account
                positions = mt5.positions_get(symbol=broker_sym)
                ai_positions = [
                    p for p in (positions or [])
                    if (p.magic == profile.magic_number) or (p.comment and (str(p.comment).upper().startswith("AI_") or "CHANAKYA" in str(p.comment).upper()))
                ]

                if len(ai_positions) >= profile.max_open_trades:
                    print(f"   ℹ️ [{profile.name}] Max open positions ({len(ai_positions)}/{profile.max_open_trades}) reached. Skipping.")
                    continue

                info = mt5.account_info()
                if not info:
                    continue

                term_info = mt5.terminal_info()
                if term_info and not term_info.trade_allowed:
                    print(f"   ⚠️ [{profile.name}] Algo Trading is DISABLED in this MT5 Terminal! Please click the 'Algo Trading' button (Ctrl+E) in MT5 to turn it GREEN.")

                if info and not info.trade_allowed:
                    print(f"   ⚠️ [{profile.name}] Trading is DISABLED for this Account (Login: {info.login}) by broker or Investor password mode.")

                equity = float(info.equity or 0.0)
                free_margin = float(info.margin_free or 0.0)

                # Free margin check
                if free_margin < profile.min_free_margin:
                    print(f"   ⚠️ [{profile.name}] Low free margin ({free_margin:.2f} {profile.currency} < {profile.min_free_margin:.2f}). Skipping.")
                    continue

                tick = mt5.symbol_info_tick(broker_sym)
                if not tick:
                    print(f"   ⚠️ [{profile.name}] Could not get live tick for '{broker_sym}'. Skipping.")
                    continue

                bid = tick.bid
                ask = tick.ask
                order_price = ask if action == "BUY" else bid

                # 4. Account-Specific Lot Sizing & SL/TP Rules with Admin Caps
                order_comment = "Chanakya_Buy" if action == "BUY" else "Chanakya_Sell"

                if profile.mode == "MICRO_COMPOUNDING":
                    # Micro Account: 0.01 lot capped to admin max_lot_size
                    lots = min(profile.max_lot_size, 0.01)
                    sl_dist = min(abs(order_price - stop_loss), profile.max_sl_points) if stop_loss > 0 else profile.max_sl_points
                    final_sl = round(order_price - sl_dist if action == "BUY" else order_price + sl_dist, 2)
                    final_tp = round(order_price + profile.quick_tp_points if action == "BUY" else order_price - profile.quick_tp_points, 2)

                else:
                    # Standard Account: Dynamic sizing clamped to admin max_lot_size
                    lots = profile.risk_manager.calculate_lot_size(
                        account_equity=equity,
                        entry_price=order_price,
                        stop_loss=stop_loss,
                        risk_pct=1.5,
                        confidence_score=consensus_score
                    )
                    lots = max(profile.min_lot_size, min(lots, profile.max_lot_size))
                    final_sl = round(stop_loss, 2) if stop_loss > 0 else 0.0
                    final_tp = round(take_profit, 2) if take_profit > 0 else 0.0

                # 5. Submit Market Order
                order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": broker_sym,
                    "volume": lots,
                    "type": order_type,
                    "price": order_price,
                    "sl": final_sl,
                    "tp": final_tp,
                    "deviation": 20,
                    "magic": profile.magic_number,
                    "comment": order_comment[:31],
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    ticket = result.order or result.deal
                    profile.last_trade_time = now_ts + 60.0
                    
                    AITradeLedger.record_executed_trade(
                        ticket=ticket,
                        symbol=self.symbol,
                        action=action,
                        volume=lots,
                        price=order_price,
                        sl=final_sl,
                        tp=final_tp,
                        consensus_score=consensus_score,
                        comment=order_comment
                    )

                    msg = f"Ticket #{ticket} executed ({lots} Lots @ {order_price:.2f}, SL={final_sl}, TP={final_tp})"
                    print(f"   ✅ [{profile.name}] {msg}")
                    execution_results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "ticket": ticket,
                        "success": True,
                        "message": msg,
                        "volume": lots,
                        "price": order_price
                    })
                else:
                    err = result.comment if result else f"Error code {mt5.last_error()}"
                    print(f"   ❌ [{profile.name}] Order Send Failed: {err}")
                    execution_results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "success": False,
                        "error": err
                    })

            finally:
                profile.shutdown()

        try:
            if CONFIG.MT5_PATH:
                mt5.initialize(path=CONFIG.MT5_PATH)
        except Exception:
            pass

        return execution_results
