import os
import sys
import time
import json

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 python module not installed")
    sys.exit(1)

sys.path.insert(0, os.path.abspath("."))
from trajedor.config.settings import load_accounts_config, SETTINGS

def check_terminal_readiness(acc_id, cfg):
    path = cfg.get("terminal_path", "")
    server = cfg.get("server", "N/A")
    login = cfg.get("login", 0)
    magic = cfg.get("magic_number", SETTINGS.MAGIC_NUMBER)
    max_agg = cfg.get("max_aggregate_lot", 0.1)
    max_single = cfg.get("max_single_trade_lot", 0.05)
    max_pos = cfg.get("max_concurrent_positions", 3)
    is_armed = cfg.get("is_active", True)

    print(f"\n=======================================================")
    print(f"DIAGNOSTIC REPORT FOR: {acc_id} ({server} | Login #{login})")
    print(f"=======================================================")
    
    if not os.path.exists(path):
        print(f"[ERROR] Terminal executable path does not exist: {path}")
        return

    ok = mt5.initialize(path=path, timeout=5000)
    if not ok:
        err = mt5.last_error()
        print(f"[ERROR] Failed to initialize MT5 at {path}: {err}")
        return

    try:
        t_info = mt5.terminal_info()
        a_info = mt5.account_info()

        # 1. Connection & Account Status
        print(f"1. TERMINAL & ACCOUNT STATUS:")
        print(f"   - Terminal Connected: {t_info.connected if t_info else 'N/A'}")
        print(f"   - Terminal Algo Trading Enabled (Button): {t_info.trade_allowed if t_info else 'N/A'}")
        print(f"   - Account Trade Allowed: {a_info.trade_allowed if a_info else 'N/A'}")
        print(f"   - Account EA/Algo Trading Allowed: {a_info.trade_expert if a_info else 'N/A'}")
        print(f"   - Balance: ${a_info.balance:.2f} | Equity: ${a_info.equity:.2f} | Free Margin: ${a_info.margin_free:.2f}")
        print(f"   - Margin Level: {a_info.margin_level:.2f}%" if a_info.margin_level else "   - Margin Level: N/A")

        # 2. Symbol & Live Market Quote
        candidate_symbols = ["XAUUSD", "XAUUSD.ecn", "GOLD", "XAUUSDm", "XAUUSD."]
        target_symbol = None
        for sym in candidate_symbols:
            s_info = mt5.symbol_info(sym)
            if s_info is not None:
                target_symbol = sym
                mt5.symbol_select(sym, True)
                break

        print(f"\n2. LIVE MARKET (GOLD / XAUUSD) STATUS:")
        if not target_symbol:
            print("   [CRITICAL] No Gold symbol found on broker watchlist!")
            return

        s_info = mt5.symbol_info(target_symbol)
        tick = mt5.symbol_info_tick(target_symbol)
        
        trade_mode_str = {
            mt5.SYMBOL_TRADE_MODE_DISABLED: "DISABLED (MARKET CLOSED)",
            mt5.SYMBOL_TRADE_MODE_LONGONLY: "LONG ONLY",
            mt5.SYMBOL_TRADE_MODE_SHORTONLY: "SHORT ONLY",
            mt5.SYMBOL_TRADE_MODE_CLOSEONLY: "CLOSE ONLY",
            mt5.SYMBOL_TRADE_MODE_FULL: "FULL (BUY & SELL ACTIVE)"
        }.get(s_info.trade_mode, f"UNKNOWN ({s_info.trade_mode})")

        print(f"   - Selected Symbol: {target_symbol}")
        print(f"   - Trade Mode: {trade_mode_str}")
        print(f"   - Live Bid: {tick.bid} | Live Ask: {tick.ask} | Spread: {round((tick.ask - tick.bid)*10, 1)} pts" if tick else "   - Live Quote: No tick received")
        if tick:
            tick_age_s = time.time() - tick.time
            print(f"   - Last Tick Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(tick.time))} UTC (Age: {round(tick_age_s, 1)}s)")

        # 3. Trajedor Risk Gate & Open Positions
        print(f"\n3. TRAJEDOR RISK GATES & DISPATCH READINESS:")
        positions = mt5.positions_get()
        total_open_positions = len(positions) if positions else 0
        
        ai_positions = []
        manual_positions = []
        if positions:
            for p in positions:
                is_ai = (p.magic == magic or p.magic in (SETTINGS.MAGIC_NUMBER, 888991, 888992, 888993))
                if is_ai:
                    ai_positions.append(p)
                else:
                    manual_positions.append(p)

        ai_volume = sum(p.volume for p in ai_positions)
        print(f"   - Armed Status in Dashboard: {'ARMED' if is_armed else 'DISARMED'}")
        print(f"   - Total Broker Open Positions: {total_open_positions} (Manual: {len(manual_positions)}, Trajedor AI: {len(ai_positions)})")
        print(f"   - Current Trajedor AI Exposure: {ai_volume:.2f} / {max_agg:.2f} lots (Cap: {max_agg:.2f})")
        print(f"   - Current Trajedor AI Position Count: {len(ai_positions)} / {max_pos} max")

        # 4. Pre-flight Simulation via mt5.order_check()
        print(f"\n4. ORDER PRE-FLIGHT (mt5.order_check) SIMULATION:")
        if not tick or tick.bid <= 0:
            print("   [BLOCKED] Market quote unavailable to simulate order.")
        else:
            test_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": target_symbol,
                "volume": min(max_single, 0.01),
                "type": mt5.ORDER_TYPE_BUY,
                "price": tick.ask,
                "sl": tick.ask - 5.0,
                "tp": tick.ask + 10.0,
                "deviation": 20,
                "magic": magic,
                "comment": "TRAJEDOR_PREFLIGHT_CHECK",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            # Attempt order_check
            chk = mt5.order_check(test_request)
            if chk is None:
                err = mt5.last_error()
                print(f"   - order_check returned None! MT5 Error: {err}")
            else:
                print(f"   - order_check Return Code: {chk.retcode} ({chk.comment})")
                print(f"   - Required Margin: ${chk.margin:.2f} | Remaining Free Margin: ${chk.margin_free:.2f}")
                if chk.retcode == 0 or "done" in chk.comment.lower():
                    print(f"   >>> [CAN PLACE TRADE]: YES! MT5 broker accepted pre-flight deal check!")
                else:
                    print(f"   >>> [BLOCKED BY BROKER/SETTINGS]: {chk.comment} (Code {chk.retcode})")

    finally:
        mt5.shutdown()
        time.sleep(0.2)

def main():
    cfg = load_accounts_config()
    for acc_id, a_cfg in cfg.items():
        check_terminal_readiness(acc_id, a_cfg)

if __name__ == "__main__":
    main()
