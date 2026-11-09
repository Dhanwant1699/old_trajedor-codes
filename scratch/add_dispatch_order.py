path = r"trajedor/src/mt5_multi_account.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

target = """    def discover_terminals(self, prune_missing: bool = True) -> Dict[str, Any]:"""

dispatch_code = '''    def dispatch_order(self, acc_id: str, action: str, requested_lot: float, sl: float = 0.0, tp: float = 0.0, comment: str = "TRAJEDOR_AI") -> Dict[str, Any]:
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

    def discover_terminals(self, prune_missing: bool = True) -> Dict[str, Any]:'''

assert target in c, "target not found"
c = c.replace(target, dispatch_code, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("SUCCESSFULLY_ADDED_DISPATCH_ORDER")
