import MetaTrader5 as mt5
import time

print("1. Initializing default MT5...")
t0 = time.time()
ok1 = mt5.initialize()
print(f"Default init: {ok1} in {time.time()-t0:.2f}s")
if ok1:
    print("Account info:", mt5.account_info().login)

print("\n2. Initializing Terminal - 1 without shutdown...")
t0 = time.time()
ok2 = mt5.initialize(path=r"C:\Program Files\MetaTrader 5 - 1\terminal64.exe", timeout=1000)
print(f"Terminal 1 init: {ok2} in {time.time()-t0:.2f}s")

print("\n3. Shutdown and Initializing Terminal - 1...")
mt5.shutdown()
t0 = time.time()
ok3 = mt5.initialize(path=r"C:\Program Files\MetaTrader 5 - 1\terminal64.exe", timeout=1000)
print(f"Terminal 1 with shutdown init: {ok3} in {time.time()-t0:.2f}s")
if ok3:
    print("Account info:", mt5.account_info().login)
mt5.shutdown()
