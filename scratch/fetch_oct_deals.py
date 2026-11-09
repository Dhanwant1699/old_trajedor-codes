import os
import sys
from datetime import datetime, timezone
import MetaTrader5 as mt5

terminals = [
    ('acc_1', r'C:\Program Files\MetaTrader 5\terminal64.exe'),
    ('acc_2', r'C:\Program Files\MetaTrader 5 - 1\terminal64.exe'),
    ('acc_3', r'C:\Program Files\MetaTrader 5 - 2\terminal64.exe')
]

print("=" * 80)
print("FETCHING OCT 1 & 2 DEALS ACROSS ALL MT5 TERMINALS")
print("=" * 80)

for acc_id, term_path in terminals:
    print(f"\n>>> Checking Terminal [{acc_id}]: {term_path}")
    if not os.path.exists(term_path):
        print("  [ERROR] Path does not exist.")
        continue

    if mt5.initialize(path=term_path, timeout=5000):
        acc = mt5.account_info()
        print(f"  Connected to Login #{acc.login} | Server: {acc.server} | Currency: {acc.currency}")
        
        # 1. Fetch exact Oct 1 to Oct 3 range
        from_dt = datetime(2026, 10, 1, 0, 0, 0)
        to_dt = datetime(2026, 10, 3, 23, 59, 59)
        deals = mt5.history_deals_get(from_dt, to_dt)
        print(f"  Deals in Oct 1 - Oct 3, 2026 window: {len(deals) if deals else 0}")
        
        if deals:
            for d in deals:
                time_str = datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S")
                entry_str = "IN" if d.entry == 0 else ("OUT" if d.entry == 1 else "IN/OUT")
                type_str = "BUY" if d.type == 0 else ("SELL" if d.type == 1 else str(d.type))
                print(f"    Deal #{d.ticket} | Time: {time_str} | Pos: {d.position_id} | {d.symbol} {type_str} {d.volume} lots @ {d.price} | PnL: {d.profit:+.2f} | Magic: {d.magic} | Comment: '{d.comment}' | Entry: {entry_str}")
        else:
            # Also check wider range in case broker timestamps differ
            print("  Checking wider window (Sep 28 to Oct 4)...")
            wide_deals = mt5.history_deals_get(datetime(2026, 9, 28), datetime(2026, 10, 4, 23, 59, 59))
            if wide_deals:
                print(f"  Found {len(wide_deals)} deals in wider window. Listing last 10:")
                for d in wide_deals[-10:]:
                    time_str = datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"    Deal #{d.ticket} | Time: {time_str} | Pos: {d.position_id} | {d.symbol} | PnL: {d.profit:+.2f} | Magic: {d.magic} | Comment: '{d.comment}'")
            else:
                print("  No deals found in wider window either.")

        mt5.shutdown()
    else:
        print("  [ERROR] Failed to initialize MT5 terminal.")
