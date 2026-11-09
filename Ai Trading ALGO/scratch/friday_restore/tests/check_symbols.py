import MetaTrader5 as mt5

if mt5.initialize():
    symbols = mt5.symbols_get()
    all_names = [s.name for s in symbols] if symbols else []
    
    btc_matches = [s for s in all_names if "BTC" in s.upper() or "BITCOIN" in s.upper()]
    gold_matches = [s for s in all_names if "XAU" in s.upper() or "GOLD" in s.upper()]
    
    print("Gold matches in MT5:", gold_matches)
    print("Bitcoin matches in MT5:", btc_matches)
    mt5.shutdown()
else:
    print("MT5 initialize failed")
