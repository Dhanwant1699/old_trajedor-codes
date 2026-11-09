import os
import sys
from datetime import datetime
import MetaTrader5 as mt5
from collections import defaultdict
import json

terminals = [
    ('acc_1', 'ICMarketsSC Master EUR', r'C:\Program Files\MetaTrader 5\terminal64.exe'),
    ('acc_2', 'GTCGlobalSA Micro USD', r'C:\Program Files\MetaTrader 5 - 1\terminal64.exe'),
    ('acc_3', 'GTCGlobalSA Standard USD', r'C:\Program Files\MetaTrader 5 - 2\terminal64.exe')
]

trades_by_date = {"2026-10-01": [], "2026-10-02": []}

for acc_id, acc_name, term_path in terminals:
    if not os.path.exists(term_path):
        continue
    if mt5.initialize(path=term_path, timeout=5000):
        from_dt = datetime(2026, 10, 1, 0, 0, 0)
        to_dt = datetime(2026, 10, 2, 23, 59, 59)
        deals = mt5.history_deals_get(from_dt, to_dt)
        if deals:
            pos_deals = defaultdict(list)
            for d in deals:
                pos_deals[d.position_id].append(d)

            for pos_id, p_deals in pos_deals.items():
                in_deals = [d for d in p_deals if d.entry == 0]
                out_deals = [d for d in p_deals if d.entry == 1]
                if not in_deals:
                    continue

                first_deal = in_deals[0]
                is_ai = (first_deal.magic in (777999, 777888, 888991, 888992, 888993)) or \
                        any("Chanakya" in str(d.comment) or "EarlyCut" in str(d.comment) or "AI" in str(d.comment) for d in p_deals)
                
                if not is_ai:
                    continue

                dt_str = datetime.fromtimestamp(first_deal.time).strftime("%Y-%m-%d")
                if dt_str not in trades_by_date:
                    continue

                total_pnl = sum(d.profit for d in p_deals) + sum(d.commission for d in p_deals) + sum(d.swap for d in p_deals)
                total_vol = sum(d.volume for d in in_deals)
                direction = "BUY" if first_deal.type == 0 else "SELL"
                entry_time = datetime.fromtimestamp(first_deal.time).strftime("%H:%M:%S")
                exit_time = datetime.fromtimestamp(out_deals[-1].time).strftime("%H:%M:%S") if out_deals else "OPEN"
                exit_comments = [str(d.comment) for d in out_deals if d.comment]
                in_comments = [str(d.comment) for d in in_deals if d.comment]

                trades_by_date[dt_str].append({
                    "account": acc_name,
                    "pos_id": pos_id,
                    "symbol": first_deal.symbol,
                    "direction": direction,
                    "vol": round(total_vol, 2),
                    "entry_price": round(first_deal.price, 2),
                    "exit_price": round(out_deals[-1].price, 2) if out_deals else 0.0,
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "pnl": round(total_pnl, 2),
                    "in_comments": in_comments,
                    "exit_comments": exit_comments
                })
        mt5.shutdown()

print("REPORT DATA:")
for dt in ["2026-10-01", "2026-10-02"]:
    tr = trades_by_date[dt]
    wins = [t for t in tr if t["pnl"] > 0]
    losses = [t for t in tr if t["pnl"] < 0]
    net = sum(t["pnl"] for t in tr)
    print(f"\n=== DATE: {dt} ===")
    print(f"Total AI Trades: {len(tr)} | Wins: {len(wins)} | Losses: {len(losses)} | Net PnL: €{net:+.2f}")
    for t in tr:
        outcome = "WIN" if t["pnl"] > 0 else "LOSS"
        print(f"  [{outcome}] {t['entry_time']}->{t['exit_time']} | {t['direction']} {t['vol']} @ {t['entry_price']}->{t['exit_price']} | PnL: {t['pnl']:+6.2f} | In: {t['in_comments']} | Exit: {t['exit_comments']}")
