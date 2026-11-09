import MetaTrader5 as mt5
import json

p = r"C:\Program Files\MetaTrader 5\terminal64.exe"
if mt5.initialize(path=p, timeout=5000):
    rates = mt5.copy_rates_from_pos("XAUUSD.ecn", mt5.TIMEFRAME_M5, 0, 30)
    tick = mt5.symbol_info_tick("XAUUSD.ecn")
    price = tick.bid
    
    highs = [float(c[2]) for c in rates]
    lows = [float(c[3]) for c in rates]
    session_high = max(highs)
    session_low = min(lows)
    range_span = max(5.0, session_high - session_low)
    range_pct = (price - session_low) / range_span
    
    recent_highs = highs[-6:]
    recent_lows = lows[-6:]
    local_high = max(recent_highs)
    local_low = min(recent_lows)
    
    print(f"Current Gold: ${price:.2f}")
    print(f"Session Range: ${session_low:.2f} to ${session_high:.2f} ({range_span:.2f} pts)")
    print(f"Price Location: {range_pct*100:.1f}% from Floor")
    print(f"Recent Local Swing: Low=${local_low:.2f} | High=${local_high:.2f}")
    
    mt5.shutdown()
