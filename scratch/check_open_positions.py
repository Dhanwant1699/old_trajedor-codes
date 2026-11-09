import MetaTrader5 as mt5
import json
import datetime

with open('trajedor/config/accounts.json', 'r') as f:
    cfg = json.load(f)

for acc_id, acc in cfg.items():
    print(f"\n=================== {acc_id}: {acc['broker']} (Login: {acc['login']}) ===================")
    if mt5.initialize(path=acc['terminal_path']):
        positions = mt5.positions_get()
        print(f"Open Positions: {len(positions) if positions else 0}")
        if positions:
            for p in positions:
                p_type = "BUY" if p.type == 0 else "SELL"
                print(f"  Pos #{p.ticket} | Sym: {p.symbol} | {p_type} {p.volume} @ {p.price_open} | Cur: {p.price_current} | SL: {p.sl} | TP: {p.tp} | PnL: ${p.profit:.2f} | Magic: {p.magic} | Comment: {p.comment}")

        from_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
        deals = mt5.history_deals_get(from_time, datetime.datetime.now())
        print(f"Recent Deals (last 30m): {len(deals) if deals else 0}")
        if deals:
            for d in deals:
                t_str = datetime.datetime.fromtimestamp(d.time).strftime('%H:%M:%S')
                d_type = "BUY" if d.type == 0 else "SELL"
                print(f"  Deal #{d.ticket} (Order #{d.order}) | {t_str} | {d_type} {d.volume} @ {d.price} | PnL: ${d.profit:.2f} | Comment: {d.comment}")

        mt5.shutdown()
