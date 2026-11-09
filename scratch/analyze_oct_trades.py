import os
import sys
from datetime import datetime, timezone
import MetaTrader5 as mt5
from collections import defaultdict
import json

terminals = [
    ('acc_1', 'ICMarketsSC Master EUR', r'C:\Program Files\MetaTrader 5\terminal64.exe'),
    ('acc_2', 'GTCGlobalSA Micro USD', r'C:\Program Files\MetaTrader 5 - 1\terminal64.exe'),
    ('acc_3', 'GTCGlobalSA Standard USD', r'C:\Program Files\MetaTrader 5 - 2\terminal64.exe')
]

all_positions = []

for acc_id, acc_name, term_path in terminals:
    if not os.path.exists(term_path):
        continue
    if mt5.initialize(path=term_path, timeout=5000):
        # Fetch Oct 1 00:00 to Oct 2 23:59:59 UTC
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
                
                if not in_deals and not out_deals:
                    continue

                # Identify if placed by AI Trading Algo
                first_deal = in_deals[0] if in_deals else p_deals[0]
                is_ai = (first_deal.magic in (777999, 777888, 888991, 888992, 888993)) or \
                        any("Chanakya" in str(d.comment) or "EarlyCut" in str(d.comment) or "AI" in str(d.comment) for d in p_deals)
                
                # We specifically want AI Trading Algo trades as requested by user
                total_profit = sum(d.profit for d in p_deals) + sum(d.commission for d in p_deals) + sum(d.swap for d in p_deals)
                total_vol = sum(d.volume for d in in_deals) if in_deals else p_deals[0].volume
                direction = "BUY" if first_deal.type == 0 else "SELL"
                entry_price = first_deal.price
                entry_time = datetime.fromtimestamp(first_deal.time).strftime("%Y-%m-%d %H:%M:%S")
                
                exit_price = out_deals[-1].price if out_deals else 0.0
                exit_time = datetime.fromtimestamp(out_deals[-1].time).strftime("%Y-%m-%d %H:%M:%S") if out_deals else "OPEN"
                exit_comments = [str(d.comment) for d in out_deals if d.comment]
                in_comments = [str(d.comment) for d in in_deals if d.comment]

                all_positions.append({
                    "account": acc_name,
                    "position_id": pos_id,
                    "is_ai": is_ai,
                    "symbol": first_deal.symbol,
                    "direction": direction,
                    "volume": round(total_vol, 2),
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "pnl": round(total_profit, 2),
                    "magic": first_deal.magic,
                    "in_comments": in_comments,
                    "exit_comments": exit_comments,
                    "num_deals": len(p_deals)
                })
        mt5.shutdown()

print("=" * 80)
print(f"TOTAL RECONSTRUCTED POSITIONS (OCT 1 - OCT 2): {len(all_positions)}")
ai_positions = [p for p in all_positions if p["is_ai"]]
print(f"AI TRADING ALGO POSITIONS: {len(ai_positions)}")
print("=" * 80)

# Sort chronologically
ai_positions.sort(key=lambda x: x["entry_time"])

wins = [p for p in ai_positions if p["pnl"] > 0]
losses = [p for p in ai_positions if p["pnl"] < 0]
breakevens = [p for p in ai_positions if p["pnl"] == 0]
total_pnl = sum(p["pnl"] for p in ai_positions)
win_rate = (len(wins) / len(ai_positions) * 100) if ai_positions else 0.0

print(f"WIN COUNT: {len(wins)} | LOSS COUNT: {len(losses)} | BREAKEVEN: {len(breakevens)}")
print(f"WIN RATE: {win_rate:.1f}% | NET PnL: €{total_pnl:.2f}")
print("-" * 80)

for idx, p in enumerate(ai_positions, 1):
    outcome = "WIN" if p["pnl"] > 0 else ("LOSS" if p["pnl"] < 0 else "BE")
    print(f"[{idx:02d}] {p['entry_time']} | Pos #{p['position_id']} | {p['direction']} {p['volume']} lots @ {p['entry_price']} -> {p['exit_price']} | PnL: {p['pnl']:+6.2f} [{outcome}]")
    print(f"     In-Comments: {p['in_comments']} | Exit-Comments: {p['exit_comments']}")
