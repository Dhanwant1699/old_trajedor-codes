import MetaTrader5 as mt5
import datetime

mt5.initialize()
sym = 'XAUUSD.ecn' if mt5.symbol_info('XAUUSD.ecn') else 'XAUUSD'
rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 15)

print(f"=== REAL-TIME M5 CANDLE DATA FETCHED AUTONOMOUSLY FROM MT5 ({sym}) ===\n")
print(f"{'TIME':<20} | {'OPEN':<9} | {'HIGH':<9} | {'LOW':<9} | {'CLOSE':<9} | {'TYPE':<5}")
print("-" * 70)
for r in rates:
    t_str = datetime.datetime.fromtimestamp(r['time'], datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    direction = 'BULL' if r['close'] >= r['open'] else 'BEAR'
    print(f"{t_str:<20} | {r['open']:>9.2f} | {r['high']:>9.2f} | {r['low']:>9.2f} | {r['close']:>9.2f} | {direction:<5}")

tick = mt5.symbol_info_tick(sym)
print(f"\nLIVE TICK: Bid={tick.bid}, Ask={tick.ask}")

# Also calculate exact session high and low over last 100 candles
rates_100 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 100)
session_low = min(r['low'] for r in rates_100)
session_high = max(r['high'] for r in rates_100)
print(f"Session Low (The bottom wick in screenshot): ${session_low:.2f}")
print(f"Session High (The top spike in screenshot): ${session_high:.2f}")

mt5.shutdown()
