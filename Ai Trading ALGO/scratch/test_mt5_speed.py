import time
import os
import sys
import MetaTrader5 as mt5

sys.path.insert(0, os.path.abspath("."))
from config import CONFIG
from core.data_engine import MT5DataEngine

print("Initializing MT5 connection...")
t0 = time.time()
ok = mt5.initialize()
print(f"mt5.initialize() took {time.time()-t0:.4f}s | connected={ok}")

if ok:
    t0 = time.time()
    info = mt5.account_info()
    print(f"account_info took {time.time()-t0:.4f}s | equity={info.equity if info else None}")
    
    t0 = time.time()
    tick = mt5.symbol_info_tick("XAUUSD")
    print(f"symbol_info_tick took {time.time()-t0:.4f}s | bid={tick.bid if tick else None}")
    
    t0 = time.time()
    pos = mt5.positions_get()
    print(f"positions_get took {time.time()-t0:.4f}s | open={len(pos) if pos else 0}")
