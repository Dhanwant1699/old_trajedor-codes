import os

path = r"trajedor/src/mt5_multi_account.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

target = """            login_val = 0
            curr_val = "USD"
            comp_name = f"MT5 ({folder_name})"
            if MT5_AVAILABLE:
                try:
                    if mt5.initialize(path=p, timeout=1000):
                        info = mt5.account_info()
                        if info:
                            login_val = info.login
                            curr_val = info.currency or "USD"
                            comp_name = f"{info.company} ({curr_val})"
                        mt5.shutdown()
                except Exception:
                    pass

            self.accounts_config[acc_id] = {
                "name": comp_name,
                "login": login_val,
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

        if new_count > 0 or pruned_count > 0:
            save_accounts_config(self.accounts_config)"""

repl = """            login_val = 0
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
            save_accounts_config(self.accounts_config)"""

if target in c:
    c = c.replace(target, repl, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("SUCCESSFULLY_UPDATED")
else:
    print("TARGET_NOT_FOUND")
