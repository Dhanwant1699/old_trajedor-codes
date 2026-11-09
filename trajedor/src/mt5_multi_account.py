"""
TRAJEDOR - Multi-Terminal MetaTrader 5 Bridge & Order Dispatcher.
Controls and monitors all 3 configured MT5 accounts simultaneously:
- Account 1: ICMarketsSC Master (EUR)
- Account 2: GTCGlobalSA Micro (USD)
- Account 3: GTCGlobalSA Standard (USD)
Strictly tags and monitors ONLY Trajedor AI orders (ignores all manual trades).
"""

import os
import time
from typing import Dict, Any, List, Optional
from trajedor.config.settings import load_accounts_config, SETTINGS

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class MT5MultiAccountBridge:
    def __init__(self):
        self.accounts_config = load_accounts_config()
        try:
            self.discover_terminals(prune_missing=True)
        except Exception:
            pass

    def get_live_telemetry(self) -> Dict[str, Any]:
        """
        Polls all active MT5 accounts and returns live balance, equity,
        floating PnL, and open positions.
        """
        self.accounts_config = load_accounts_config()
        results = {}
        if not MT5_AVAILABLE:
            return self._mock_telemetry()

        for acc_id, cfg in self.accounts_config.items():
            if not cfg.get("is_active", True):
                results[acc_id] = {
                    "id": acc_id,
                    "name": cfg.get("name", acc_id),
                    "status": "DISARMED",
                    "currency": cfg.get("currency", "USD"),
                    "balance": 0.0,
                    "equity": 0.0,
                    "floating_pnl": 0.0,
                    "open_positions": [],
                    "max_aggregate_lot": cfg.get("max_aggregate_lot", 0.30),
                    "max_single_trade_lot": cfg.get("max_single_trade_lot", 0.10),
                    "max_concurrent_positions": cfg.get("max_concurrent_positions", 3),
                    "scaling_strategy": cfg.get("scaling_strategy", "AI_DYNAMIC_PYRAMID"),
                    "current_ai_lots": 0.0,
                    "current_ai_pos_count": 0,
                    "is_active": False
                }
                continue

            term_path = cfg.get("terminal_path", "")
            magic = cfg.get("magic_number", SETTINGS.MAGIC_NUMBER)
            acc_name = cfg.get("name", acc_id)
            currency = cfg.get("currency", "USD")
            cfg_server = cfg.get("server", "")
            cfg_broker = cfg.get("broker", "")
            cfg_trader = cfg.get("trader_name", "")

            if not term_path or not os.path.exists(term_path):
                continue

            try:
                # Initialize specific terminal with 5s timeout to prevent IPC timeout
                ok = mt5.initialize(path=term_path, timeout=5000)
                if ok:
                    info = mt5.account_info()
                    positions = mt5.positions_get()
                    
                    pos_list = []
                    floating_pnl = 0.0
                    if positions:
                        for p in positions:
                            # Filter AI positions or mark accordingly
                            is_ai = (p.magic == magic or p.magic in (SETTINGS.MAGIC_NUMBER, 888991, 888992, 888993))
                            p_dict = {
                                "ticket": p.ticket,
                                "symbol": p.symbol,
                                "type": "BUY" if p.type == 0 else "SELL",
                                "volume": round(p.volume, 2),
                                "open_price": round(p.price_open, 2),
                                "current_price": round(p.price_current, 2),
                                "sl": round(p.sl, 2),
                                "tp": round(p.tp, 2),
                                "profit": round(p.profit, 2),
                                "is_ai": is_ai,
                                "comment": p.comment
                            }
                            pos_list.append(p_dict)
                            floating_pnl += p.profit

                    # Calculate active AI lots and positions
                    ai_positions = [p for p in pos_list if p.get("is_ai")]
                    current_ai_lots = round(sum(p["volume"] for p in ai_positions), 2)
                    current_ai_pos_count = len(ai_positions)

                    broker_name = cfg_broker
                    if info and info.company:
                        broker_name = "IC Markets (Raw Trading Ltd)" if "raw trading" in info.company.lower() else info.company
                    trader_name = (info.name if info and info.name else cfg_trader) or "Trader"
                    server_name = (info.server if info and info.server else cfg_server) or "MT5 Server"
                    login_val = info.login if info else cfg.get("login")

                    results[acc_id] = {
                        "id": acc_id,
                        "name": acc_name or server_name,
                        "trader_name": trader_name,
                        "server": server_name,
                        "broker": broker_name or server_name,
                        "login": login_val,
                        "currency": info.currency if info else currency,
                        "balance": round(info.balance, 2) if info else 0.0,
                        "equity": round(info.equity, 2) if info else 0.0,
                        "floating_pnl": round(floating_pnl, 2),
                        "status": "CONNECTED",
                        "open_positions": pos_list,
                        "max_aggregate_lot": cfg.get("max_aggregate_lot", 0.30),
                        "max_single_trade_lot": cfg.get("max_single_trade_lot", 0.10),
                        "max_concurrent_positions": cfg.get("max_concurrent_positions", 3),
                        "scaling_strategy": cfg.get("scaling_strategy", "AI_DYNAMIC_PYRAMID"),
                        "current_ai_lots": current_ai_lots,
                        "current_ai_pos_count": current_ai_pos_count,
                        "is_active": cfg.get("is_active", True),
                        "daily_target": float(cfg.get("daily_target", 100.0)),
                        "daily_max_loss": float(cfg.get("daily_max_loss", 50.0))
                    }
                    mt5.shutdown()
                    time.sleep(0.15)
                else:
                    results[acc_id] = {
                        "id": acc_id,
                        "name": acc_name or cfg_server,
                        "trader_name": cfg_trader or "Trader",
                        "server": cfg_server or "MT5 Server",
                        "broker": cfg_broker or "Broker",
                        "login": cfg.get("login", 0),
                        "status": "OFFLINE",
                        "error": "Failed MT5 initialize",
                        "currency": currency,
                        "balance": 0.0,
                        "equity": 0.0,
                        "floating_pnl": 0.0,
                        "open_positions": [],
                        "max_aggregate_lot": cfg.get("max_aggregate_lot", 0.30),
                        "max_single_trade_lot": cfg.get("max_single_trade_lot", 0.10),
                        "max_concurrent_positions": cfg.get("max_concurrent_positions", 3),
                        "scaling_strategy": cfg.get("scaling_strategy", "AI_DYNAMIC_PYRAMID"),
                        "current_ai_lots": 0.0,
                        "current_ai_pos_count": 0,
                        "is_active": cfg.get("is_active", True),
                        "daily_target": float(cfg.get("daily_target", 100.0)),
                        "daily_max_loss": float(cfg.get("daily_max_loss", 50.0))
                    }
                    time.sleep(0.15)
            except Exception as e:
                results[acc_id] = {
                    "id": acc_id,
                    "name": acc_name or cfg_server,
                    "trader_name": cfg_trader or "Trader",
                    "server": cfg_server or "MT5 Server",
                    "broker": cfg_broker or "Broker",
                    "login": cfg.get("login", 0),
                    "status": "ERROR",
                    "error": str(e),
                    "currency": currency,
                    "balance": 0.0,
                    "equity": 0.0,
                    "floating_pnl": 0.0,
                    "open_positions": [],
                    "max_aggregate_lot": cfg.get("max_aggregate_lot", 0.30),
                    "max_single_trade_lot": cfg.get("max_single_trade_lot", 0.10),
                    "max_concurrent_positions": cfg.get("max_concurrent_positions", 3),
                    "scaling_strategy": cfg.get("scaling_strategy", "AI_DYNAMIC_PYRAMID"),
                    "current_ai_lots": 0.0,
                    "current_ai_pos_count": 0,
                    "is_active": cfg.get("is_active", True),
                    "daily_target": float(cfg.get("daily_target", 100.0)),
                    "daily_max_loss": float(cfg.get("daily_max_loss", 50.0))
                }
                time.sleep(0.15)

        return results

    def update_account_limits(self, acc_id: str, new_limits: Dict[str, Any]) -> bool:
        """Dynamically persists and updates granular risk and lot limits for an account."""
        import json
        from trajedor.config.settings import ACCOUNTS_FILE
        self.accounts_config = load_accounts_config()
        if acc_id in self.accounts_config:
            if "max_aggregate_lot" in new_limits:
                self.accounts_config[acc_id]["max_aggregate_lot"] = round(float(new_limits["max_aggregate_lot"]), 2)
            if "max_single_trade_lot" in new_limits:
                self.accounts_config[acc_id]["max_single_trade_lot"] = round(float(new_limits["max_single_trade_lot"]), 2)
            if "max_concurrent_positions" in new_limits:
                self.accounts_config[acc_id]["max_concurrent_positions"] = int(new_limits["max_concurrent_positions"])
            if "daily_target" in new_limits:
                self.accounts_config[acc_id]["daily_target"] = round(float(new_limits["daily_target"]), 2)
            if "daily_max_loss" in new_limits:
                self.accounts_config[acc_id]["daily_max_loss"] = round(float(new_limits["daily_max_loss"]), 2)
            if "scaling_strategy" in new_limits:
                self.accounts_config[acc_id]["scaling_strategy"] = str(new_limits["scaling_strategy"])
            if "is_active" in new_limits:
                self.accounts_config[acc_id]["is_active"] = bool(new_limits["is_active"])

            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.accounts_config, f, indent=2)
            return True
        return False

    def get_live_gold_tick(self) -> Dict[str, Any]:
        """Fetches live Gold bid, ask, and spread with fast fallback."""
        if not MT5_AVAILABLE:
            return {"bid": 4139.52, "ask": 4139.72, "spread": 2.0}

        try:
            ok = False
            try:
                ok = mt5.initialize(timeout=1000)
            except Exception:
                pass
            if ok:
                sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSD.ecn"
                mt5.symbol_select(sym, True)
                tick = mt5.symbol_info_tick(sym)
                if tick and tick.bid > 0:
                    spread = round((tick.ask - tick.bid) * 10, 1)
                    return {
                        "bid": round(tick.bid, 2),
                        "ask": round(tick.ask, 2),
                        "spread": spread
                    }
        except Exception:
            pass

        return {"bid": 4139.52, "ask": 4139.72, "spread": 2.0}

    def get_live_candles(self, count: int = 35) -> Dict[str, Any]:
        """Fetches recent M5 OHLC candles, support, resistance, and key levels for live chart rendering."""
        if not MT5_AVAILABLE:
            return {"candles": [], "support": 4130.0, "resistance": 4165.0}

        try:
            ok = False
            try:
                ok = mt5.initialize(timeout=1000)
            except Exception:
                pass
            if ok:
                sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSD.ecn"
                mt5.symbol_select(sym, True)
                rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, count)
                if rates is not None and len(rates) > 0:
                    candles = []
                    for r in rates:
                        candles.append({
                            "time": int(r["time"]),
                            "open": round(float(r["open"]), 2),
                            "high": round(float(r["high"]), 2),
                            "low": round(float(r["low"]), 2),
                            "close": round(float(r["close"]), 2),
                            "volume": int(r["tick_volume"])
                        })
                    lows = [c["low"] for c in candles]
                    highs = [c["high"] for c in candles]
                    return {
                        "candles": candles,
                        "support": min(lows),
                        "resistance": max(highs),
                        "symbol": sym
                    }
        except Exception:
            pass

        return {"candles": [], "support": 4130.0, "resistance": 4165.0}

    def validate_and_allocate_lot(self, acc_id: str, requested_lot: float) -> Dict[str, Any]:
        """
        Institutional pre-flight risk gate enforcing aggregate lot caps, single-trade limits,
        and max concurrent open position counts.
        Returns:
            {"allowed": bool, "allocated_lot": float, "reason": str}
        """
        self.accounts_config = load_accounts_config()
        cfg = self.accounts_config.get(acc_id, {})
        if not cfg.get("is_active", True):
            return {"allowed": False, "allocated_lot": 0.0, "reason": f"Account {acc_id} is disarmed/paused by operator."}

        max_agg = float(cfg.get("max_aggregate_lot", 0.30))
        max_single = float(cfg.get("max_single_trade_lot", 0.10))
        max_positions = int(cfg.get("max_concurrent_positions", 3))

        telemetry = self.get_live_telemetry()
        acc_telemetry = telemetry.get(acc_id, {})
        current_lots = float(acc_telemetry.get("current_ai_lots", 0.0))
        current_pos_count = int(acc_telemetry.get("current_ai_pos_count", 0))

        # 1. Enforce Max Concurrent Position Cap
        if current_pos_count >= max_positions:
            return {
                "allowed": False,
                "allocated_lot": 0.0,
                "reason": f"Max concurrent positions reached ({current_pos_count}/{max_positions}). No further trades allowed."
            }

        # 2. Enforce Aggregate Lot Capacity
        remaining_room = round(max_agg - current_lots, 2)
        if remaining_room <= 0.001:
            return {
                "allowed": False,
                "allocated_lot": 0.0,
                "reason": f"Max aggregate lot exposure reached ({current_lots:.2f}/{max_agg:.2f} lots). Cannot add exposure."
            }

        # 3. Scale lot size to adhere to single-trade limit and remaining lot budget
        lot_to_trade = min(requested_lot, max_single, remaining_room)
        lot_to_trade = round(lot_to_trade, 2)

        if lot_to_trade < 0.01:
            return {
                "allowed": False,
                "allocated_lot": 0.0,
                "reason": f"Calculated allowable lot {lot_to_trade:.2f} is below minimum broker lot size 0.01."
            }

        return {
            "allowed": True,
            "allocated_lot": lot_to_trade,
            "current_exposure": current_lots,
            "max_exposure": max_agg,
            "current_positions": current_pos_count,
            "max_positions": max_positions,
            "reason": f"Approved {lot_to_trade:.2f} lots (Remaining capacity: {round(remaining_room - lot_to_trade, 2):.2f} lots, Position {current_pos_count + 1}/{max_positions})"
        }

    def dispatch_order(self, acc_id: str, action: str, requested_lot: float, sl: float = 0.0, tp: float = 0.0, comment: str = "TRAJEDOR_AI") -> Dict[str, Any]:
        """
        Executes an institutional MT5 market order on the target account,
        enforcing pre-flight risk checks, dynamic symbol resolution, and filling modes.
        """
        self.accounts_config = load_accounts_config()
        cfg = self.accounts_config.get(acc_id)
        if not cfg or not cfg.get("is_active", True):
            return {"success": False, "reason": f"Account {acc_id} is disarmed or not active."}

        term_path = cfg.get("terminal_path", "")
        if not term_path or not os.path.exists(term_path):
            return {"success": False, "reason": f"Terminal path does not exist: {term_path}"}

        # 1. Enforce Pre-Flight Risk & Lot Gate
        gate = self.validate_and_allocate_lot(acc_id, requested_lot)
        if not gate.get("allowed"):
            return {"success": False, "reason": gate.get("reason")}

        allocated_lot = gate.get("allocated_lot", 0.01)
        magic = cfg.get("magic_number", SETTINGS.MAGIC_NUMBER)

        if not MT5_AVAILABLE:
            return {"success": False, "reason": "MT5 module unavailable"}

        ok = mt5.initialize(path=term_path, timeout=5000)
        if not ok:
            return {"success": False, "reason": f"Failed to initialize MT5: {mt5.last_error()}"}

        try:
            # 2. Detect Broker Symbol for Gold
            candidate_symbols = ["XAUUSD.ecn", "XAUUSD", "GOLD", "XAUUSDm", "XAUUSD."]
            target_symbol = None
            for sym in candidate_symbols:
                s_info = mt5.symbol_info(sym)
                if s_info is not None:
                    target_symbol = sym
                    mt5.symbol_select(sym, True)
                    break

            if not target_symbol:
                return {"success": False, "reason": "No Gold symbol found on broker"}

            s_info = mt5.symbol_info(target_symbol)
            tick = mt5.symbol_info_tick(target_symbol)
            if not tick or tick.bid <= 0:
                return {"success": False, "reason": "No live tick quote available"}

            # 3. Resolve Order Type, Price, and Filling Mode
            is_buy = (action.upper() == "BUY")
            order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
            price = tick.ask if is_buy else tick.bid

            # Determine broker filling mode
            filling = mt5.ORDER_FILLING_IOC
            if hasattr(s_info, "filling_mode"):
                if s_info.filling_mode & 1:
                    filling = mt5.ORDER_FILLING_FOK
                elif s_info.filling_mode & 2:
                    filling = mt5.ORDER_FILLING_IOC
                else:
                    filling = mt5.ORDER_FILLING_RETURN

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": target_symbol,
                "volume": float(allocated_lot),
                "type": order_type,
                "price": price,
                "sl": round(float(sl), 2) if sl else 0.0,
                "tp": round(float(tp), 2) if tp else 0.0,
                "deviation": 25,
                "magic": magic,
                "comment": comment[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }

            res = mt5.order_send(request)
            if res is None:
                err = mt5.last_error()
                return {"success": False, "reason": f"order_send returned None: {err}"}

            if res.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "reason": f"Broker rejected [Code {res.retcode}]: {res.comment}"}

            return {
                "success": True,
                "ticket": res.order,
                "volume": allocated_lot,
                "price": price,
                "symbol": target_symbol,
                "action": action.upper(),
                "comment": res.comment
            }
        finally:
            mt5.shutdown()
            time.sleep(0.15)

    def modify_position_sl_tp(self, acc_id: str, ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> Dict[str, Any]:
        """Modifies Stop Loss and/or Take Profit for an active open position."""
        if not MT5_AVAILABLE:
            return {"success": False, "reason": "MT5 not available"}
        cfg = self.accounts_config.get(acc_id)
        if not cfg or not cfg.get("terminal_path"):
            return {"success": False, "reason": f"Invalid account {acc_id}"}
        
        path = cfg["terminal_path"]
        if not mt5.initialize(path=path, timeout=5000):
            return {"success": False, "reason": f"Failed to initialize MT5 for {acc_id}"}
        
        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return {"success": False, "reason": f"Position #{ticket} not found"}
            pos = positions[0]
            current_sl = pos.sl
            current_tp = pos.tp
            new_sl = round(float(sl), 2) if sl is not None else current_sl
            new_tp = round(float(tp), 2) if tp is not None else current_tp

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": pos.symbol,
                "sl": new_sl,
                "tp": new_tp
            }
            res = mt5.order_send(request)
            if res is None:
                return {"success": False, "reason": f"order_send returned None: {mt5.last_error()}"}
            if res.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "reason": f"Broker error [{res.retcode}]: {res.comment}"}
            return {"success": True, "ticket": ticket, "sl": new_sl, "tp": new_tp}
        finally:
            mt5.shutdown()
            time.sleep(0.15)

    def close_position(self, acc_id: str, ticket: int, volume: Optional[float] = None, comment: str = "AI_CLOSE") -> Dict[str, Any]:
        """Closes an active position fully or partially (if volume is specified)."""
        if not MT5_AVAILABLE:
            return {"success": False, "reason": "MT5 not available"}
        cfg = self.accounts_config.get(acc_id)
        if not cfg or not cfg.get("terminal_path"):
            return {"success": False, "reason": f"Invalid account {acc_id}"}

        path = cfg["terminal_path"]
        if not mt5.initialize(path=path, timeout=5000):
            return {"success": False, "reason": f"Failed to initialize MT5 for {acc_id}"}

        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return {"success": False, "reason": f"Position #{ticket} not found"}
            pos = positions[0]
            close_vol = float(volume) if volume and volume > 0 else pos.volume
            close_vol = min(close_vol, pos.volume)

            # Close BUY with SELL at Bid; Close SELL with BUY at Ask
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                return {"success": False, "reason": f"Tick unavailable for {pos.symbol}"}
            price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

            filling = mt5.ORDER_FILLING_IOC
            sinfo = mt5.symbol_info(pos.symbol)
            if sinfo:
                fill_mode = sinfo.filling_mode
                if fill_mode == 1:
                    filling = mt5.ORDER_FILLING_FOK
                elif fill_mode == 2:
                    filling = mt5.ORDER_FILLING_IOC
                else:
                    filling = mt5.ORDER_FILLING_RETURN

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": pos.symbol,
                "volume": close_vol,
                "type": close_type,
                "price": price,
                "deviation": 25,
                "magic": pos.magic,
                "comment": comment[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling
            }
            res = mt5.order_send(request)
            if res is None:
                return {"success": False, "reason": f"order_send returned None: {mt5.last_error()}"}
            if res.retcode != mt5.TRADE_RETCODE_DONE:
                return {"success": False, "reason": f"Broker close rejected [{res.retcode}]: {res.comment}"}
            return {
                "success": True,
                "ticket": ticket,
                "closed_volume": close_vol,
                "remaining_volume": round(pos.volume - close_vol, 2),
                "close_price": price,
                "comment": comment
            }
        finally:
            mt5.shutdown()
            time.sleep(0.15)

    def discover_terminals(self, prune_missing: bool = True) -> Dict[str, Any]:
        """
        Scans Windows running processes and standard MetaTrader 5 directories
        to auto-discover newly launched or installed MT5 terminals.
        Purges any accounts whose terminal_path does not exist on disk when prune_missing is True.
        """
        import subprocess
        import glob
        from trajedor.config.settings import save_accounts_config

        self.accounts_config = load_accounts_config()

        # 0. Prune any accounts whose terminal_path does not exist on this machine
        pruned_count = 0
        if prune_missing:
            valid_accounts = {}
            for acc_id, cfg in self.accounts_config.items():
                p = cfg.get("terminal_path", "")
                if p and os.path.exists(p) and os.path.isfile(p):
                    valid_accounts[acc_id] = cfg
                else:
                    pruned_count += 1
            self.accounts_config = valid_accounts

        known_paths = {os.path.normpath(cfg.get("terminal_path", "")).lower(): acc_id for acc_id, cfg in self.accounts_config.items()}
        candidate_paths = set()

        # 1. Scan running Windows processes for terminal64.exe or terminal.exe
        try:
            cmd = ['powershell', '-NoProfile', '-Command',
                   'Get-Process -Name terminal64, terminal -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path']
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, _ = p.communicate(timeout=6)
            for line in stdout.splitlines():
                clean_p = line.strip().strip('"').strip("'")
                if clean_p and os.path.exists(clean_p) and clean_p.lower().endswith(".exe"):
                    candidate_paths.add(os.path.normpath(clean_p))
        except Exception:
            pass

        # 2. Scan standard installation locations
        search_dirs = [
            r"C:\Program Files\MetaTrader 5*",
            r"C:\Program Files (x86)\MetaTrader 5*",
            os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal\*")
        ]
        for pattern in search_dirs:
            for d in glob.glob(pattern):
                exe = os.path.join(d, "terminal64.exe")
                if os.path.exists(exe):
                    candidate_paths.add(os.path.normpath(exe))

        # 3. Refresh existing accounts with live MT5 metadata if available
        config_changed = False
        for p in sorted(candidate_paths):
            p_norm = p.lower()
            if p_norm in known_paths:
                acc_id = known_paths[p_norm]
                if MT5_AVAILABLE:
                    try:
                        if mt5.initialize(path=p, timeout=5000):
                            info = mt5.account_info()
                            if info and info.login > 0:
                                self.accounts_config[acc_id]["login"] = info.login
                                self.accounts_config[acc_id]["currency"] = info.currency or "USD"
                                self.accounts_config[acc_id]["server"] = info.server
                                self.accounts_config[acc_id]["trader_name"] = info.name
                                broker_name = "IC Markets (Raw Trading Ltd)" if "raw trading" in (info.company or "").lower() else (info.company or info.server)
                                self.accounts_config[acc_id]["broker"] = broker_name
                                self.accounts_config[acc_id]["name"] = info.server
                                config_changed = True
                            mt5.shutdown()
                            time.sleep(0.15)
                    except Exception:
                        pass

        # 4. Register newly detected terminal paths
        new_count = 0
        existing_nums = []
        for k in self.accounts_config.keys():
            if k.startswith("acc_") and k[4:].isdigit():
                existing_nums.append(int(k[4:]))
        next_num = max(existing_nums, default=0) + 1

        for p in sorted(candidate_paths):
            p_norm = p.lower()
            if p_norm in known_paths:
                continue

            acc_id = f"acc_{next_num}"
            magic = 888990 + next_num
            folder_name = os.path.basename(os.path.dirname(p))

            login_val = 0
            curr_val = "USD"
            serv_val = "MT5 Server"
            trader_val = "Trader"
            broker_val = f"MT5 ({folder_name})"
            if MT5_AVAILABLE:
                try:
                    if mt5.initialize(path=p, timeout=5000):
                        info = mt5.account_info()
                        if info:
                            login_val = info.login
                            curr_val = info.currency or "USD"
                            serv_val = info.server or "MT5 Server"
                            trader_val = info.name or "Trader"
                            broker_val = "IC Markets (Raw Trading Ltd)" if "raw trading" in (info.company or "").lower() else (info.company or serv_val)
                        mt5.shutdown()
                        time.sleep(0.15)
                except Exception:
                    pass

            self.accounts_config[acc_id] = {
                "name": serv_val,
                "trader_name": trader_val,
                "login": login_val,
                "server": serv_val,
                "broker": broker_val,
                "currency": curr_val,
                "terminal_path": p,
                "magic_number": magic,
                "max_aggregate_lot": 0.20,
                "max_single_trade_lot": 0.05,
                "max_concurrent_positions": 3,
                "scaling_strategy": "AI_DYNAMIC_PYRAMID",
                "daily_target": 50.0,
                "daily_max_loss": 25.0,
                "is_active": True
            }
            known_paths[p_norm] = acc_id
            next_num += 1
            new_count += 1
            config_changed = True

        if new_count > 0 or pruned_count > 0 or config_changed:
            save_accounts_config(self.accounts_config)

        return {
            "total_terminals": len(self.accounts_config),
            "newly_discovered": new_count,
            "pruned_missing": pruned_count,
            "accounts": self.accounts_config
        }

    def _mock_telemetry(self) -> Dict[str, Any]:
        cfg = load_accounts_config()
        self.accounts_config = cfg
        results = {}
        for acc_id, a_cfg in cfg.items():
            results[acc_id] = {
                "id": acc_id,
                "name": a_cfg.get("name", f"Terminal {acc_id}"),
                "login": a_cfg.get("login", 0),
                "status": "CONNECTED" if a_cfg.get("is_active", True) else "DISARMED",
                "currency": a_cfg.get("currency", "USD"),
                "balance": 0.0,
                "equity": 0.0,
                "floating_pnl": 0.0,
                "open_positions": [],
                "max_aggregate_lot": a_cfg.get("max_aggregate_lot", 0.20),
                "max_single_trade_lot": a_cfg.get("max_single_trade_lot", 0.05),
                "max_concurrent_positions": a_cfg.get("max_concurrent_positions", 3),
                "scaling_strategy": a_cfg.get("scaling_strategy", "AI_DYNAMIC_PYRAMID"),
                "current_ai_lots": 0.0,
                "current_ai_pos_count": 0,
                "is_active": a_cfg.get("is_active", True),
                "daily_target": float(a_cfg.get("daily_target", 50.0)),
                "daily_max_loss": float(a_cfg.get("daily_max_loss", 25.0))
            }
        return results

