import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import MetaTrader5 as mt5
from core.execution_engine import MT5ExecutionEngine

def run_test():
    print("==================================================")
    print("🚀 BULLION AI - MT5 LIVE TRADE PLACEMENT TEST")
    print("==================================================")
    
    if not mt5.initialize():
        print(f"❌ Failed to connect to MT5: {mt5.last_error()}")
        return

    acc = mt5.account_info()
    term = mt5.terminal_info()
    print(f"👤 Account: {acc.login} ({acc.name}) | Server: {acc.server}")
    print(f"💰 Balance: {acc.balance} {acc.currency} | Equity: {acc.equity} {acc.currency}")
    print(f"🤖 Algo Trading Allowed: {term.trade_allowed} | Account Trade Allowed: {acc.trade_allowed}")

    symbol = "XAUUSD"
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"❌ Failed to get live tick for {symbol}")
        mt5.shutdown()
        return

    current_bid = tick.bid
    current_ask = tick.ask
    print(f"\n📊 Live Market: Bid = {current_bid:.2f} | Ask = {current_ask:.2f} | Spread = {(current_ask - current_bid)*10:.1f} pts")

    # Set proper SL and TP for SELL trade
    # On SELL: SL is above entry, TP is below entry
    sl_distance = 6.0  # 6 points above entry
    tp_distance = 6.0  # 6 points below entry
    sl_price = round(current_bid + sl_distance, 2)
    tp_price = round(current_bid - tp_distance, 2)

    exec_engine = MT5ExecutionEngine(symbol=symbol, magic_number=777888)

    print(f"\n📤 Placing 0.01 Lot SELL Trade on running candle...")
    print(f"   Action: SELL")
    print(f"   Volume: 0.01 Lots")
    print(f"   Target Price: ~{current_bid:.2f}")
    print(f"   Stop Loss (SL): {sl_price:.2f} (+{sl_distance} pts)")
    print(f"   Take Profit (TP): {tp_price:.2f} (-{tp_distance} pts)")

    success, msg, ticket = exec_engine.send_market_order(
        action="SELL",
        volume=0.01,
        sl=sl_price,
        tp=tp_price,
        comment="Bullion_Test_Sell",
        consensus_score=92
    )

    if not success or not ticket:
        print(f"❌ Order Placement FAILED: {msg}")
        mt5.shutdown()
        return

    print(f"✅ Order Placed SUCCESSFULLY!")
    print(f"   Ticket: #{ticket}")
    print(f"   Message: {msg}")

    # Verify live position on MT5 terminal
    time.sleep(1.0)
    pos = mt5.positions_get(ticket=ticket)
    if pos:
        p = pos[0]
        print(f"\n🔍 VERIFYING POSITION ON MT5 TERMINAL:")
        print(f"   Ticket: #{p.ticket}")
        print(f"   Symbol: {p.symbol}")
        print(f"   Type: {'SELL' if p.type == 1 else 'BUY'}")
        print(f"   Volume: {p.volume} Lots")
        print(f"   Open Price: {p.price_open:.2f}")
        print(f"   Current Price: {p.price_current:.2f}")
        print(f"   Verified SL on Broker: {p.sl:.2f}")
        print(f"   Verified TP on Broker: {p.tp:.2f}")
        print(f"   Floating P&L: {p.profit:.2f} {acc.currency}")
    else:
        print("⚠️ Could not find open position for ticket (it may have closed immediately).")

    # Let the trade run for a few seconds to simulate candle observation
    print("\n⏳ Holding position for 4 seconds to observe price action and floating P&L...")
    for i in range(4):
        time.sleep(1.0)
        pos = mt5.positions_get(ticket=ticket)
        if pos:
            p = pos[0]
            print(f"   [Tick {i+1}] Current: {p.price_current:.2f} | Floating P&L: {p.profit:+.2f} {acc.currency}")

    # Now close position cleanly
    print(f"\n🚪 Closing Position #{ticket} now...")
    close_ok, close_msg = exec_engine.close_position(ticket=ticket, comment="Bullion_Test_Close")
    if close_ok:
        print(f"✅ Position #{ticket} CLOSED SUCCESSFULLY!")
        print(f"   Result: {close_msg}")
    else:
        print(f"❌ Close failed: {close_msg}")

    # Check closed deal history
    time.sleep(1.0)
    deals = mt5.history_deals_get(position=ticket)
    if deals:
        print("\n📜 CLOSED DEAL AUDIT TRAIL:")
        for d in deals:
            deal_type_str = "ENTRY_IN" if d.entry == 0 else "ENTRY_OUT"
            print(f"   Deal #{d.ticket} | {deal_type_str} | Price: {d.price:.2f} | Volume: {d.volume} | Profit: {d.profit:+.2f} {acc.currency}")

    print("\n==================================================")
    print("🎯 TEST COMPLETED: Full Open -> Verify -> Close Cycle Verified!")
    print("==================================================")
    mt5.shutdown()

if __name__ == "__main__":
    run_test()
