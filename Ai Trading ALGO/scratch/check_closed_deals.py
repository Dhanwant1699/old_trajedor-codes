import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json

with open('data/admin_config.json', 'r') as f:
    cfg = json.load(f)

for acc_id, a_cfg in cfg.get('accounts', {}).items():
    p = a_cfg.get('terminal_path')
    name = a_cfg.get('name', acc_id)
    if mt5.initialize(path=p):
        now = datetime.now()
        deals = mt5.history_deals_get(now - timedelta(days=2), now)
        print(f"\n=== CLOSED DEALS FOR {name} ({acc_id}) ===")
        if deals:
            for d in deals:
                if d.entry == 1: # Out / close deal
                    print(f"Deal #{d.ticket} | PosID #{d.position_id} | Vol: {d.volume} | Price: {d.price} | Profit: {d.profit} | Comment: {d.comment} | Time: {datetime.fromtimestamp(d.time)}")
        else:
            print("No deals found.")
        mt5.shutdown()
