import MetaTrader5 as mt5
import json
import datetime

with open('trajedor/config/accounts.json', 'r') as f:
    cfg = json.load(f)

acc = cfg['acc_1']
if mt5.initialize(path=acc['terminal_path']):
    # check positions directly
    positions = mt5.positions_get()
    print('OPEN POSITIONS:', len(positions) if positions else 0)
    if positions:
        for p in positions:
            print(f'Ticket: {p.ticket}, Symbol: {p.symbol}, Type: {"BUY" if p.type==0 else "SELL"}, Volume: {p.volume}, Price Open: {p.price_open}, Price Current: {p.price_current}, SL: {p.sl}, TP: {p.tp}, Profit: ${p.profit:.2f}')
    
    from_time = datetime.datetime.now() - datetime.timedelta(hours=6)
    deals = mt5.history_deals_get(from_time, datetime.datetime.now())
    print('\nRECENT DEALS (last 6h):', len(deals) if deals else 0)
    if deals:
        for d in deals:
            deal_type = "BUY" if d.type == 0 else ("SELL" if d.type == 1 else str(d.type))
            entry_type = "IN" if d.entry == 0 else ("OUT" if d.entry == 1 else str(d.entry))
            print(f'Deal: {d.ticket}, Order: {d.order}, Time: {datetime.datetime.fromtimestamp(d.time)}, Symbol: {d.symbol}, Type: {deal_type}, Entry: {entry_type}, Vol: {d.volume}, Price: {d.price}, Profit: ${d.profit:.2f}, Comment: {d.comment}')

    sym = 'XAUUSD.ecn' if mt5.symbol_info('XAUUSD.ecn') else 'XAUUSD'
    tick = mt5.symbol_info_tick(sym)
    if tick:
        print(f'\nCURRENT TICK {sym}: Bid={tick.bid}, Ask={tick.ask}')
    mt5.shutdown()
else:
    print('Failed to init MT5')
