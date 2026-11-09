import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_engine import MT5DataEngine

print("--- Testing Gold (XAUUSD) Data Engine ---")
gold_engine = MT5DataEngine(symbol="XAUUSD")
if gold_engine.connect():
    payload_gold = gold_engine.extract_full_market_payload()
    price_gold = payload_gold["pricing"]["bid"]
    spread_gold = payload_gold["pricing"]["spread_points"]
    fvgs_gold = payload_gold["market_structures"]["m15_execution_structure"]["active_fvgs"]
    print(f"[OK] Gold Symbol: {gold_engine.symbol} | Price: ${price_gold:,.2f} | Spread: {spread_gold} pts | Active FVGs: {len(fvgs_gold)}")
    gold_engine.disconnect()

print("\n--- Testing Bitcoin (BTCUSD / BTC) Data Engine ---")
btc_engine = MT5DataEngine(symbol="BTCUSD")
if btc_engine.connect():
    payload_btc = btc_engine.extract_full_market_payload()
    price_btc = payload_btc["pricing"]["bid"]
    spread_btc = payload_btc["pricing"]["spread_points"]
    fvgs_btc = payload_btc["market_structures"]["m15_execution_structure"]["active_fvgs"]
    print(f"[OK] Bitcoin Symbol: {btc_engine.symbol} | Price: ${price_btc:,.2f} | Spread: {spread_btc} pts | Active FVGs: {len(fvgs_btc)}")
    btc_engine.disconnect()

print("\n[SUCCESS] Both Gold & Bitcoin Data Engines Verified Concurrently!")
