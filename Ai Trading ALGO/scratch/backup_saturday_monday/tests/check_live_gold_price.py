import MetaTrader5 as mt5
import json

if mt5.initialize():
    symbol = "XAUUSD"
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    
    print("=== LIVE MT5 TICK FOR XAUUSD ===")
    if tick:
        print(f"Bid: {tick.bid}")
        print(f"Ask: {tick.ask}")
        print(f"Last: {tick.last}")
        print(f"Time: {tick.time}")
    else:
        print("No tick for XAUUSD")

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 5)
    if rates is not None and len(rates) > 0:
        print("\n=== LATEST 5 M15 CANDLES FOR XAUUSD ===")
        for r in rates:
            print(f"Time: {r['time']}, Open: {r['open']}, High: {r['high']}, Low: {r['low']}, Close: {r['close']}")

    mt5.shutdown()
else:
    print("Failed to initialize MT5")
