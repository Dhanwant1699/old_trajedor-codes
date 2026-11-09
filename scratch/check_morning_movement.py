import os
import sys
import time
from datetime import datetime, timezone
import MetaTrader5 as mt5

p = r"C:\Program Files\MetaTrader 5\terminal64.exe"
if mt5.initialize(path=p, timeout=5000):
    rates = mt5.copy_rates_from_pos("XAUUSD.ecn", mt5.TIMEFRAME_M5, 0, 60)
    if rates is not None and len(rates) > 0:
        highs = [r[2] for r in rates]
        lows = [r[3] for r in rates]
        opens = [r[1] for r in rates]
        closes = [r[4] for r in rates]
        times = [r[0] for r in rates]
        
        start_time = datetime.fromtimestamp(times[0], tz=timezone.utc).strftime('%H:%M:%S UTC')
        end_time = datetime.fromtimestamp(times[-1], tz=timezone.utc).strftime('%H:%M:%S UTC')
        
        day_high = max(highs)
        day_low = min(lows)
        day_open = opens[0]
        curr_price = closes[-1]
        
        print(f"Candles analyzed: {len(rates)} (from {start_time} to {end_time})")
        print(f"Session Open: ${day_open:.2f}")
        print(f"Session High: ${day_high:.2f}")
        print(f"Session Low:  ${day_low:.2f}")
        print(f"Current Bid:  ${curr_price:.2f}")
        print(f"Total Range:  ${day_high - day_low:.2f} ({(day_high - day_low)*10:.1f} points)")
        print(f"Net Change:   ${curr_price - day_open:.2f}")
    else:
        print("No rates returned for XAUUSD.ecn")
    mt5.shutdown()
else:
    print("MT5 init failed")
