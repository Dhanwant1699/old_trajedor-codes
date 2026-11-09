import MetaTrader5 as mt5
import json

print("=== CHECKING DEFAULT RUNNING MT5 ===")
ok = mt5.initialize()
if ok:
    acc = mt5.account_info()
    term = mt5.terminal_info()
    if acc:
        print(f"Login: {acc.login}")
        print(f"Name: {acc.name}")
        print(f"Server: {acc.server}")
        print(f"Balance: {acc.balance} {acc.currency}")
        print(f"Equity: {acc.equity} {acc.currency}")
        print(f"Trade Allowed: {acc.trade_allowed}")
        print(f"Trade Expert (Algo Allowed): {acc.trade_expert}")
    if term:
        print(f"Terminal Path: {term.path}")
        print(f"Terminal Connected: {term.connected}")
        print(f"Terminal Trade Allowed: {term.trade_allowed}")
    
    # Check Symbol Info
    for sym in ["XAUUSD", "GOLD", "XAUUSDm"]:
        info = mt5.symbol_info(sym)
        if info:
            tick = mt5.symbol_info_tick(sym)
            print(f"Symbol {sym}: Bid={tick.bid if tick else 'N/A'}, Ask={tick.ask if tick else 'N/A'}, Spread={info.spread}")
            
    # Check Open Positions
    positions = mt5.positions_get()
    print(f"Open Positions Count: {len(positions) if positions else 0}")
    if positions:
        for p in positions:
            print(f"Ticket: {p.ticket}, Symbol: {p.symbol}, Type: {'BUY' if p.type==0 else 'SELL'}, Volume: {p.volume}, Open Price: {p.price_open}, Current Price: {p.price_current}, SL: {p.sl}, TP: {p.tp}, Profit: {p.profit}")
else:
    print(f"Failed to init default MT5: {mt5.last_error()}")
mt5.shutdown()
