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
from core.council_state import CouncilStateManager

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
        min_free_margin: float = 5.0,
        tp1_close_pct: float = 50.0
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
        self.tp1_close_pct = tp1_close_pct
        
        self.last_trade_time = 0.0
        self.partially_closed_tickets = set()
        self.breakeven_locked_tickets = set()
        self.tier1_partial_tickets = set()
        self.tier2_partial_tickets = set()
        self.risk_manager = RiskManager(symbol=CONFIG.SYMBOL)
        self.today_realized_pnl = 0.0
        self.today_trade_count = 0
        self.target_reached_today = False
        self.max_loss_hit_today = False

    def connect(self) -> bool:
        if not mt5:
            return False
        try:
            if not self.terminal_path:
                return mt5.initialize(timeout=3000)
            return mt5.initialize(path=self.terminal_path, timeout=3000)
        except Exception:
            return False

    def shutdown(self):
        # Do not call mt5.shutdown() as it terminates global IPC session for other accounts/threads
        pass


class DualAccountManager:
    def __init__(self, symbol: str = CONFIG.SYMBOL):
        self.symbol = symbol
        self.accounts: List[AccountProfile] = []
        self._last_config_load_time = 0.0
        self.reload_config()

    def reload_config(self, force: bool = False):
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
                        min_free_margin=float(conf.get("min_free_margin", 5.0)),
                        tp1_close_pct=float(conf.get("tp1_close_pct", 50.0))
                    )
                    if existing:
                        profile.last_trade_time = existing.last_trade_time
                        profile.partially_closed_tickets = existing.partially_closed_tickets
                        profile.breakeven_locked_tickets = existing.breakeven_locked_tickets
                        profile.tier1_partial_tickets = getattr(existing, "tier1_partial_tickets", set())
                        profile.tier2_partial_tickets = getattr(existing, "tier2_partial_tickets", set())
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
        current_state = CouncilStateManager.get_state()
        council_decision = current_state.get("symbols", {}).get(self.symbol, {})

        for profile in self.accounts:
            # Sync today's realized progress
            self.update_daily_target_status(profile)

            if not profile.connect():
                continue

            try:
                broker_sym = self.resolve_broker_symbol(self.symbol)
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
                    pos_type = "BUY" if pos.type == 0 else "SELL"
                    open_price = float(pos.price_open)
                    current_price = bid if pos_type == "BUY" else ask
                    profit = float(pos.profit)
                    sl = float(pos.sl or 0.0)
                    volume = float(pos.volume)
                    ticket = pos.ticket

                    price_gain = (current_price - open_price) if pos_type == "BUY" else (open_price - current_price)
                    initial_r = max(abs(open_price - sl), 5.0) if sl > 0 else 6.50
                    r_multiple = price_gain / initial_r

                    sym_info = mt5.symbol_info(broker_sym)
                    fm = getattr(sym_info, "filling_mode", 0) if sym_info else 0
                    fill_mode = mt5.ORDER_FILLING_IOC
                    if fm & 2:
                        fill_mode = mt5.ORDER_FILLING_IOC
                    elif fm & 1:
                        fill_mode = mt5.ORDER_FILLING_FOK
                    elif fm & 4:
                        fill_mode = mt5.ORDER_FILLING_RETURN

                    # SENTRY 3B: AI EARLY THESIS INVALIDATION CUT (Cut loss early at -0.25R to -0.85R if AI thesis flips!)
                    if r_multiple <= -0.25 and r_multiple >= -0.85:
                        is_thesis_invalidated = False
                        invalidation_reason = ""

                        council_action = str(council_decision.get("master_action", council_decision.get("action", ""))).upper()
                        council_score = int(council_decision.get("quorum_score", council_decision.get("consensus_score", 0)) or 0)
                        council_health = str(council_decision.get("trade_health", "")).upper()
                        council_rec = str(council_decision.get("recommended_management", "")).upper()

                        if pos_type == "BUY" and (council_action == "SELL" and council_score >= 75):
                            is_thesis_invalidated = True
                            invalidation_reason = f"AI Council flipped to SELL ({council_score}% consensus)"
                        elif pos_type == "SELL" and (council_action == "BUY" and council_score >= 75):
                            is_thesis_invalidated = True
                            invalidation_reason = f"AI Council flipped to BUY ({council_score}% consensus)"
                        elif council_health == "INVALIDATED" or council_rec == "EARLY_CUT":
                            is_thesis_invalidated = True
                            invalidation_reason = "AI Active Surveillance marked thesis INVALIDATED"

                        if not is_thesis_invalidated:
                            try:
                                r_m5 = mt5.copy_rates_from_pos(broker_sym, mt5.TIMEFRAME_M5, 0, 25)
                                if r_m5 is not None and len(r_m5) >= 21:
                                    df_m5_close = pd.Series([x['close'] for x in r_m5])
                                    e9 = float(df_m5_close.ewm(span=9, adjust=False).mean().iloc[-1])
                                    e21 = float(df_m5_close.ewm(span=21, adjust=False).mean().iloc[-1])
                                    if pos_type == "BUY" and e9 < (e21 - 0.40) and price_gain <= -3.0:
                                        is_thesis_invalidated = True
                                        invalidation_reason = f"M5 Fast EMA 9/21 Bearish Breakdown ({e9:.2f} < {e21:.2f})"
                                    elif pos_type == "SELL" and e9 > (e21 + 0.40) and price_gain <= -3.0:
                                        is_thesis_invalidated = True
                                        invalidation_reason = f"M5 Fast EMA 9/21 Bullish Breakout ({e9:.2f} > {e21:.2f})"
                            except Exception:
                                pass

                        if is_thesis_invalidated:
                            req_cut = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": ticket,
                                "symbol": broker_sym,
                                "volume": volume,
                                "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                "price": bid if pos_type == "BUY" else ask,
                                "deviation": 25,
                                "magic": profile.magic_number,
                                "comment": f"EarlyCut_{invalidation_reason[:10]}"[:31],
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": fill_mode
                            }
                            res_cut = mt5.order_send(req_cut)
                            if res_cut and res_cut.retcode == mt5.TRADE_RETCODE_DONE:
                                all_actions.append({
                                    "account": profile.name,
                                    "ticket": ticket,
                                    "type": "EARLY_THESIS_INVALIDATION_CUT",
                                    "thought": f"⚡ Sentry 3B (Early Loss Cutter): Cut losing trade early at {r_multiple:.2f}R ({profit:+.2f} {profile.currency}) instead of full -1.0R loss! Reason: {invalidation_reason}. Saved 50%+ risk capital.",
                                    "result": f"Closed position #{ticket} early"
                                })
                                continue

                    # Micro account fast breakeven and profit lock
                    if profile.mode == "MICRO_COMPOUNDING":
                        # Early breakeven
                        if price_gain >= profile.early_be_points and ticket not in profile.breakeven_locked_tickets:
                            new_sl = open_price + 0.10 if pos_type == "BUY" else open_price - 0.10
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": broker_sym,
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
                                    "thought": f"Secured +${profit:.2f} ({price_gain:.2f} pts). SL moved to Breakeven @ {new_sl:.2f} to eliminate risk.",
                                    "result": "SL Moved to Breakeven"
                                })

                        # Quick Scalp Profit Lock
                        if price_gain >= profile.quick_tp_points or profit >= 1.00:
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

                    # Standard Prop Account 7-Sentry Lifecycle Management
                    elif profile.mode == "STANDARD_PROP":
                        initial_r = max(abs(open_price - sl), 5.0) if sl > 0 else 6.50
                        r_multiple = price_gain / initial_r
                        struct_m15 = (market_payload or {}).get("market_structures", {}).get("m15_execution_structure", {})
                        atr_val = float(struct_m15.get("atr_14", 6.50) or 6.50)
                        rsi_val = float(struct_m15.get("rsi_14", 50.0) or 50.0)
                        patterns_list = struct_m15.get("candlestick_patterns", [])

                        # SENTRY 7: 3-TIER DYNAMIC PARTIAL-BOOKING OPTIMIZER
                        # Priority 1: Bank real cash FIRST before moving SL to avoid "+40-60 gain reverses into cost-to-cost"
                        sym_info = mt5.symbol_info(broker_sym)
                        fm = getattr(sym_info, "filling_mode", 0) if sym_info else 0
                        fill_mode = mt5.ORDER_FILLING_IOC
                        if fm & 2:
                            fill_mode = mt5.ORDER_FILLING_IOC
                        elif fm & 1:
                            fill_mode = mt5.ORDER_FILLING_FOK
                        elif fm & 4:
                            fill_mode = mt5.ORDER_FILLING_RETURN

                                                # SENTRY 7: REAL-TIME AI DYNAMIC PROFIT SENTIENT REASONING
                        # Rather than a blind static point target, the AI evaluates live market dynamics in real time:
                        is_gold = any(k in str(broker_sym).upper() for k in ["XAU", "GOLD"])
                        min_gain_for_ai = 4.50 if is_gold else 2.50
                        
                        # 1. Opposing Supply / Demand & Resistance / Support Wall Proximity
                        sd_data = struct_m15.get("supply_demand_zones", {})
                        supply_zones = sd_data.get("fresh_supply_zones", []) or sd_data.get("supply_zones", [])
                        demand_zones = sd_data.get("fresh_demand_zones", []) or sd_data.get("demand_zones", [])
                        
                        eq_data = (market_payload or {}).get("institutional_equilibrium", {}) or {}
                        vah = float(eq_data.get("value_area_high", 0.0) or 0.0)
                        val = float(eq_data.get("value_area_low", 0.0) or 0.0)

                        is_hitting_wall = False
                        wall_desc = ""
                        if pos_type == "BUY":
                            for sz in supply_zones:
                                bot = float(sz.get("bottom", 0.0))
                                if bot > open_price and abs(current_price - bot) <= 1.20:
                                    is_hitting_wall, wall_desc = True, f"Supply Wall @ {bot:.2f}"
                                    break
                            if not is_hitting_wall and vah > open_price and abs(current_price - vah) <= 1.20:
                                is_hitting_wall, wall_desc = True, f"VAH Resistance @ {vah:.2f}"
                        elif pos_type == "SELL":
                            for dz in demand_zones:
                                top = float(dz.get("top", 0.0))
                                if top < open_price and abs(current_price - top) <= 1.20:
                                    is_hitting_wall, wall_desc = True, f"Demand Wall @ {top:.2f}"
                                    break
                            if not is_hitting_wall and val > 0 and val < open_price and abs(current_price - val) <= 1.20:
                                is_hitting_wall, wall_desc = True, f"VAL Support @ {val:.2f}"

                        # 2. Candlestick Reversal Triggers in Real Time
                        candlestick_reversal = False
                        rev_candlestick_name = ""
                        for p in patterns_list:
                            p_name = str(p.get("pattern", "")).upper()
                            p_bias = str(p.get("bias", "")).upper()
                            if pos_type == "BUY" and ("BEARISH" in p_bias or any(k in p_name for k in ["SHOOTING", "EVENING", "TWEEZER TOP", "DARK CLOUD", "BEARISH ENGULFING", "GRAVESTONE"])):
                                candlestick_reversal, rev_candlestick_name = True, p.get("pattern", "Bearish Reversal")
                                break
                            elif pos_type == "SELL" and ("BULLISH" in p_bias or any(k in p_name for k in ["HAMMER", "MORNING", "TWEEZER BOTTOM", "PIERCING", "BULLISH ENGULFING", "DRAGONFLY"])):
                                candlestick_reversal, rev_candlestick_name = True, p.get("pattern", "Bullish Reversal")
                                break

                        # 3. Momentum Impulse Expansion (Marubozu, Three White Soldiers/Black Crows, CVD thrust)
                        is_momentum_surging = False
                        for p in patterns_list:
                            p_name = str(p.get("pattern", "")).upper()
                            if pos_type == "BUY" and any(k in p_name for k in ["MARUBOZU", "WHITE SOLDIERS", "CONVERGENT_BULLISH"]):
                                is_momentum_surging = True
                                break
                            elif pos_type == "SELL" and any(k in p_name for k in ["MARUBOZU", "BLACK CROWS", "CONVERGENT_BEARISH"]):
                                is_momentum_surging = True
                                break

                        # 4. Sentient Decision Logic:
                        # - If price is in profit (>= 4.50 pts) AND hits an opposing Wall -> BANK IMMEDIATELY!
                        # - If price is in profit (>= 4.50 pts) AND prints a Reversal Candlestick -> BANK IMMEDIATELY!
                        # - If momentum is surging and no wall ahead -> HOLD RUNNER, DO NOT CUT! Let profit expand!
                        # - If trade reaches solid institutional target (>= 8.50 pts or >= 1.5R) -> BANK 50% regardless to lock cash!
                        is_tier1_profit = False
                        t1_reason = ""
                        if ticket not in profile.tier1_partial_tickets:
                            if price_gain >= min_gain_for_ai:
                                if is_hitting_wall:
                                    is_tier1_profit = True
                                    t1_reason = f"Hit Opposing {wall_desc} (+{price_gain:.2f} pts)"
                                elif candlestick_reversal:
                                    is_tier1_profit = True
                                    t1_reason = f"Reversal Candlestick ({rev_candlestick_name}) printed (+{price_gain:.2f} pts)"
                                elif price_gain >= (8.50 if is_gold else 5.00) or r_multiple >= 1.50:
                                    is_tier1_profit = True
                                    t1_reason = f"Full Institutional Target Hit (+{price_gain:.2f} pts | {r_multiple:.2f}R)"
                                elif is_momentum_surging:
                                    # Pro-Human AI: Momentum surging, hold runner to maximize gains!
                                    t1_reason = f"Momentum accelerating in favor (+{price_gain:.2f} pts). Holding for larger swing."
                                elif price_gain >= (6.50 if is_gold else 3.50):
                                    is_tier1_profit = True
                                    t1_reason = f"Tier 1 Profit Milestone (+{price_gain:.2f} pts)"

                        if is_tier1_profit and ticket not in profile.tier1_partial_tickets:
                            if volume >= 0.03:
                                # Close 35% of volume to bank real cash
                                t1_vol = round(volume * 0.35, 2)
                                if (volume - t1_vol) < 0.01:
                                    t1_vol = round(volume - 0.01, 2)
                                if t1_vol >= 0.01:
                                    req_t1 = {
                                        "action": mt5.TRADE_ACTION_DEAL,
                                        "position": ticket,
                                        "symbol": broker_sym,
                                        "volume": t1_vol,
                                        "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                        "price": bid if pos_type == "BUY" else ask,
                                        "deviation": 25,
                                        "magic": profile.magic_number,
                                        "comment": "Chanakya_T1_Bank35",
                                        "type_time": mt5.ORDER_TIME_GTC,
                                        "type_filling": fill_mode
                                    }
                                    res_t1 = mt5.order_send(req_t1)
                                    if res_t1 and res_t1.retcode == mt5.TRADE_RETCODE_DONE:
                                        profile.tier1_partial_tickets.add(ticket)
                                        # Protected Breakeven with healthy 1.20 pt buffer above spread
                                        be_sl = round(open_price + 1.20 if pos_type == "BUY" else open_price - 1.20, 2)
                                        req_be = {
                                            "action": mt5.TRADE_ACTION_SLTP,
                                            "position": ticket,
                                            "symbol": broker_sym,
                                            "sl": be_sl,
                                            "tp": round(pos.tp, 2) if pos.tp else 0.0
                                        }
                                        mt5.order_send(req_be)
                                        profile.breakeven_locked_tickets.add(ticket)
                                        rem_vol = round(volume - t1_vol, 2)
                                        all_actions.append({
                                            "account": profile.name,
                                            "ticket": ticket,
                                            "type": "DYNAMIC_PARTIAL_BANKED_35",
                                            "thought": f"AI Real-Time Profit Decision: {t1_reason}. Banked 35% cash ({t1_vol} lots). Remaining {rem_vol} lots secured at Breakeven ({be_sl:.2f}).",
                                            "result": f"Partial closed {t1_vol} lots"
                                        })
                            elif volume == 0.02:
                                # For 0.02 lots, close 0.01 lot (50%) at Tier 1
                                req_t1 = {
                                    "action": mt5.TRADE_ACTION_DEAL,
                                    "position": ticket,
                                    "symbol": broker_sym,
                                    "volume": 0.01,
                                    "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                    "price": bid if pos_type == "BUY" else ask,
                                    "deviation": 25,
                                    "magic": profile.magic_number,
                                    "comment": "Chanakya_T1_50",
                                    "type_time": mt5.ORDER_TIME_GTC,
                                    "type_filling": fill_mode
                                }
                                res_t1 = mt5.order_send(req_t1)
                                if res_t1 and res_t1.retcode == mt5.TRADE_RETCODE_DONE:
                                    profile.tier1_partial_tickets.add(ticket)
                                    be_sl = round(open_price + 1.20 if pos_type == "BUY" else open_price - 1.20, 2)
                                    req_be = {
                                        "action": mt5.TRADE_ACTION_SLTP,
                                        "position": ticket,
                                        "symbol": broker_sym,
                                        "sl": be_sl,
                                        "tp": round(pos.tp, 2) if pos.tp else 0.0
                                    }
                                    mt5.order_send(req_be)
                                    profile.breakeven_locked_tickets.add(ticket)
                                    all_actions.append({
                                        "account": profile.name,
                                        "ticket": ticket,
                                        "type": "DYNAMIC_PARTIAL_BANKED_50",
                                        "thought": f"AI Real-Time Profit Decision: {t1_reason}. Banked 50% cash (0.01 lots @ +${profit:.2f}). Runner secured at Breakeven ({be_sl:.2f}) trailing to TP.",
                                        "result": "Partial closed 0.01 lots"
                                    })
                            else:
                                profile.tier1_partial_tickets.add(ticket)
                                locked_profit_pts = max(1.50, round(price_gain * 0.45, 2))
                                profit_sl = round(open_price + locked_profit_pts if pos_type == "BUY" else open_price - locked_profit_pts, 2)
                                req_be = {
                                    "action": mt5.TRADE_ACTION_SLTP,
                                    "position": ticket,
                                    "symbol": broker_sym,
                                    "sl": profit_sl,
                                    "tp": round(pos.tp, 2) if pos.tp else 0.0
                                }
                                res_sl = mt5.order_send(req_be)
                                if res_sl and res_sl.retcode == mt5.TRADE_RETCODE_DONE:
                                    profile.breakeven_locked_tickets.add(ticket)
                                    all_actions.append({
                                        "account": profile.name,
                                        "ticket": ticket,
                                        "type": "SINGLE_MICRO_PROFIT_LOCKED",
                                        "thought": f"AI Real-Time Profit Decision: {t1_reason}. SL advanced to {profit_sl:,.2f} (+{locked_profit_pts:.1f} pts locked). Zero cost-to-cost risk!",
                                        "result": f"SL advanced to {profit_sl:,.2f}"
                                    })


                        # SENTRY 1: FALLBACK BREAKEVEN LOCK
                        if (r_multiple >= 0.85 or price_gain >= max(6.00, atr_val * 0.75)) and ticket not in profile.breakeven_locked_tickets:
                            be_sl = open_price + 0.50 if pos_type == "BUY" else open_price - 0.50
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": ticket,
                                "symbol": broker_sym,
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
                                    "thought": f"🛡️ Sentry 1 (BE Lock): Profit +{r_multiple:.2f}R (+{price_gain:.2f} pts). SL locked at Breakeven ({be_sl:.2f}) with cushion.",
                                    "result": "SL Moved to Breakeven"
                                })

                        # SENTRY 3: MOMENTUM EXHAUSTION & REVERSAL EARLY PROFIT SENTRY
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

                        # If trade is in profit (+0.50R or more) and reversal detected, exit early to bank cash!
                        if r_multiple >= 0.50 and is_exhaustion:
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": ticket,
                                "symbol": broker_sym,
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

                        # TIER 2: CORE TARGET 1 PARTIAL BANK (+1.20R or TP1)
                        is_tp1_reached = False
                        if pos.tp and pos.tp > 0:
                            if pos_type == "BUY" and current_price >= (pos.tp - 0.40):
                                is_tp1_reached = True
                            elif pos_type == "SELL" and current_price <= (pos.tp + 0.40):
                                is_tp1_reached = True

                        if (r_multiple >= 1.20 or (is_tp1_reached and r_multiple >= 0.80)) and ticket not in profile.tier2_partial_tickets:
                            if volume >= 0.02:
                                # Close 50% of remaining volume
                                t2_vol = round(volume * 0.50, 2)
                                if (volume - t2_vol) < 0.01:
                                    t2_vol = round(volume - 0.01, 2)
                                if t2_vol >= 0.01:
                                    req_t2 = {
                                        "action": mt5.TRADE_ACTION_DEAL,
                                        "position": ticket,
                                        "symbol": broker_sym,
                                        "volume": t2_vol,
                                        "type": mt5.ORDER_TYPE_SELL if pos_type == "BUY" else mt5.ORDER_TYPE_BUY,
                                        "price": bid if pos_type == "BUY" else ask,
                                        "deviation": 25,
                                        "magic": profile.magic_number,
                                        "comment": "Chanakya_T2_Core",
                                        "type_time": mt5.ORDER_TIME_GTC,
                                        "type_filling": fill_mode
                                    }
                                    res_t2 = mt5.order_send(req_t2)
                                    if res_t2 and res_t2.retcode == mt5.TRADE_RETCODE_DONE:
                                        profile.tier2_partial_tickets.add(ticket)
                                        profile.partially_closed_tickets.add(ticket)
                                        # Advance SL to lock +0.50R profit on runner!
                                        profit_sl = round(open_price + (initial_r * 0.50) if pos_type == "BUY" else open_price - (initial_r * 0.50), 2)
                                        req_sl = {
                                            "action": mt5.TRADE_ACTION_SLTP,
                                            "position": ticket,
                                            "symbol": broker_sym,
                                            "sl": profit_sl,
                                            "tp": round(pos.tp, 2) if pos.tp else 0.0
                                        }
                                        mt5.order_send(req_sl)
                                        rem_vol = round(volume - t2_vol, 2)
                                        all_actions.append({
                                            "account": profile.name,
                                            "ticket": ticket,
                                            "type": "PROP_TIER2_CORE_TP1",
                                            "thought": f"🎯 Sentry 7 Tier 2 (TP1 Core @ +{r_multiple:.2f}R): Banked {t2_vol} lots. Runner {rem_vol} lots locked with +0.50R profit @ {profit_sl:,.2f} trailing to TP2.",
                                            "result": f"Partial closed {t2_vol} lots"
                                        })
                            else:
                                # Micro Account: Advance SL to lock +0.60R profit
                                if ticket not in profile.tier2_partial_tickets:
                                    profile.tier2_partial_tickets.add(ticket)
                                    profit_sl = round(open_price + (initial_r * 0.60) if pos_type == "BUY" else open_price - (initial_r * 0.60), 2)
                                    req_sl = {
                                        "action": mt5.TRADE_ACTION_SLTP,
                                        "position": ticket,
                                        "symbol": broker_sym,
                                        "sl": profit_sl,
                                        "tp": round(pos.tp, 2) if pos.tp else 0.0
                                    }
                                    mt5.order_send(req_sl)
                                    all_actions.append({
                                        "account": profile.name,
                                        "ticket": ticket,
                                        "type": "MICRO_PROFIT_LOCK_60",
                                        "thought": f"🛡️ Sentry 7 Micro Armor (+1.20R / TP1): SL advanced to {profit_sl:,.2f} (+0.60R locked). Runner protected.",
                                        "result": f"SL Ratcheted to {profit_sl}"
                                    })

                        # SENTRY 2: HUMAN PRO DYNAMIC RATCHET TRAILING STOP
                        # Trails tightly behind M5 swing structure (2.20 to 3.20 pt gap) + milestone profit locks
                        if r_multiple >= 0.80:
                            is_gold = any(k in str(broker_sym).upper() for k in ["XAU", "GOLD"])
                            is_btc = any(k in str(broker_sym).upper() for k in ["BTC", "BITCOIN"])
                            trail_gap = 250.0 if is_btc else (min(4.50, max(3.20, atr_val * 0.50)) if is_gold else 0.0035)

                            m5_low = 0.0
                            m5_high = 0.0
                            try:
                                r_m5 = mt5.copy_rates_from_pos(broker_sym, mt5.TIMEFRAME_M5, 0, 3)
                                if r_m5 is not None and len(r_m5) >= 2:
                                    m5_low = float(r_m5[-2]['low'])
                                    m5_high = float(r_m5[-2]['high'])
                            except Exception:
                                pass

                            target_sl = None
                            if pos_type == "BUY":
                                c1 = current_price - trail_gap
                                c2 = (m5_low - 0.35) if (m5_low > (open_price + 0.50)) else 0.0
                                c3 = 0.0
                                if r_multiple >= 1.60:
                                    c3 = open_price + (initial_r * 1.10)
                                elif r_multiple >= 1.30:
                                    c3 = open_price + (initial_r * 0.70)
                                elif r_multiple >= 1.00:
                                    c3 = open_price + (initial_r * 0.35)

                                calc_sl = round(max(c1, c2, c3), 2)
                                if calc_sl > (sl + 0.30) and calc_sl > (open_price + 0.30):
                                    target_sl = calc_sl

                            elif pos_type == "SELL":
                                c1 = current_price + trail_gap
                                c2 = (m5_high + 0.35) if (m5_high > 0 and m5_high < (open_price - 0.50)) else 999999.0
                                c3 = 999999.0
                                if r_multiple >= 1.60:
                                    c3 = open_price - (initial_r * 1.10)
                                elif r_multiple >= 1.30:
                                    c3 = open_price - (initial_r * 0.70)
                                elif r_multiple >= 1.00:
                                    c3 = open_price - (initial_r * 0.35)

                                calc_sl = round(min(c1, c2, c3), 2)
                                if (sl <= 0 or calc_sl < (sl - 0.30)) and calc_sl < (open_price - 0.30):
                                    target_sl = calc_sl

                            if target_sl is not None:
                                req_trail = {
                                    "action": mt5.TRADE_ACTION_SLTP,
                                    "position": ticket,
                                    "symbol": broker_sym,
                                    "sl": target_sl,
                                    "tp": round(pos.tp, 2) if pos.tp else 0.0
                                }
                                res_trail = mt5.order_send(req_trail)
                                if res_trail and res_trail.retcode == mt5.TRADE_RETCODE_DONE:
                                    pts_locked = abs(target_sl - open_price)
                                    gap_dist = abs(current_price - target_sl)
                                    all_actions.append({
                                        "account": profile.name,
                                        "ticket": ticket,
                                        "type": "HUMAN_PRO_DYNAMIC_TRAIL",
                                        "thought": f"📈 Sentry 2 (Human Pro Trail): SL ratcheted to {target_sl:,.2f} (Trailing Gap: {gap_dist:.2f} pts | Accrued profit locked: +{pts_locked:.2f} pts). Never gives back gains!",
                                        "result": f"SL Ratcheted to {target_sl}"
                                    })

            finally:
                profile.shutdown()

        return all_actions

    def resolve_broker_symbol(self, base_symbol: str) -> str:
        """Resolves the active broker's exact symbol name variant (e.g. XAUUSD, XAUUSD+, XAUUSDm)."""
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
                    return bid >= 10000.0
                if is_gold:
                    return bid >= 1000.0
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
                if is_gold and ("XAU" in s_upper or "GOLD" in s_upper):
                    if _is_valid(s_name):
                        return s_name
                elif is_btc and ("BTC" in s_upper or "BITCOIN" in s_upper):
                    if _is_valid(s_name):
                        return s_name

        return base_symbol

    def count_open_positions(self, base_symbol: str) -> int:
        """Returns total AI open positions across all connected active accounts for base_symbol."""
        total = 0
        for profile in self.accounts:
            if not profile.is_active:
                continue
            if not profile.connect():
                continue
            try:
                broker_sym = self.resolve_broker_symbol(base_symbol)
                positions = mt5.positions_get(symbol=broker_sym)
                ai_positions = [
                    p for p in (positions or [])
                    if (p.magic == profile.magic_number) or (p.comment and (str(p.comment).upper().startswith("AI_") or "CHANAKYA" in str(p.comment).upper()))
                ]
                total += len(ai_positions)
            finally:
                profile.shutdown()
        return total

    def execute_dual_sniper_signal(
        self,
        action: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        consensus_score: int,
        sniper_state: Dict[str, Any],
        take_profit_2: float = 0.0
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

                # 3b. Anti-Cluster Guard: Prevent opening duplicate or clustered positions near each other
                is_gold = any(k in str(broker_sym).upper() for k in ["XAU", "GOLD"])
                is_btc = any(k in str(broker_sym).upper() for k in ["BTC", "BITCOIN"])
                min_spacing = 250.0 if is_btc else (5.0 if is_gold else 0.0035)

                clashing_position = None
                for p in ai_positions:
                    dist = abs(order_price - float(p.price_open))
                    if dist < min_spacing:
                        clashing_position = (p, dist)
                        break

                if clashing_position:
                    cp, cdist = clashing_position
                    print(f"   🛡️ [{profile.name}] Anti-Cluster Guard: Proposed entry ${order_price:,.2f} is within {cdist:.2f} pts of existing Position #{cp.ticket} (Open: ${cp.price_open:,.2f} | Min spacing: {min_spacing:.2f} pts). Skipping duplicate entry.")
                    continue

                                # 3c. Institutional Anti-Laddering & Post-Trade Reset Guard: Prevent rapid re-entries and chasing tops/bottoms
                try:
                    now_time = datetime.now()
                    recent_deals = mt5.history_deals_get(now_time - timedelta(minutes=25), now_time + timedelta(minutes=1))
                    if recent_deals:
                        ai_magic_numbers = {profile.magic_number, CONFIG.MAGIC_NUMBER, 777888, 777999, 778101, 778110, 778221}
                        recent_ai_deals = [
                            d for d in recent_deals
                            if (d.entry == 1 or d.profit != 0.0)
                            and ((d.magic in ai_magic_numbers) or (d.comment and (str(d.comment).upper().startswith("AI_") or "CHANAKYA" in str(d.comment).upper())))
                        ]
                        if recent_ai_deals:
                            recent_ai_deals.sort(key=lambda x: x.time, reverse=True)
                            last_deal = recent_ai_deals[0]
                            elapsed_since_last_exit = now_ts - float(last_deal.time)
                            last_exit_price = float(last_deal.price)

                            # Guard 1: Minimum Structural Reset Timeout (At least 1 full M5 candle cycle = 240 seconds)
                            # Eliminates the amateur error of re-entering 1-5 seconds after an exit!
                            if elapsed_since_last_exit < 240.0:
                                rem_s = int(240.0 - elapsed_since_last_exit)
                                print(f"   ⏳ [{profile.name}] Post-Trade Cooldown Guard: Last trade closed {int(elapsed_since_last_exit)}s ago. Waiting {rem_s}s for fresh M5 candle structure.")
                                continue

                            # Guard 2: Anti-Ladder Trap Guard (Do NOT buy higher than last exit, or sell lower than last exit!)
                            if is_gold and elapsed_since_last_exit < 900.0:
                                if action == "BUY" and order_price >= (last_exit_price - 2.50):
                                    print(f"   🛡️ [{profile.name}] Anti-Ladder Trap Guard: Proposed BUY @ ${order_price:.2f} is higher or near last exit (${last_exit_price:.2f}). Waiting for a discount pullback of >= 2.5 pts.")
                                    continue
                                elif action == "SELL" and order_price <= (last_exit_price + 2.50):
                                    print(f"   🛡️ [{profile.name}] Anti-Ladder Trap Guard: Proposed SELL @ ${order_price:.2f} is lower or near last exit (${last_exit_price:.2f}). Waiting for a premium pullback of >= 2.5 pts.")
                                    continue

                            # Guard 3: Post-Loss Extended Protection (10-minute cooldown after full SL hit)
                            if last_deal.profit < -0.05 and elapsed_since_last_exit < 600.0:
                                rem_s = int(600.0 - elapsed_since_last_exit)
                                print(f"   🛡️ [{profile.name}] Post-Loss Cooling Guard: Account took a loss ({last_deal.profit:.2f} {profile.currency}) {int(elapsed_since_last_exit)}s ago. Cooling off for {rem_s}s to prevent revenge entries.")
                                continue
                except Exception as e:
                    pass

# 4. Account-Specific Lot Sizing & SL/TP Rules with Admin Caps
                order_comment = "Chanakya_Buy" if action == "BUY" else "Chanakya_Sell"

                if profile.mode == "MICRO_COMPOUNDING":
                    # Micro Account: 0.01 lot capped to admin max_lot_size
                    lots = min(profile.max_lot_size, 0.01)
                    # Respect Council's structural SL instead of ultra-tight noise clamp
                    if stop_loss > 0:
                        final_sl = round(stop_loss, 2)
                    else:
                        fallback_sl = 250.0 if is_btc else (10.0 if is_gold else 0.0040)
                        final_sl = round(order_price - fallback_sl if action == "BUY" else order_price + fallback_sl, 2)

                    if take_profit > 0:
                        final_tp = round(take_profit, 2)
                    else:
                        fallback_tp = 450.0 if is_btc else (18.0 if is_gold else 0.0080)
                        final_tp = round(order_price + fallback_tp if action == "BUY" else order_price - fallback_tp, 2)

                else:
                    # Standard Account: Dynamic sizing clamped to admin max_lot_size
                    lots = profile.risk_manager.calculate_lot_size(
                        account_equity=equity,
                        entry_price=order_price,
                        stop_loss=stop_loss,
                        risk_pct=1.5,
                        confidence_score=consensus_score,
                        max_lot_cap=profile.max_lot_size
                    )
                    lots = max(profile.min_lot_size, min(lots, profile.max_lot_size))
                    final_sl = round(stop_loss, 2) if stop_loss > 0 else 0.0
                    # For volume >= 0.02, set broker TP to TP2 so Sentry 7 can bank 50% at TP1 and the runner can ride to TP2
                    if lots >= 0.02 and take_profit_2 > 0:
                        final_tp = round(take_profit_2, 2)
                    else:
                        final_tp = round(take_profit, 2) if take_profit > 0 else 0.0

                # 5. Submit Order (Market or Pending Limit)
                order_mode = sniper_state.get("order_type", "MARKET_OR_LIMIT") if sniper_state else "MARKET_OR_LIMIT"
                if order_mode == "LIMIT_ONLY":
                    trade_action = mt5.TRADE_ACTION_PENDING
                    req_type = mt5.ORDER_TYPE_BUY_LIMIT if action == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT
                    target_exec_price = round(entry_price, 2)
                    order_comment_eff = f"{order_comment[:26]}_LMT"
                    action_recorded = f"{action}_LIMIT"
                else:
                    trade_action = mt5.TRADE_ACTION_DEAL
                    req_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
                    target_exec_price = order_price
                    order_comment_eff = order_comment[:31]
                    action_recorded = action

                sym_info = mt5.symbol_info(broker_sym)
                fm = getattr(sym_info, "filling_mode", 0) if sym_info else 0
                fill_mode = mt5.ORDER_FILLING_IOC
                if fm & 2:
                    fill_mode = mt5.ORDER_FILLING_IOC
                elif fm & 1:
                    fill_mode = mt5.ORDER_FILLING_FOK
                elif fm & 4:
                    fill_mode = mt5.ORDER_FILLING_RETURN

                request = {
                    "action": trade_action,
                    "symbol": broker_sym,
                    "volume": lots,
                    "type": req_type,
                    "price": target_exec_price,
                    "sl": final_sl,
                    "tp": final_tp,
                    "deviation": 20,
                    "magic": profile.magic_number,
                    "comment": order_comment_eff,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": fill_mode,
                }

                result = mt5.order_send(request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    for alt_fill in [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC]:
                        if alt_fill != fill_mode:
                            request["type_filling"] = alt_fill
                            result = mt5.order_send(request)
                            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                break

                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    ticket = result.order or result.deal
                    profile.last_trade_time = now_ts + 60.0
                    
                    AITradeLedger.record_executed_trade(
                        ticket=ticket,
                        symbol=self.symbol,
                        action=action_recorded,
                        volume=lots,
                        price=target_exec_price,
                        sl=final_sl,
                        tp=final_tp,
                        consensus_score=consensus_score,
                        comment=order_comment_eff
                    )

                    mode_desc = "Pending Limit" if order_mode == "LIMIT_ONLY" else "Market Deal"
                    msg = f"[{mode_desc}] #{ticket} placed ({lots} Lots @ {target_exec_price:.2f}, SL={final_sl}, TP={final_tp})"
                    print(f"   ✅ [{profile.name}] {msg}")
                    execution_results.append({
                        "account_id": profile.account_id,
                        "account_name": profile.name,
                        "ticket": ticket,
                        "success": True,
                        "message": msg,
                        "volume": lots,
                        "price": target_exec_price,
                        "order_mode": order_mode
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

    def cancel_dual_pending_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Cancels all AI pending limit orders across both accounts."""
        sym = symbol or self.symbol
        results = []
        for profile in self.accounts:
            if not profile.connect():
                continue
            try:
                broker_sym = self.resolve_broker_symbol(sym)
                orders = mt5.orders_get(symbol=broker_sym)
                if orders:
                    for ord_obj in orders:
                        if getattr(ord_obj, "magic", 0) == profile.magic_number:
                            req = {
                                "action": mt5.TRADE_ACTION_REMOVE,
                                "order": ord_obj.ticket,
                                "comment": "Chanakya_Cancel"
                            }
                            res = mt5.order_send(req)
                            results.append({
                                "account": profile.name,
                                "ticket": ord_obj.ticket,
                                "success": bool(res and res.retcode == mt5.TRADE_RETCODE_DONE),
                                "retcode": getattr(res, "retcode", None)
                            })
            finally:
                profile.shutdown()
        return results
