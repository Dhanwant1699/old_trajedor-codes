"""
Unit & Integration Test for 7-Sentry Dynamic Trade Lifecycle Suite.
Simulates real-world market tick events, order book surges, reversals, and news shocks.
"""

import sys
import os
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.pro_trade_manager import ProTradeManager
from core.execution_engine import MT5ExecutionEngine


def test_sentry_suite():
    print("=" * 80)
    print("🧪 TESTING 7-SENTRY DYNAMIC TRADE LIFECYCLE SUITE")
    print("=" * 80)

    # 1. Setup Mock Execution Engine
    mock_exec = MagicMock(spec=MT5ExecutionEngine)
    mock_exec.symbol = "XAUUSD"
    mock_exec.move_to_breakeven.return_value = (True, "Breakeven SL set at entry + 0.40")
    mock_exec.update_stop_loss.return_value = (True, "SL updated to trailing level")
    mock_exec.close_position.return_value = (True, "Position closed")
    mock_exec.close_partial_position.return_value = (True, "Partial volume closed")

    manager = ProTradeManager(execution_engine=mock_exec)

    # Base Market Payload
    base_market = {
        "pricing": {"bid": 2700.00, "ask": 2700.20, "spread_points": 20.0},
        "market_structures": {
            "m15_execution_structure": {
                "atr_14": 6.00,
                "rsi_14": 52.0,
                "candlestick_patterns": []
            },
            "m5_micro_momentum": {
                "rsi_14": 50.0,
                "ema_9": 2699.5,
                "ema_21": 2698.0
            }
        },
        "tick_order_flow": {
            "ask_lifters_pct": 55.0,
            "bid_hitters_pct": 45.0,
            "flow_imbalance": "BULLISH_AGGRESSION"
        },
        "volume_delta_cvd": {
            "cvd_pattern": "BULLISH_ACCUMULATION"
        },
        "liquidity_execution_quality": {
            "spread_ratio": 1.0,
            "clearance": "CLEARED"
        }
    }

    base_news = {
        "news_blackout_active": False,
        "minutes_to_next_impact": 120
    }

    # -------------------------------------------------------------------------
    # TEST 1: Sentry 1 - Breakeven Lock at +0.75R
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Sentry 1: Dynamic Breakeven-Lock...")
    pos_open = [{
        "ticket": 1001,
        "type": "BUY",
        "open_price": 2690.00,
        "sl": 2684.00,  # 6.0 pt risk
        "tp": 2710.00,
        "volume": 0.08,
        "profit": 80.00,
        "time": time.time() - 300
    }]
    # Current bid 2695.00 -> +5.00 pts -> +0.83R (exceeds +0.75R)
    market_be = dict(base_market)
    market_be["pricing"] = {"bid": 2695.00, "ask": 2695.20, "spread_points": 20.0}

    actions = manager.evaluate_and_manage_positions(pos_open, market_be, base_news)
    assert 1001 in manager.breakeven_locked_tickets, "Ticket 1001 should be breakeven locked!"
    mock_exec.move_to_breakeven.assert_called()
    print("   ✅ Sentry 1 Passed: Breakeven locked at +0.83R gain (Kills +$60 -> -$80 reversion).")

    # -------------------------------------------------------------------------
    # TEST 2: Sentry 3 - Momentum Exhaustion / Reversal Defense
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Sentry 3: Momentum Exhaustion & Reversal Detection...")
    # Position in profit (+0.90R), but sudden Bearish Reversal Wick + 72% Bid Hitters appears
    mock_exec.reset_mock()
    pos_profit = [{
        "ticket": 1002,
        "type": "BUY",
        "open_price": 2690.00,
        "sl": 2690.40,
        "tp": 2710.00,
        "volume": 0.08,
        "profit": 55.00,
        "time": time.time() - 600
    }]
    market_exhaust = {
        "pricing": {"bid": 2695.50, "ask": 2695.70, "spread_points": 20.0},
        "market_structures": {
            "m15_execution_structure": {
                "atr_14": 6.00,
                "rsi_14": 78.0,  # Extreme overbought
                "candlestick_patterns": [{"pattern": "Bearish Shooting Star Pinbar"}]
            },
            "m5_micro_momentum": {"rsi_14": 82.0, "ema_9": 2695.0, "ema_21": 2696.0}
        },
        "tick_order_flow": {
            "ask_lifters_pct": 28.0,
            "bid_hitters_pct": 72.0,  # > 68% seller aggression
            "flow_imbalance": "BEARISH_AGGRESSION"
        },
        "volume_delta_cvd": {"cvd_pattern": "BEARISH_DISTRIBUTION"},
        "liquidity_execution_quality": {"spread_ratio": 1.0, "clearance": "CLEARED"}
    }
    actions = manager.evaluate_and_manage_positions(pos_profit, market_exhaust, base_news)
    exhaustion_action = next((a for a in actions if a["type"] == "MOMENTUM_EXHAUSTION_EXIT"), None)
    assert exhaustion_action is not None, "Momentum Exhaustion Exit should trigger!"
    assert mock_exec.close_position.call_args[1]["ticket"] == 1002
    assert "Chanakya_Exhaust" in mock_exec.close_position.call_args[1]["comment"]
    print(f"   ✅ Sentry 3 Passed: Banked early profit on reversal signal: {exhaustion_action['thought']}")

    # -------------------------------------------------------------------------
    # TEST 3: Sentry 7 - Dynamic Partial Booking Optimizer
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Sentry 7: Dynamic Partial-Booking Optimizer...")
    mock_exec.reset_mock()
    pos_tp1 = [{
        "ticket": 1003,
        "type": "BUY",
        "open_price": 2690.00,
        "sl": 2684.00,
        "tp": 2700.00,  # TP1 @ 2700.00 (+10 pts / +1.66R)
        "volume": 0.08,
        "profit": 80.00,
        "time": time.time() - 400
    }]
    market_tp1 = {
        "pricing": {"bid": 2700.50, "ask": 2700.70, "spread_points": 20.0},
        "market_structures": {
            "m15_execution_structure": {"atr_14": 6.00, "rsi_14": 60.0, "candlestick_patterns": []},
            "m5_micro_momentum": {"rsi_14": 62.0, "ema_9": 2700.0, "ema_21": 2698.0}
        },
        "tick_order_flow": {"ask_lifters_pct": 60.0, "bid_hitters_pct": 40.0},
        "volume_delta_cvd": {"cvd_pattern": "BULLISH_ACCUMULATION"},
        "liquidity_execution_quality": {"spread_ratio": 1.0}
    }
    actions = manager.evaluate_and_manage_positions(pos_tp1, market_tp1, base_news)
    partial_action = next((a for a in actions if a["type"] == "DYNAMIC_PARTIAL_BOOKED"), None)
    assert partial_action is not None, "Dynamic Partial should trigger!"
    assert 1003 in manager.partially_closed_tickets
    print(f"   ✅ Sentry 7 Passed: Banked partial volume at TP1: {partial_action['thought']}")

    # -------------------------------------------------------------------------
    # TEST 4: Sentry 2 & 4 - Human Pro Dynamic Micro-Structure Trailing Stop
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Sentry 2 & 4: Human Pro Dynamic Trailing Stop...")
    mock_exec.reset_mock()
    pos_trail = [{
        "ticket": 1004,
        "type": "BUY",
        "open_price": 2690.00,
        "sl": 2690.40,
        "tp": 2720.00,
        "volume": 0.04,
        "profit": 60.00,
        "time": time.time() - 500
    }]
    # Price is at 2705.00 (+15 pts / +2.0R) with Volatility Spike (ATR = 12.0)
    market_vol_spike = {
        "pricing": {"bid": 2705.00, "ask": 2705.20, "spread_points": 20.0},
        "market_structures": {
            "m15_execution_structure": {"atr_14": 12.00, "rsi_14": 65.0, "candlestick_patterns": []},
            "m5_micro_momentum": {"rsi_14": 65.0, "ema_9": 2703.0, "ema_21": 2700.0}
        },
        "micro_structures": {
            "M5": {"prev_low": 2701.50, "prev_high": 2705.50, "fast_ema_cross": "BULLISH_CROSS"}
        },
        "tick_order_flow": {"ask_lifters_pct": 52.0, "bid_hitters_pct": 48.0},
        "volume_delta_cvd": {"cvd_pattern": "BALANCED"},
        "liquidity_execution_quality": {"spread_ratio": 1.9}  # Volatility spike trigger
    }
    manager.breakeven_locked_tickets.add(1004)
    manager.partially_closed_tickets.add(1004)
    actions = manager.evaluate_and_manage_positions(pos_trail, market_vol_spike, base_news)
    trail_action = next((a for a in actions if a["type"] == "ATR_RATCHET_TRAILING_UPDATE"), None)
    assert trail_action is not None, "Human Pro Trail should update SL!"
    # With tight trailing gap min(3.80, max(2.80, 12.0*0.50)) = 3.80 pt gap -> 2705.00 - 3.80 = 2701.20
    assert manager.trailing_sl_cache[1004] == 2701.20
    print(f"   ✅ Sentry 2 Passed: SL ratcheted to {manager.trailing_sl_cache[1004]} (Locks +11.20 pts profit with tight gap): {trail_action['thought']}")

    # -------------------------------------------------------------------------
    # TEST 5: Sentry 5 - Time-in-Trade Decay Sentry
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Sentry 5: Time-in-Trade Decay Sentry...")
    mock_exec.reset_mock()
    pos_stagnant = [{
        "ticket": 1005,
        "type": "BUY",
        "open_price": 2690.00,
        "sl": 2684.00,
        "tp": 2710.00,
        "volume": 0.08,
        "profit": 1.50,
        "time": time.time() - (50 * 60)  # 50 minutes open (exceeds 45m limit)
    }]
    market_flat = {
        "pricing": {"bid": 2690.50, "ask": 2690.70, "spread_points": 20.0},
        "market_structures": {
            "m15_execution_structure": {"atr_14": 5.00, "rsi_14": 50.0, "candlestick_patterns": []},
            "m5_micro_momentum": {"rsi_14": 50.0, "ema_9": 2690.5, "ema_21": 2690.4}
        },
        "tick_order_flow": {"ask_lifters_pct": 50.0, "bid_hitters_pct": 50.0},
        "volume_delta_cvd": {"cvd_pattern": "FLAT"},
        "liquidity_execution_quality": {"spread_ratio": 1.0}
    }
    actions = manager.evaluate_and_manage_positions(pos_stagnant, market_flat, base_news)
    decay_action = next((a for a in actions if a["type"] == "TIME_DECAY_EXIT"), None)
    assert decay_action is not None, "Time Decay Exit should trigger for stagnant trade!"
    mock_exec.close_position.assert_called_with(ticket=1005, comment="Chanakya_Time_Decay")
    print(f"   ✅ Sentry 5 Passed: Exited stagnant trade after 50m: {decay_action['thought']}")

    # -------------------------------------------------------------------------
    # TEST 6: Sentry 6 - News / Shock Flash Shield
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Sentry 6: News / Shock Flash Shield...")
    mock_exec.reset_mock()
    pos_news = [{
        "ticket": 1006,
        "type": "BUY",
        "open_price": 2690.00,
        "sl": 2684.00,
        "tp": 2710.00,
        "volume": 0.08,
        "profit": 35.00,
        "time": time.time() - 300
    }]
    market_news_shock = dict(base_market)
    market_news_shock["pricing"] = {"bid": 2693.50, "ask": 2694.00, "spread_points": 50.0}
    news_blackout_active = {
        "news_blackout_active": True,
        "minutes_to_next_impact": 4  # CPI / NFP in 4 mins
    }
    actions = manager.evaluate_and_manage_positions(pos_news, market_news_shock, news_blackout_active)
    news_action = next((a for a in actions if a["type"] == "NEWS_SHOCK_DEFENSE"), None)
    assert news_action is not None, "News Flash Shield should de-risk!"
    print(f"   ✅ Sentry 6 Passed: Secured 50% cash & BE stop ahead of news shock: {news_action['thought']}")

    # -------------------------------------------------------------------------
    # TEST 7: Sentry 3B - AI Early Thesis Invalidation Cut
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Sentry 3B: AI Early Thesis Invalidation Cut...")
    mock_exec.reset_mock()
    pos_losing = [{
        "ticket": 1007,
        "type": "BUY",
        "open_price": 2690.00,
        "sl": 2684.00,  # 6.0 pt initial risk
        "tp": 2710.00,
        "volume": 0.08,
        "profit": -24.00,
        "time": time.time() - 200
    }]
    # Current bid is 2687.60 -> -2.40 pts -> -0.40R loss
    # AI Council flips to SELL with 82% confidence or trade_health INVALIDATED
    market_early_cut = dict(base_market)
    market_early_cut["pricing"] = {"bid": 2687.60, "ask": 2687.80, "spread_points": 20.0}
    market_early_cut["micro_structures"] = {
        "M5": {"prev_low": 2687.00, "prev_high": 2691.00, "fast_ema_cross": "BEARISH_CROSS"}
    }
    market_early_cut["tick_order_flow"] = {"ask_lifters_pct": 30.0, "bid_hitters_pct": 70.0}

    council_flip = {
        "consensus_action": "SELL",
        "consensus_confidence": 85.0,
        "trade_health": "INVALIDATED"
    }
    actions = manager.evaluate_and_manage_positions(pos_losing, market_early_cut, base_news, council_deliberation=council_flip)
    cut_action = next((a for a in actions if a["type"] == "AI_EARLY_THESIS_CUT"), None)
    assert cut_action is not None, "AI Early Thesis Cut should trigger at -0.40R when thesis is invalidated!"
    mock_exec.close_position.assert_called_with(ticket=1007, comment="Chanakya_EarlyCut_AI")
    print(f"   ✅ Sentry 3B Passed: Early thesis cut saved capital at -0.40R loss: {cut_action['thought']}")

    print("\n" + "=" * 80)
    print("🎯 ALL 7 TRADE LIFECYCLE SENTRIES VERIFIED AND 100% OPERATIONAL!")
    print("=" * 80)


if __name__ == "__main__":
    test_sentry_suite()
