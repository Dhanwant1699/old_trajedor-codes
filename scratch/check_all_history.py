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
                print(f"  Pos #{p.ticket} | Sym: {p.symbol} | Type: {'BUY' if p.type==0 else 'SELL'} | Vol: {p.volume} | Open: {p.price_open} | Current: {p.price_current} | SL: {p.sl} | TP: {p.tp} | Profit: ${p.profit:.2f}")

        orders = mt5.history_orders_get(datetime.datetime(2025, 1, 1), datetime.datetime.now())
        print(f"Historical Orders: {len(orders) if orders else 0}")
        if orders:
            for o in orders[-10:]:
                print(f"  Order #{o.ticket} | Time: {datetime.datetime.fromtimestamp(o.time_setup)} | Sym: {o.symbol} | Type: {o.type} | Vol: {o.volume_initial} | State: {o.state} | SL: {o.sl} | TP: {o.tp} | Comment: {o.comment}")

        deals = mt5.history_deals_get(datetime.datetime(2025, 1, 1), datetime.datetime.now())
        print(f"Historical Deals: {len(deals) if deals else 0}")
        if deals:
            for d in deals[-10:]:
                print(f"  Deal #{d.ticket} (Order #{d.order}) | Time: {datetime.datetime.fromtimestamp(d.time)} | Sym: {d.symbol} | Type: {d.type} | Entry: {d.entry} | Price: {d.price} | Profit: ${d.profit:.2f} | Comment: {d.comment}")
        mt5.shutdown()
    else:
        print("Failed to initialize MT5")
