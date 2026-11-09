import MetaTrader5 as mt5

if mt5.initialize():
    for name in ["BTC", "BTCUSD", "XAUUSD"]:
        info = mt5.symbol_info(name)
        tick = mt5.symbol_info_tick(name)
        if info:
            print(f"Symbol {name}: Enabled={info.visible}, Digits={info.digits}, Contract={info.trade_contract_size}, MinLot={info.volume_min}, Price={tick.ask if tick else 'No Tick'}")
            if not info.visible:
                mt5.symbol_select(name, True)
                print(f"Selected {name} to Market Watch -> Now visible={mt5.symbol_info(name).visible}")
        else:
            print(f"Symbol {name} not found")
    mt5.shutdown()
