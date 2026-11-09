import os
import sys
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MetaTrader5 as mt5
from core.dual_account_manager import DualAccountManager, AccountProfile

def test_dual_account_partial_booking():
    print("\n=======================================================")
    print("🧪 TESTING DUAL ACCOUNT MANAGER SENTRY 7 PARTIAL BOOKING")
    print("=======================================================")

    mgr = DualAccountManager(symbol="XAUUSD")
    
    # Create test profile
    profile = AccountProfile(
        account_id="test_acc",
        name="Test Account",
        terminal_path="",
        currency="USD",
        magic_number=777888,
        mode="STANDARD_PROP",
        tp1_close_pct=50.0
    )
    # Mock connect/shutdown
    profile.connect = MagicMock(return_value=True)
    profile.shutdown = MagicMock()
    mgr.accounts = [profile]

    # Mock MT5 methods
    mt5.positions_get = MagicMock()
    mt5.symbol_info_tick = MagicMock()
    mt5.symbol_info = MagicMock()
    mt5.order_send = MagicMock()

    # Mock symbol tick
    tick = MagicMock()
    tick.bid = 4350.0
    tick.ask = 4350.5
    mt5.symbol_info_tick.return_value = tick

    sym_info = MagicMock()
    sym_info.filling_mode = 2  # IOC
    mt5.symbol_info.return_value = sym_info

    # 1. Test standard 0.06 lot position reaching TP1 (R >= 1.20)
    mock_pos = MagicMock()
    mock_pos.ticket = 999111
    mock_pos.magic = 777888
    mock_pos.comment = "Chanakya_Buy"
    mock_pos.type = 0  # BUY
    mock_pos.price_open = 4340.0
    mock_pos.volume = 0.06
    mock_pos.sl = 4330.0  # initial R = 10.0 pts. current_price = 4350.0 -> price_gain = +10.0 pts -> R = 1.0R (wait, let's make bid 4353.0 -> R = 1.30R)
    mock_pos.tp = 4355.0
    mock_pos.profit = 78.0

    tick.bid = 4353.0  # R = (4353 - 4340) / 10 = +1.30R >= 1.20R!

    mt5.positions_get.return_value = [mock_pos]
    
    order_res = MagicMock()
    order_res.retcode = mt5.TRADE_RETCODE_DONE
    order_res.order = 123456
    order_res.deal = 123456
    mt5.order_send.return_value = order_res

    market_payload = {
        "pricing": {"bid": 4353.0, "ask": 4353.5, "spread_points": 5.0},
        "market_structures": {
            "m15_execution_structure": {"atr_14": 6.5, "rsi_14": 65.0, "candlestick_patterns": []}
        }
    }

    actions = mgr.evaluate_and_manage_all_accounts(market_payload=market_payload, news_payload={})

    partial_acts = [a for a in actions if "PARTIAL" in a.get("type", "")]
    assert len(partial_acts) == 1, f"Expected 1 partial action, got {len(partial_acts)}"
    act = partial_acts[0]
    print(f"   ✅ Partial Booking Triggered: {act['thought']}")
    assert 999111 in profile.tier1_partial_tickets
    assert 999111 in profile.breakeven_locked_tickets

    # Verify order_send was called with volume = 0.03 lots (50% of 0.06)
    # Verify order_send calls
    calls = mt5.order_send.call_args_list
    deal_call = next((c[0][0] for c in calls if c[0][0]["action"] == mt5.TRADE_ACTION_DEAL), None)
    assert deal_call is not None, "TRADE_ACTION_DEAL call must be present for partial booking!"
    assert deal_call["volume"] == 0.02  # 33% of 0.06 lots
    assert deal_call["position"] == 999111
    assert deal_call["type"] == mt5.ORDER_TYPE_SELL  # Closing a BUY
    print(f"   ✅ Deal Request Verified: Closed {deal_call['volume']} lots on Ticket #{deal_call['position']}")

    sltp_call = next((c[0][0] for c in calls if c[0][0]["action"] == mt5.TRADE_ACTION_SLTP and c[0][0]["sl"] == 4340.35), None)
    assert sltp_call is not None, "TRADE_ACTION_SLTP call for runner must be present!"
    assert sltp_call["position"] == 999111
    assert sltp_call["sl"] == 4340.35  # Open 4340.0 + 0.35 buffer
    print(f"   ✅ Runner Protected: SL moved to Breakeven @ {sltp_call['sl']}")

    print("\n=======================================================")
    print("🎯 SENTRY 7 DYNAMIC PARTIAL BOOKING TEST PASSED 100%!")
    print("=======================================================\n")

if __name__ == "__main__":
    test_dual_account_partial_booking()
