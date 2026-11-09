import MetaTrader5 as mt5
import json
import os

config_path = r'data\admin_config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

accounts = cfg.get('accounts', {})
print(f"=== CHECKING {len(accounts)} CONFIGURED ACCOUNTS ===")

for acc_id, acc_info in accounts.items():
    path = acc_info.get('terminal_path')
    name = acc_info.get('name', acc_id)
    print(f"\n--- [{acc_id}] {name} ---")
    print(f"Path: {path}")
    if not os.path.exists(path):
        print("Status: Path does NOT exist!")
        continue
    
    init_ok = mt5.initialize(path=path, timeout=3000)
    if not init_ok:
        print(f"Status: MT5 initialize failed! Error: {mt5.last_error()}")
        continue
    
    term_info = mt5.terminal_info()
    acc = mt5.account_info()
    
    if term_info is None or acc is None:
        print(f"Status: Failed to get info! Error: {mt5.last_error()}")
    else:
        print(f"Connected to Broker: {term_info.connected}")
        print(f"Login: {acc.login} ({acc.name})")
        print(f"Server: {acc.server}")
        print(f"Balance: {acc.balance:,.2f} {acc.currency} | Equity: {acc.equity:,.2f} {acc.currency}")
        print(f"Broker Trade Allowed: {acc.trade_allowed}")
        print(f"Broker EA/Algo Allowed: {acc.trade_expert}")
        print(f"MT5 'Algo Trading' Button State (Active): {term_info.trade_allowed}")
        
        can_place_algo_trade = (term_info.connected and acc.trade_allowed and acc.trade_expert and term_info.trade_allowed)
        print(f"CAN AI PLACE TRADES NOW? -> {'YES (READY)' if can_place_algo_trade else 'NO (BLOCKED - Check Algo Trading Button or Connection)'}")
        
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            print("Open Positions: 0 (No open trades)")
        else:
            print(f"Open Positions: {len(positions)} active trade(s):")
            for p in positions:
                side = "BUY" if p.type == 0 else "SELL"
                print(f"  - Ticket #{p.ticket} | {p.symbol} | {side} {p.volume} lots | Open: {p.price_open} | SL: {p.sl} | TP: {p.tp} | Floating P/L: {p.profit:+.2f} {acc.currency}")
    mt5.shutdown()

print("\n=== ALSO CHECKING ALL INSTALLED TERMINALS IN SYSTEM ===")
from core.dashboard_server import auto_detect_installed_terminals
installed = auto_detect_installed_terminals()
for t in installed:
    print(f"- {t.get('name')} | Login: {t.get('login')} | Server: {t.get('server')} | Connected: {t.get('connected')} | Equity: {t.get('equity')} {t.get('currency')} | Active in Algo: {t.get('is_active')}")
