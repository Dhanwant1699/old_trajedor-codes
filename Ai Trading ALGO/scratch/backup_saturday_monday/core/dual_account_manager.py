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
        allowed_symbols: Optional[List[str]] = None,
        symbol_lots: Optional[Dict[str, float]] = None,
        symbol_settings: Optional[Dict[str, Dict[str, Any]]] = None,
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
        self.allowed_symbols = allowed_symbols if allowed_symbols is not None else ["XAUUSD"]
        self.symbol_lots = symbol_lots if symbol_lots is not None else {
            "XAUUSD": max_lot_size,
            "BTCUSD": min(max_lot_size, 0.05)
        }
        
        # Initialize granular per-symbol settings for XAUUSD & BTCUSD
        default_xau_lot = self.symbol_lots.get("XAUUSD", max_lot_size)
        default_btc_lot = self.symbol_lots.get("BTCUSD", min(max_lot_size, 0.05))
        
        if symbol_settings is not None:
            self.symbol_settings = symbol_settings
        else:
            self.symbol_settings = {
                "XAUUSD": {
                    "max_lot_size": float(default_xau_lot),
                    "max_open_positions": int(max_open_trades),
                    "daily_profit_target": float(daily_profit_target),
                    "daily_max_loss": float(daily_max_loss)
                },
                "BTCUSD": {
                    "max_lot_size": float(default_btc_lot),
                    "max_open_positions": int(max_open_trades),
                    "daily_profit_target": float(daily_profit_target),
                    "daily_max_loss": float(daily_max_loss)
                }
            }

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

    def is_symbol_allowed(self, symbol: str) -> bool:
        """Checks whether this account profile is permitted to trade the requested symbol."""
        if not self.allowed_symbols:
            return True
        sym_clean = symbol.upper()
        for allowed in self.allowed_symbols:
            al_clean = allowed.upper()
            if al_clean == sym_clean:
                return True
            if ("XAU" in al_clean or "GOLD" in al_clean) and ("XAU" in sym_clean or "GOLD" in sym_clean):
                return True
            if ("BTC" in al_clean or "BITCOIN" in al_clean) and ("BTC" in sym_clean or "BITCOIN" in sym_clean):
                return True
        return False

    def get_lot_size_for_symbol(self, symbol: str) -> float:
        """Returns the specific configured maximum lot size for the given symbol."""
        sym_clean = "BTCUSD" if ("BTC" in symbol.upper() or "BITCOIN" in symbol.upper()) else "XAUUSD"
        if sym_clean in self.symbol_settings and "max_lot_size" in self.symbol_settings[sym_clean]:
            return float(self.symbol_settings[sym_clean]["max_lot_size"])
        if sym_clean in self.symbol_lots:
            return float(self.symbol_lots[sym_clean])
        return float(self.max_lot_size if sym_clean == "XAUUSD" else min(self.max_lot_size, 0.05))

    def get_max_positions_for_symbol(self, symbol: str) -> int:
        """Returns the maximum allowed concurrent open positions for the given symbol."""
        sym_clean = "BTCUSD" if ("BTC" in symbol.upper() or "BITCOIN" in symbol.upper()) else "XAUUSD"
        if sym_clean in self.symbol_settings and "max_open_positions" in self.symbol_settings[sym_clean]:
            return int(self.symbol_settings[sym_clean]["max_open_positions"])
        return int(self.max_open_trades)

    def get_daily_target_for_symbol(self, symbol: str) -> float:
        """Returns the daily profit target for the given symbol."""
        sym_clean = "BTCUSD" if ("BTC" in symbol.upper() or "BITCOIN" in symbol.upper()) else "XAUUSD"
        if sym_clean in self.symbol_settings and "daily_profit_target" in self.symbol_settings[sym_clean]:
            return float(self.symbol_settings[sym_clean]["daily_profit_target"])
        return float(self.daily_profit_target)

    def get_daily_loss_for_symbol(self, symbol: str) -> float:
        """Returns the daily max loss limit for the given symbol."""
        sym_clean = "BTCUSD" if ("BTC" in symbol.upper() or "BITCOIN" in symbol.upper()) else "XAUUSD"
        if sym_clean in self.symbol_settings and "daily_max_loss" in self.symbol_settings[sym_clean]:
            return float(self.symbol_settings[sym_clean]["daily_max_loss"])
        return float(self.daily_max_loss)

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

    @property
    def profiles(self) -> Dict[str, AccountProfile]:
        return {a.account_id: a for a in self.accounts}

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
                    
                    xau_conf_lot = float(conf.get("symbol_lots", {}).get("XAUUSD", conf.get("max_lot_size", 0.08)))
                    btc_conf_lot = float(conf.get("symbol_lots", {}).get("BTCUSD", min(float(conf.get("max_lot_size", 0.08)), 0.05)))
                    
                    sym_settings = conf.get("symbol_settings", {
                        "XAUUSD": {
                            "max_lot_size": xau_conf_lot,
                            "max_open_positions": int(conf.get("max_open_trades", 1)),
                            "daily_profit_target": float(conf.get("daily_profit_target", 100.0)),
                            "daily_max_loss": float(conf.get("daily_max_loss", 50.0))
                        },
                        "BTCUSD": {
                            "max_lot_size": btc_conf_lot,
                            "max_open_positions": int(conf.get("max_open_trades", 1)),
                            "daily_profit_target": float(conf.get("daily_profit_target", 100.0)),
                            "daily_max_loss": float(conf.get("daily_max_loss", 50.0))
                        }
                    })

                    profile = AccountProfile(
                        account_id=acc_id,
                        name=conf.get("name", f"Account ({acc_id})"),
                        terminal_path=conf.get("terminal_path", ""),
                        currency=conf.get("currency", "USD"),
                        magic_number=int(conf.get("magic_number", 777888)),
                        mode=conf.get("mode", "STANDARD_PROP"),
                        is_active=bool(conf.get("is_active", True)),
                        allowed_symbols=conf.get("allowed_symbols", ["XAUUSD"]),
                        symbol_lots=conf.get("symbol_lots", {
                            "XAUUSD": xau_conf_lot,
                            "BTCUSD": btc_conf_lot
                        }),
                        symbol_settings=sym_settings,
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
            profile.symbol_realized_pnl = {"XAUUSD": 0.0, "BTCUSD": 0.0}
            deals = None
            try:
                deals = mt5.history_deals_get(today_start, today_end)
            except Exception as d_err:
                deals = None
                ai_magic_numbers = {profile.magic_number, CONFIG.MAGIC_NUMBER, 777888, 777999, 778101, 778110}
                today_out_deals = [
                    d for d in deals
                    if (d.entry == 1 or d.profit != 0.0)
                    and ((d.magic in ai_magic_numbers) or (d.comment and (str(d.comment).upper().startswith("AI_") or "CHANAKYA" in str(d.comment).upper())))
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

    def resolve_broker_symbol(self, base_symbol: str) -> str:
        if mt5 is None:
            return base_symbol
        is_btc = "BTC" in base_symbol.upper() or "BITCOIN" in base_symbol.upper()
        is_gold = "XAU" in base_symbol.upper() or "GOLD" in base_symbol.upper()

        def _is_valid(sym_name: str) -> bool:
            try:
                t = mt5.symbol_info_tick(sym_name)
                bid = float(t.bid) if (t and t.bid > 0) else 0.0
                if bid <= 0:
                    info = mt5.symbol_info(sym_name)
                    bid = float(info.bid) if (info and info.bid > 0) else (float(info.last) if (info and info.last) else 0.0)
                if is_btc:
                    return bid >= 10000.0  # Real Bitcoin check
                if is_gold:
                    return bid >= 1000.0   # Real Gold check
                return bid > 0
            except Exception:
                return False

        if mt5.symbol_select(base_symbol, True) and _is_valid(base_symbol):
            return base_symbol

        if is_btc:
            candidates = ["BTCUSD", "BTCUSD+", "BTCUSDm", "BTCUSD.m", "BTCUSDT", "BTCUSDT+", "Bitcoin", "BTC/USD"]
        elif is_gold:
            candidates = ["XAUUSD", "XAUUSD+", "XAUUSDm", "XAUUSD.m", "XAUUSD_i", "XAUUSD.", "XAU/USD", "XAUEUR"]
        else:
            candidates = [base_symbol, f"{base_symbol}+", f"{base_symbol}m", f"{base_symbol}.m", f"{base_symbol}_i"]

        for alt in candidates:
            if mt5.symbol_select(alt, True) and _is_valid(alt):
                return alt

        all_syms = mt5.symbols_get()
        if all_syms:
            for s in all_syms:
                s_name = s.name
                s_upper = s_name.upper()
                match = False
                if is_btc:
                    if ("BTCUSD" in s_upper or "BTCUSDT" in s_upper or "BITCOIN" in s_upper) and not ("BTCL" in s_upper or s_upper == "BTC"):
                        match = True
                elif is_gold:
                    if ("XAUUSD" in s_upper or "XAU/USD" in s_upper or "XAUEUR" in s_upper) and (s_upper != "GOLD"):
                        match = True
                else:
                    if base_symbol.upper() in s_upper:
                        match = True

                if match and mt5.symbol_select(s_name, True) and _is_valid(s_name):
                    return s_name

        return base_symbol

    def evaluate_and_manage_all_accounts(
        self,
        market_payload: Dict[str, Any],
        news_payload: Dict[str, Any],
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs independent 7-Sentry trade management across all active accounts.
        Iterates over open positions across accounts.
        """
        all_actions = []
        target_sym = symbol or self.symbol

        for profile in self.accounts:
            # Sync today's realized progress
            self.update_daily_target_status(profile)

            if not profile.connect():
                continue

            try:
                broker_sym = self.resolve_broker_symbol(target_sym)
                positions = mt5.positions_get(symbol=broker_sym)
                if not positions:
                    continue

                ai_positions = [
                    p for p in positions
                    if (p.magic == profile.magic_number) or (p.comment and (str(p.comment).upper().startswith("AI_") or "CHANAKYA" in str(p.comment).upper()))
                ]

                if not ai_positions:
                    continue

                tick = mt5.symbol_info_tick(broker_sym)
                bid = tick.bid if tick else 0.0
                ask = tick.ask if tick else 0.0

                for pos in ai_positions:
                    ticket = pos.ticket
                    open_price = float(pos.price_open)
                    pos_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                    volume = float(pos.volume)
                    current_price = bid if pos_type == "BUY" else ask
                    profit = float(pos.profit)
                    sl = float(pos.sl)

                    price_gain = (current_price - open_price) if pos_type == "BUY" else (open_price - current_price)
                    is_btc = "BTC" in str(broker_sym).upper() or "BITCOIN" in str(broker_sym).upper()

                    # Micro Account Mode
                    if profile.mode == "MICRO_COMPOUNDING":
                        early_be_trigger = 35.0 if is_btc else profile.early_be_points
                        be_offset = 15.0 if is_btc else 0.10
                        quick_tp_dist = 250.0 if is_btc else profile.quick_tp_points
                        quick_tp_cash = 2.50 if is_btc else 1.00

                        # Instant Early BE
                        if price_gain >= early_be_trigger and ticket not in profile.breakeven_locked_tickets:
                            new_sl = round(open_price + be_offset if pos_type == "BUY" else open_price - be_offset, 2)
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": broker_sym,
                                "sl": new_sl,
                                "tp": round(pos.tp, 2) if pos.tp else 0.0
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                profile.breakeven_locked_tickets.add(ticket)
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "MICRO_EARLY_BREAKEVEN",
                                    "thought": f"Secured +${profit:.2f} ({price_gain:.2f} pts). SL moved to Breakeven @ {new_sl:.2f} to eliminate risk on micro capital.",
                                    "result": "SL Moved to Breakeven"
                                })

                        # Quick Scalp Profit Lock
                        if price_gain >= quick_tp_dist or profit >= quick_tp_cash:
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": ticket,
                                "symbol": broker_sym,
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

                    # Standard Prop Account — AI-DRIVEN Position Management (Gold) / Legacy (BTC)
                    elif profile.mode == "STANDARD_PROP":
                        fallback_r = 1000.0 if is_btc else 6.50
                        initial_r = max(abs(open_price - sl), fallback_r) if sl > 0 else fallback_r
                        r_multiple = price_gain / initial_r
                        struct_m15 = (market_payload or {}).get("market_structures", {}).get("m15_execution_structure", {})
                        default_atr = 1500.0 if is_btc else 6.50
                        atr_val = float(struct_m15.get("atr_14", default_atr) or default_atr)
                        rsi_val = float(struct_m15.get("rsi_14", 50.0) or 50.0)
                        patterns_list = struct_m15.get("candlestick_patterns", [])

                        # Asset-specific calibration
                        be_trigger_r = CONFIG.BTC_TRAILING_BE_TRIGGER_R if is_btc else CONFIG.TRAILING_BE_TRIGGER_R
                        be_buffer = CONFIG.BTC_TRAILING_BUFFER_DOLLARS if is_btc else 0.40
                        tp_tol = 25.0 if is_btc else 0.35
                        min_trail = CONFIG.BTC_MIN_TRAIL_DISTANCE if is_btc else 4.80
                        min_step = CONFIG.BTC_MIN_TRAIL_STEP if is_btc else 0.30
                        trail_multiplier = CONFIG.BTC_TRAILING_ATR_MULTIPLIER if is_btc else CONFIG.TRAILING_ATR_MULTIPLIER
                        trail_trigger_r = CONFIG.BTC_TRAILING_LOCK_TRIGGER_R if is_btc else 1.00

                        # =========================================================
                        # 🧠 Unified AI Position Management Agent (Gold & Bitcoin)
                        # =========================================================
                        pos_comment = str(pos.comment or "").upper()
                        is_scalp_trade = "SCALP" in pos_comment
                        pos_trade_style = "SCALP" if is_scalp_trade else "STANDARD_PROP"

                        if is_btc:
                            if not hasattr(self, '_btc_position_agent'):
                                from agents.btcusd.btcusd_position_manager_agent import CryptoPositionManagerAgent
                                self._btc_position_agent = CryptoPositionManagerAgent()
                            active_pos_agent = self._btc_position_agent
                        else:
                            if not hasattr(self, '_ai_position_agent'):
                                from agents.xauusd.xauusd_position_manager_agent import GoldPositionManagerAgent
                                self._ai_position_agent = GoldPositionManagerAgent()
                            active_pos_agent = self._ai_position_agent

                        m5_struct = (market_payload or {}).get("market_structures", {}).get("m5_scalp_structure", {})
                        tick_flow = (market_payload or {}).get("market_structures", {}).get("tick_order_flow", {})
                        vdelta = (market_payload or {}).get("market_structures", {}).get("volume_delta", {})
                        regime_info = (market_payload or {}).get("market_structures", {}).get("regime_detection", {})

                        position_context = {
                            "ticket": ticket,
                            "symbol": target_sym,
                            "type": pos_type,
                            "trade_style": pos_trade_style,
                            "entry_price": open_price,
                            "current_price": current_price,
                            "sl": sl,
                            "tp": float(pos.tp) if pos.tp else 0.0,
                            "volume": volume,
                            "profit_pnl": profit,
                            "price_gain": price_gain,
                            "r_multiple": r_multiple,
                            "time_in_trade_mins": 0.0,
                            "already_partial_closed": ticket in profile.partially_closed_tickets,
                            "already_breakeven_locked": ticket in profile.breakeven_locked_tickets,
                            "currency": profile.currency
                        }
                        market_snapshot = {
                            "m5_structure": m5_struct,
                            "m15_structure": struct_m15,
                            "tick_order_flow": tick_flow,
                            "volume_delta": vdelta,
                            "regime": regime_info
                        }

                        ai_decision = active_pos_agent.evaluate_position(position_context, market_snapshot)
                        ai_action = ai_decision.get("action", "HOLD_POSITION")
                        ai_reasoning = ai_decision.get("reasoning", "")

                        # SCALP PROACTIVE BOOKING OVERRIDE:
                        # If trade was opened as a SCALP and price moved in favor by >= 0.50R or quick thrust (Gold >= $1.20, BTC >= $250),
                        # ensure immediate early Breakeven lock or partial profit bank!
                        scalp_thrust_met = (is_scalp_trade and (r_multiple >= 0.50 or (price_gain >= (250.0 if is_btc else 1.20))))
                        if scalp_thrust_met and ticket not in profile.breakeven_locked_tickets:
                            if ai_action == "HOLD_POSITION":
                                ai_action = "MOVE_TO_BREAKEVEN"
                                ai_reasoning = f"Scalp momentum thrust reached (+{price_gain:.2f} pts). Locking risk-free Breakeven immediately."

                        if ai_action == "TAKE_PARTIAL_PROFIT" and ticket not in profile.partially_closed_tickets:
                            if volume >= 0.02:
                                close_pct = ai_decision.get("partial_close_pct", 50) / 100.0
                                close_pct = max(0.20, min(0.80, close_pct))
                                close_vol = max(0.01, round(volume * close_pct, 2))
                                req = {
                                    "action": mt5.TRADE_ACTION_DEAL,
                                    "position": ticket,
                                    "symbol": broker_sym,
                                    "volume": close_vol,
                                    "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                    "price": bid if pos_type == "BUY" else ask,
                                    "deviation": 25,
                                    "magic": profile.magic_number,
                                    "comment": f"Chanakya_AI_{pos_trade_style[:5]}Part",
                                    "type_time": mt5.ORDER_TIME_GTC,
                                    "type_filling": mt5.ORDER_FILLING_IOC
                                }
                                res = mt5.order_send(req)
                                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                    profile.partially_closed_tickets.add(ticket)
                                    # Lock BE on remaining runner
                                    be_sl = open_price + be_buffer if pos_type == "BUY" else open_price - be_buffer
                                    be_req = {
                                        "action": mt5.TRADE_ACTION_SLTP,
                                        "position": ticket,
                                        "symbol": broker_sym,
                                        "sl": round(be_sl, 2),
                                        "tp": round(pos.tp, 2) if pos.tp else 0.0
                                    }
                                    mt5.order_send(be_req)
                                    all_actions.append({
                                        "account": profile.name,
                                        "ticket": ticket,
                                        "type": "AI_PARTIAL_PROFIT",
                                        "thought": f"🧠 AI Position Agent [{pos_trade_style}]: Banked {int(close_pct*100)}% ({close_vol} lots @ +{r_multiple:.2f}R). {ai_reasoning[:100]}",
                                        "result": f"Partial closed {close_vol} lots"
                                    })
                            else:
                                if ticket not in profile.breakeven_locked_tickets:
                                    be_sl = open_price + be_buffer if pos_type == "BUY" else open_price - be_buffer
                                    be_req = {
                                        "action": mt5.TRADE_ACTION_SLTP,
                                        "position": ticket,
                                        "symbol": broker_sym,
                                        "sl": round(be_sl, 2),
                                        "tp": round(pos.tp, 2) if pos.tp else 0.0
                                    }
                                    res = mt5.order_send(be_req)
                                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                        profile.breakeven_locked_tickets.add(ticket)

                        elif ai_action == "MOVE_TO_BREAKEVEN" and ticket not in profile.breakeven_locked_tickets:
                            new_sl = ai_decision.get("new_sl_price")
                            if not new_sl or new_sl <= 0:
                                new_sl = open_price + be_buffer if pos_type == "BUY" else open_price - be_buffer
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": broker_sym,
                                "sl": round(float(new_sl), 2),
                                "tp": round(pos.tp, 2) if pos.tp else 0.0
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                profile.breakeven_locked_tickets.add(ticket)
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "AI_BREAKEVEN_LOCK",
                                    "thought": f"🧠 AI Position Agent [{pos_trade_style}]: Locked BE @ +{r_multiple:.2f}R. {ai_reasoning[:100]}",
                                    "result": "SL Moved to Breakeven"
                                })

                        elif ai_action == "CLOSE_FULL":
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": ticket,
                                "symbol": broker_sym,
                                "volume": volume,
                                "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                "price": bid if pos_type == "BUY" else ask,
                                "deviation": 25,
                                "magic": profile.magic_number,
                                "comment": f"Chanakya_AI_{pos_trade_style[:5]}Exit",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "AI_FULL_EXIT",
                                    "thought": f"🧠 AI Position Agent [{pos_trade_style}]: Full exit @ +{r_multiple:.2f}R (+${profit:.2f}). {ai_reasoning[:100]}",
                                    "result": f"Position #{ticket} closed by AI"
                                })
                                continue

                        elif ai_action == "TIGHTEN_TRAIL":
                            new_sl = ai_decision.get("new_sl_price")
                            if new_sl and new_sl > 0:
                                valid = (pos_type == "BUY" and new_sl > sl) or (pos_type == "SELL" and (sl <= 0 or new_sl < sl))
                                if valid:
                                    req = {
                                        "action": mt5.TRADE_ACTION_SLTP,
                                        "position": ticket,
                                        "symbol": broker_sym,
                                        "sl": round(float(new_sl), 2),
                                        "tp": round(pos.tp, 2) if pos.tp else 0.0
                                    }
                                    res = mt5.order_send(req)
                                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                        all_actions.append({
                                            "account": profile.name,
                                            "ticket": ticket,
                                            "type": "AI_TRAIL_TIGHTEN",
                                            "thought": f"🧠 AI Position Agent [{pos_trade_style}]: Tightened SL to {new_sl:,.2f}. {ai_reasoning[:100]}",
                                            "result": f"SL tightened to {new_sl}"
                                        })

                        # else: HOLD_POSITION — AI says do nothing

                        # SENTRY 2: ATR-BASED DYNAMIC RATCHET TRAILING STOP (BTC 2.75x ATR / Gold 1.35x ATR)
                        if r_multiple >= trail_trigger_r:
                            trail_dist = max(min_trail, atr_val * trail_multiplier)
                            target_sl = round(current_price - trail_dist if pos_type == "BUY" else current_price + trail_dist, 2)
                            should_update = False
                            if pos_type == "BUY" and target_sl > sl and target_sl > (open_price + min_step):
                                should_update = True
                            elif pos_type == "SELL" and (sl <= 0 or target_sl < sl) and target_sl < (open_price - min_step):
                                should_update = True

                            if should_update and abs(target_sl - sl) >= min_step:
                                req = {
                                    "action": mt5.TRADE_ACTION_SLTP,
                                    "position": ticket,
                                    "symbol": broker_sym,
                                    "sl": target_sl,
                                    "tp": round(pos.tp, 2) if pos.tp else 0.0
                                }
                                res = mt5.order_send(req)
                                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                    all_actions.append({
                                        "account": profile.name,
                                        "ticket": ticket,
                                        "type": "PROP_ATR_RATCHET_TRAIL",
                                        "thought": f"📈 Sentry 2 (ATR Trail): SL advanced to {target_sl:,.2f} ({trail_multiplier:.2f}x ATR Trail). Accrued profits secured.",
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
        sniper_state: Dict[str, Any],
        symbol: str = "XAUUSD",
        account_allocations: Optional[Dict[str, Any]] = None,
        trade_style: str = "STANDARD_PROP"
    ) -> List[Dict[str, Any]]:
        """
        Executes a validated sniper signal across all eligible accounts independently,
        strictly respecting:
        - Per-Account AI planned lot size & allocations from CRO Risk Planner
        - Allowed symbol filtering (XAUUSD, BTCUSD, or Both)
        - Symbol-specific lot sizing and maximum lot ceilings
        - Admin Active toggle (is_active)
        - Daily Profit Target (stops if today's target achieved)
        - Daily Max Loss (stops if max loss breached)
        - Max Open Positions & Max Lot Size caps
        """
        self.reload_config()
        execution_results = []
        now_ts = time.time()
        target_sym = symbol or self.symbol

        for profile in self.accounts:
            # 1. Admin Active Check
            if not profile.is_active:
                print(f"   ⏸️ [{profile.name}] Trading PAUSED by Admin. Skipping signal.")
                continue

            # 2. Asset Selection Check (XAUUSD / BTCUSD / Both)
            if not profile.is_symbol_allowed(target_sym):
                print(f"   ⏸️ [{profile.name}] Asset {target_sym} not in allowed symbols {profile.allowed_symbols}. Skipping.")
                continue

            # 3. Daily Target / Loss Safety Gates
            daily_target = profile.get_daily_target_for_symbol(target_sym)
            daily_max_loss = profile.get_daily_loss_for_symbol(target_sym)

            if profile.today_realized_pnl >= daily_target:
                curr_sym = "€" if profile.currency == "EUR" else "$"
                print(f"   🎯 [{profile.name}] Daily Target Achieved (+{curr_sym}{profile.today_realized_pnl:.2f} / {curr_sym}{daily_target:.2f} for {target_sym}). No new trades today!")
                continue

            if profile.today_realized_pnl <= -abs(daily_max_loss):
                print(f"   🛑 [{profile.name}] Daily Max Loss Limit reached ({profile.today_realized_pnl:.2f} <= -{daily_max_loss:.2f} for {target_sym}). Skipping trade.")
                continue

            # Cooldown per account
            if now_ts - profile.last_trade_time < 60.0:
                continue

            if not profile.connect():
                print(f"   ⚠️ [{profile.name}] Failed to connect to terminal: {profile.terminal_path}")
                continue

            try:
                broker_sym = self.resolve_broker_symbol(target_sym)

                # 4. Check open positions on this account for this symbol
                positions = mt5.positions_get(symbol=broker_sym)
                ai_positions = [
                    p for p in (positions or [])
                    if (p.magic == profile.magic_number) or (p.comment and (str(p.comment).upper().startswith("AI_") or "CHANAKYA" in str(p.comment).upper()))
                ]

                max_pos_for_sym = profile.get_max_positions_for_symbol(target_sym)
                if len(ai_positions) >= max_pos_for_sym:
                    print(f"   ℹ️ [{profile.name}] Max open positions for {target_sym} ({len(ai_positions)}/{max_pos_for_sym}) reached. Skipping.")
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

                # 5. Asset-Specific Lot Sizing & SL/TP Rules with Multi-Account AI Risk Plan
                is_scalp = (trade_style == "SCALP")
                is_btc = "BTC" in target_sym.upper() or "BITCOIN" in target_sym.upper()
                order_comment = f"Chanakya_{'Scalp' if is_scalp else 'Prop'}_{action.capitalize()}"
                max_lot_for_symbol = profile.get_lot_size_for_symbol(target_sym)

                # Check if CRO Multi-Account Risk Planner prepared a specific allocation for this account
                alloc = (account_allocations or {}).get(profile.account_id)
                if alloc:
                    if alloc.get("status") == "SKIPPED":
                        print(f"   ⏸️ [{profile.name}] AI Multi-Account Risk Planner SKIPPED: {alloc.get('reason', 'Policy veto')}")
                        continue
                    planned_lots = float(alloc.get("planned_lots", 0.0))
                else:
                    planned_lots = 0.0

                if profile.mode == "MICRO_COMPOUNDING":
                    # Micro Account: planned lot or 0.01 lot capped to symbol max lot
                    lots = planned_lots if planned_lots > 0 else min(max_lot_for_symbol, 0.01)
                    lots = max(profile.min_lot_size, min(lots, max_lot_for_symbol))
                    sl_dist = min(abs(order_price - stop_loss), profile.max_sl_points) if stop_loss > 0 else profile.max_sl_points
                    final_sl = round(order_price - sl_dist if action == "BUY" else order_price + sl_dist, 2)
                    final_tp = round(order_price + profile.quick_tp_points if action == "BUY" else order_price - profile.quick_tp_points, 2)

                else:
                    # Standard Account: Use planned lot from AI CRO or calculate dynamically per equity & quorum
                    if planned_lots > 0:
                        lots = planned_lots
                    else:
                        lots = profile.risk_manager.calculate_lot_size(
                            account_equity=equity,
                            entry_price=order_price,
                            stop_loss=stop_loss,
                            risk_pct=1.5,
                            confidence_score=consensus_score,
                            symbol=broker_sym,
                            max_lot_cap=max_lot_for_symbol
                        )
                    lots = max(profile.min_lot_size, min(lots, max_lot_for_symbol))
                    final_sl = round(stop_loss, 2) if stop_loss > 0 else 0.0
                    final_tp = round(take_profit, 2) if take_profit > 0 else 0.0

                # 5b. Strict 5% Aggregate Account Risk Cap Check (Including All Open AI Trades)
                max_allowed_portfolio_risk_pct = float(getattr(CONFIG, "MAX_PORTFOLIO_AGGREGATE_RISK_PCT", 5.0))
                max_risk_dollars = equity * (max_allowed_portfolio_risk_pct / 100.0)

                # Query live open positions on this account
                open_pos = mt5.positions_get() or ()
                existing_open_risk = 0.0
                for op in open_pos:
                    op_sym = str(op.symbol).upper()
                    op_contract = 1.0 if ("BTC" in op_sym or "BITCOIN" in op_sym) else 100.0
                    if op.sl > 0:
                        if op.type == 0 and op.sl >= op.price_open:  # BUY with SL >= entry
                            p_risk = 0.0
                        elif op.type == 1 and op.sl <= op.price_open:  # SELL with SL <= entry
                            p_risk = 0.0
                        else:
                            p_risk = abs(op.price_open - op.sl) * op_contract * op.volume
                    else:
                        p_risk = (1000.0 if "BTC" in op_sym else 10.0) * op_contract * op.volume
                    existing_open_risk += p_risk

                # Calculate new proposed trade risk
                target_contract = 1.0 if is_btc else 100.0
                proposed_sl_dist = abs(order_price - final_sl) if final_sl > 0 else (1000.0 if is_btc else 10.0)
                loss_per_lot = proposed_sl_dist * target_contract
                new_trade_risk = loss_per_lot * lots
                total_risk_after_trade = existing_open_risk + new_trade_risk
                total_risk_pct = (total_risk_after_trade / equity * 100.0) if equity > 0 else 0.0

                if total_risk_pct > max_allowed_portfolio_risk_pct:
                    remaining_budget = max(0.0, max_risk_dollars - existing_open_risk)
                    if remaining_budget <= 0.0 or (existing_open_risk / equity * 100.0) >= max_allowed_portfolio_risk_pct:
                        print(f"   🛡️ [{profile.name}] RISK VETO: Account already has {existing_open_risk/equity*100.0:.2f}% open risk (>= {max_allowed_portfolio_risk_pct}% cap). Skipping trade to preserve capital.")
                        continue
                    # Scale down lots to fit strictly inside <= 5% total risk
                    if loss_per_lot > 0:
                        capped_lots = round(remaining_budget / loss_per_lot, 2)
                        if capped_lots < profile.min_lot_size:
                            print(f"   🛡️ [{profile.name}] RISK VETO: Remaining 5% risk budget ({remaining_budget/equity*100.0:.2f}%) cannot afford minimum {profile.min_lot_size} lot. Skipping.")
                            continue
                        print(f"   🛡️ [{profile.name}] 5% Risk Cap: Resized lots from {lots:.2f} to {capped_lots:.2f} so total portfolio risk remains <= {max_allowed_portfolio_risk_pct}%.")
                        lots = capped_lots

                print(f"   🤖 [{profile.name}] AI Planned Execution [{trade_style}]: {lots:.2f} Lots (Equity: {equity:.2f} {profile.currency} | Mode: {profile.mode} | Total Risk: {(existing_open_risk + loss_per_lot*lots)/equity*100.0:.2f}% <= 5.0%)")

                # 6. Submit Market Order with Dynamic Filling Mode Resolution
                order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
                
                # Dynamically resolve broker supported filling mode
                filling_type = mt5.ORDER_FILLING_IOC
                sym_info = mt5.symbol_info(broker_sym)
                if sym_info:
                    if sym_info.filling_mode & 2:
                        filling_type = mt5.ORDER_FILLING_IOC
                    elif sym_info.filling_mode & 1:
                        filling_type = mt5.ORDER_FILLING_FOK
                    elif sym_info.filling_mode & 4:
                        filling_type = mt5.ORDER_FILLING_RETURN

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": broker_sym,
                    "volume": float(lots),
                    "type": order_type,
                    "price": float(order_price),
                    "sl": float(final_sl),
                    "tp": float(final_tp),
                    "deviation": 25,
                    "magic": profile.magic_number,
                    "comment": order_comment[:31],
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling_type,
                }

                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    ticket = result.order or result.deal
                    profile.last_trade_time = now_ts + 60.0
                    
                    AITradeLedger.record_executed_trade(
                        ticket=ticket,
                        symbol=target_sym,
                        action=action,
                        volume=lots,
                        price=order_price,
                        sl=final_sl,
                        tp=final_tp,
                        consensus_score=consensus_score,
                        comment=order_comment
                    )

                    msg = f"Ticket #{ticket} executed on {target_sym} ({lots} Lots @ {order_price:.2f}, SL={final_sl}, TP={final_tp})"
                    print(f"   ✅ [{profile.name}] {msg}")
                    execution_results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "ticket": ticket,
                        "symbol": target_sym,
                        "success": True,
                        "message": msg,
                        "volume": lots,
                        "price": order_price
                    })
                else:
                    ret_code = result.retcode if result else mt5.last_error()
                    comment = result.comment if result else "Unknown MT5 execution error"
                    err_msg = f"Order failed on {broker_sym}: Retcode {ret_code} ({comment})"
                    print(f"   ❌ [{profile.name}] {err_msg}")
                    execution_results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "symbol": target_sym,
                        "success": False,
                        "error": err_msg
                    })

            finally:
                profile.shutdown()

        try:
            if CONFIG.MT5_PATH:
                mt5.initialize(path=CONFIG.MT5_PATH)
        except Exception:
            pass

        return execution_results

    def execute_manual_market_order(
        self,
        action: str,
        symbol: str = "XAUUSD",
        account_id: str = "ALL",
        volume: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a manual or UI-triggered market order on one or all eligible accounts.
        Enforces allowed_symbols permissions, symbol_lots sizing, and 'Chanakya' comments.
        """
        self.reload_config()
        results = []
        action = action.upper()
        target_sym = symbol.upper()
        if "BTC" in target_sym:
            target_sym = "BTCUSD"
        elif "GOLD" in target_sym or "XAU" in target_sym:
            target_sym = "XAUUSD"

        # Filter target accounts
        if account_id == "ALL":
            target_profiles = [p for p in self.accounts if p.is_active and p.is_symbol_allowed(target_sym)]
        else:
            target_profiles = [p for p in self.accounts if p.account_id == account_id]

        if not target_profiles:
            return [{
                "account_id": account_id,
                "account_name": account_id,
                "symbol": target_sym,
                "success": False,
                "error": f"No active account found with permission to trade {target_sym}."
            }]

        from core.council_state import CouncilStateManager
        c_state = CouncilStateManager.get_state()
        s_data = c_state.get("symbols", {}).get(target_sym, {})

        for profile in target_profiles:
            if not profile.is_symbol_allowed(target_sym):
                results.append({
                    "account_id": profile.account_id,
                    "account_name": profile.name,
                    "symbol": target_sym,
                    "success": False,
                    "error": f"Account '{profile.name}' is not configured to trade {target_sym} (allowed: {profile.allowed_symbols})."
                })
                continue

            if not profile.connect():
                results.append({
                    "account_id": profile.account_id,
                    "account_name": profile.name,
                    "symbol": target_sym,
                    "success": False,
                    "error": f"Could not connect to MT5 terminal at {profile.terminal_path}."
                })
                continue

            try:
                broker_sym = self.resolve_broker_symbol(target_sym)
                tick = mt5.symbol_info_tick(broker_sym)
                if not tick:
                    results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "symbol": target_sym,
                        "success": False,
                        "error": f"Could not retrieve live price tick for {broker_sym}."
                    })
                    continue

                order_price = tick.ask if action == "BUY" else tick.bid
                order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL

                # Determine lot size: either custom volume passed from UI or account profile's symbol lot
                if volume and volume > 0:
                    lots = round(min(volume, profile.get_lot_size_for_symbol(target_sym) * 2.0), 2)
                else:
                    lots = profile.get_lot_size_for_symbol(target_sym)

                # Determine SL & TP
                state_sl = float(s_data.get("stop_loss", 0.0) or 0.0)
                state_tp = float(s_data.get("take_profit_1", 0.0) or 0.0)
                
                if target_sym == "BTCUSD":
                    default_risk = 450.0
                    final_sl = state_sl if state_sl > 0 else round(order_price - default_risk if action == "BUY" else order_price + default_risk, 2)
                    final_tp = state_tp if state_tp > 0 else round(order_price + (default_risk * 1.75) if action == "BUY" else order_price - (default_risk * 1.75), 2)
                else:
                    default_risk = 8.50
                    final_sl = state_sl if state_sl > 0 else round(order_price - default_risk if action == "BUY" else order_price + default_risk, 2)
                    final_tp = state_tp if state_tp > 0 else round(order_price + (default_risk * 1.75) if action == "BUY" else order_price - (default_risk * 1.75), 2)

                order_comment = f"Chanakya_{action.capitalize()}"
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": broker_sym,
                    "volume": float(lots),
                    "type": order_type,
                    "price": float(order_price),
                    "sl": float(final_sl),
                    "tp": float(final_tp),
                    "deviation": 20,
                    "magic": profile.magic_number,
                    "comment": order_comment[:31],
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    ticket = res.order or res.deal
                    AITradeLedger.record_executed_trade(
                        ticket=ticket,
                        symbol=target_sym,
                        action=action,
                        volume=lots,
                        price=order_price,
                        sl=final_sl,
                        tp=final_tp,
                        consensus_score=95,
                        comment=order_comment
                    )
                    results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "ticket": ticket,
                        "symbol": target_sym,
                        "success": True,
                        "message": f"Successfully executed {action} {lots} Lots on {profile.name} (Ticket #{ticket})",
                        "volume": lots,
                        "price": order_price
                    })
                else:
                    err = res.comment if res else f"Error code {mt5.last_error()}"
                    results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "symbol": target_sym,
                        "success": False,
                        "error": f"Broker error: {err}"
                    })
            except Exception as e:
                results.append({
                    "account_id": profile.account_id,
                    "account_name": profile.name,
                    "symbol": target_sym,
                    "success": False,
                    "error": str(e)
                })
            finally:
                profile.shutdown()

        try:
            if CONFIG.MT5_PATH:
                mt5.initialize(path=CONFIG.MT5_PATH)
        except Exception:
            pass

        return results
