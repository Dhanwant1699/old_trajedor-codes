"""
Unit Tests for Phase 3: M5 Closed Candle Confirmation, Microstructure Order Flow,
No-Chase Guard (0.3 ATR limit), and Limit Order Execution.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure root codebase is in python path
sys.path.insert(0, r"d:\Ai Trading ALGO")

import pandas as pd
import numpy as np

from config import CONFIG
from core.trade_plan import TradeDirection, TradePlan, GateResult
from core.trigger_engine import M5TriggerEngine
from core.execution_engine import MT5ExecutionEngine
from core.dual_account_manager import DualAccountManager, AccountProfile


def create_mock_m5_df(candles: list) -> pd.DataFrame:
    """
    Creates a mock M5 DataFrame from a list of dicts.
    Each dict has: open, high, low, close, tick_volume (or volume).
    """
    rows = []
    for c in candles:
        rows.append({
            "open": float(c.get("open", 2000.0)),
            "high": float(c.get("high", 2005.0)),
            "low": float(c.get("low", 1995.0)),
            "close": float(c.get("close", 2002.0)),
            "tick_volume": float(c.get("tick_volume", 100.0)),
        })
    return pd.DataFrame(rows)


def create_baseline_m5_df(count: int = 25, avg_vol: float = 100.0) -> pd.DataFrame:
    """Creates a baseline DataFrame of count candles with uniform volume."""
    candles = []
    for i in range(count):
        candles.append({
            "open": 2000.0,
            "high": 2004.0,
            "low": 1996.0,
            "close": 2001.0,
            "tick_volume": avg_vol
        })
    return create_mock_m5_df(candles)


class TestPhase3TriggerEngine(unittest.TestCase):
    def setUp(self):
        self.engine = M5TriggerEngine(
            max_chase_atr=0.30,
            min_lifters_pct=55.0,
            min_hitters_pct=55.0,
            min_vol_mult=1.25,
            min_wick_ratio=0.40
        )

    # --- 1. No-Chase Rule Tests ---
    def test_no_chase_within_band(self):
        """Live price within 0.30 * ATR passes."""
        atr = 10.0  # max chase = 3.0 pts
        planned_entry = 2000.0
        live_price = 2002.5  # 2.5 pts away <= 3.0 pts
        ok, reason, dist = self.engine.check_no_chase(live_price, planned_entry, atr)
        self.assertTrue(ok)
        self.assertAlmostEqual(dist, 2.5)

    def test_no_chase_violation(self):
        """Live price drifted > 0.30 * ATR is strictly rejected."""
        atr = 10.0  # max chase = 3.0 pts
        planned_entry = 2000.0
        live_price = 2003.8  # 3.8 pts away > 3.0 pts
        ok, reason, dist = self.engine.check_no_chase(live_price, planned_entry, atr)
        self.assertFalse(ok)
        self.assertIn("No-Chase Violation", reason)
        self.assertAlmostEqual(dist, 3.8)

    # --- 2. Microstructure Order Flow Imbalance Tests ---
    def test_order_flow_buy_pass(self):
        """BUY with lifters >= 55% and hitters < 60% passes."""
        flow = {"ask_lifters_pct": 58.0, "bid_hitters_pct": 42.0}
        ok, reason = self.engine.check_order_flow(flow, "BUY")
        self.assertTrue(ok)

    def test_order_flow_buy_fail_low_lifters(self):
        """BUY with lifters < 55% fails."""
        flow = {"ask_lifters_pct": 52.0, "bid_hitters_pct": 48.0}
        ok, reason = self.engine.check_order_flow(flow, "BUY")
        self.assertFalse(ok)
        self.assertIn("Insufficient buy aggressors", reason)

    def test_order_flow_buy_fail_heavy_sellers(self):
        """BUY with opposing bid-hitters >= 60% is vetoed."""
        flow = {"ask_lifters_pct": 56.0, "bid_hitters_pct": 62.0}
        ok, reason = self.engine.check_order_flow(flow, "BUY")
        self.assertFalse(ok)
        self.assertIn("Opposing aggressive selling", reason)

    def test_order_flow_sell_pass(self):
        """SELL with hitters >= 55% and lifters < 60% passes."""
        flow = {"ask_lifters_pct": 40.0, "bid_hitters_pct": 60.0}
        ok, reason = self.engine.check_order_flow(flow, "SELL")
        self.assertTrue(ok)

    def test_order_flow_sell_fail_low_hitters(self):
        """SELL with hitters < 55% fails."""
        flow = {"ask_lifters_pct": 48.0, "bid_hitters_pct": 52.0}
        ok, reason = self.engine.check_order_flow(flow, "SELL")
        self.assertFalse(ok)
        self.assertIn("Insufficient sell aggressors", reason)

    def test_order_flow_sell_fail_heavy_buyers(self):
        """SELL with opposing ask-lifters >= 60% is vetoed."""
        flow = {"ask_lifters_pct": 65.0, "bid_hitters_pct": 56.0}
        ok, reason = self.engine.check_order_flow(flow, "SELL")
        self.assertFalse(ok)
        self.assertIn("Opposing aggressive buying", reason)

    # --- 3. Closed M5 Candle Confirmation Pattern Tests ---
    def test_bullish_engulfing_confirmed(self):
        """Bullish engulfing candle with >= 1.25x volume passes confirmation."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # iloc[-3] (prior closed): bearish candle 2002 -> 1998
        df.loc[len(df)-3] = {"open": 2002.0, "high": 2003.0, "low": 1997.0, "close": 1998.0, "tick_volume": 100.0}
        # iloc[-2] (last closed): bullish engulfing 1997 -> 2004 with 150 volume (1.5x)
        df.loc[len(df)-2] = {"open": 1997.0, "high": 2005.0, "low": 1996.0, "close": 2004.0, "tick_volume": 150.0}
        # iloc[-1] (active forming candle)
        df.loc[len(df)-1] = {"open": 2004.0, "high": 2005.0, "low": 2003.0, "close": 2004.5, "tick_volume": 20.0}

        ok, reason, meta = self.engine.check_closed_candle_confirmation(df, "BUY", 1995.0, 2005.0)
        self.assertTrue(ok)
        self.assertEqual(meta["pattern_name"], "BULLISH_ENGULFING")
        self.assertGreaterEqual(meta["volume_ratio"], 1.25)

    def test_bullish_pinbar_hammer_confirmed(self):
        """Hammer with lower rejection wick >= 40% and volume >= 1.25x passes."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # iloc[-2]: open=2000, high=2002, low=1990 (wick=10 pts on 12 pt range = 83%), close=2001
        df.loc[len(df)-2] = {"open": 2000.0, "high": 2002.0, "low": 1990.0, "close": 2001.0, "tick_volume": 140.0}
        df.loc[len(df)-1] = {"open": 2001.0, "high": 2003.0, "low": 2000.0, "close": 2002.0, "tick_volume": 10.0}

        ok, reason, meta = self.engine.check_closed_candle_confirmation(df, "BUY", 1990.0, 2005.0)
        self.assertTrue(ok)
        self.assertIn("BULLISH_PINBAR_HAMMER", meta["pattern_name"])
        self.assertGreaterEqual(meta["lower_wick_ratio"], 0.40)

    def test_bullish_mss_choch_confirmed(self):
        """CHoCH / MSS closing above prior high with volume passes."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # iloc[-3]: high = 2002.0
        df.loc[len(df)-3] = {"open": 2000.0, "high": 2002.0, "low": 1998.0, "close": 2001.0, "tick_volume": 100.0}
        # iloc[-2]: close = 2005.0 > prev_high
        df.loc[len(df)-2] = {"open": 2001.0, "high": 2006.0, "low": 2000.0, "close": 2005.0, "tick_volume": 135.0}
        df.loc[len(df)-1] = {"open": 2005.0, "high": 2006.0, "low": 2004.0, "close": 2005.5, "tick_volume": 15.0}

        ok, reason, meta = self.engine.check_closed_candle_confirmation(df, "BUY", 1995.0, 2010.0)
        self.assertTrue(ok)
        self.assertEqual(meta["pattern_name"], "BULLISH_MSS_CHOCH")

    def test_bearish_engulfing_confirmed(self):
        """Bearish engulfing candle with >= 1.25x volume passes confirmation."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # iloc[-3]: bullish candle 1998 -> 2002
        df.loc[len(df)-3] = {"open": 1998.0, "high": 2003.0, "low": 1997.0, "close": 2002.0, "tick_volume": 100.0}
        # iloc[-2]: bearish engulfing 2003 -> 1996 with 160 volume
        df.loc[len(df)-2] = {"open": 2003.0, "high": 2004.0, "low": 1995.0, "close": 1996.0, "tick_volume": 160.0}
        df.loc[len(df)-1] = {"open": 1996.0, "high": 1997.0, "low": 1995.0, "close": 1995.5, "tick_volume": 20.0}

        ok, reason, meta = self.engine.check_closed_candle_confirmation(df, "SELL", 1990.0, 2010.0)
        self.assertTrue(ok)
        self.assertEqual(meta["pattern_name"], "BEARISH_ENGULFING")

    def test_bearish_shooting_star_confirmed(self):
        """Shooting star with upper rejection wick >= 40% and volume >= 1.25x passes."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # iloc[-2]: open=2000, high=2012, low=1999 (upper wick=12 pts on 13 pt range = 92%), close=1999.5
        df.loc[len(df)-2] = {"open": 2000.0, "high": 2012.0, "low": 1999.0, "close": 1999.5, "tick_volume": 130.0}
        df.loc[len(df)-1] = {"open": 1999.5, "high": 2000.0, "low": 1998.0, "close": 1999.0, "tick_volume": 10.0}

        ok, reason, meta = self.engine.check_closed_candle_confirmation(df, "SELL", 1995.0, 2015.0)
        self.assertTrue(ok)
        self.assertIn("BEARISH_SHOOTING_STAR", meta["pattern_name"])
        self.assertGreaterEqual(meta["upper_wick_ratio"], 0.40)

    def test_candle_fails_volume_threshold(self):
        """Valid pattern with volume < 1.25x rolling average fails confirmation."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # Bullish engulfing, but volume is only 90 (0.90x < 1.25x)
        df.loc[len(df)-3] = {"open": 2002.0, "high": 2003.0, "low": 1998.0, "close": 1999.0, "tick_volume": 100.0}
        df.loc[len(df)-2] = {"open": 1998.0, "high": 2004.0, "low": 1997.0, "close": 2003.0, "tick_volume": 90.0}
        df.loc[len(df)-1] = {"open": 2003.0, "high": 2004.0, "low": 2002.0, "close": 2003.5, "tick_volume": 10.0}

        ok, reason, meta = self.engine.check_closed_candle_confirmation(df, "BUY", 1995.0, 2005.0)
        self.assertFalse(ok)
        self.assertIn("volume", reason.lower())
        self.assertFalse(meta["vol_confirmed"])

    def test_candle_fails_zone_touch(self):
        """Valid pattern outside planned zone fails confirmation."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # Candle is high above zone (high=2050, low=2040, zone is 2000-2010)
        df.loc[len(df)-3] = {"open": 2045.0, "high": 2046.0, "low": 2041.0, "close": 2042.0, "tick_volume": 100.0}
        df.loc[len(df)-2] = {"open": 2041.0, "high": 2048.0, "low": 2040.0, "close": 2047.0, "tick_volume": 150.0}
        df.loc[len(df)-1] = {"open": 2047.0, "high": 2048.0, "low": 2046.0, "close": 2047.5, "tick_volume": 10.0}

        ok, reason, meta = self.engine.check_closed_candle_confirmation(df, "BUY", 2000.0, 2010.0)
        self.assertFalse(ok)
        self.assertIn("did not test planned zone", reason)

    # --- 4. Unified Full Trigger Engine Evaluation ---
    def test_evaluate_full_trigger_all_passed(self):
        """All Stage 3 conditions passed -> MARKET_OR_LIMIT trigger ready."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        df.loc[len(df)-3] = {"open": 2002.0, "high": 2003.0, "low": 1998.0, "close": 1999.0, "tick_volume": 100.0}
        df.loc[len(df)-2] = {"open": 1998.0, "high": 2005.0, "low": 1997.0, "close": 2004.0, "tick_volume": 150.0}
        df.loc[len(df)-1] = {"open": 2004.0, "high": 2005.0, "low": 2003.0, "close": 2004.5, "tick_volume": 10.0}

        flow = {"ask_lifters_pct": 58.0, "bid_hitters_pct": 42.0}
        res = self.engine.evaluate_full_trigger(
            df_m5=df,
            tick_flow_data=flow,
            live_price=2003.0,
            planned_entry=2002.0,
            direction="BUY",
            atr=8.0,
            entry_zone_low=1995.0,
            entry_zone_high=2005.0
        )
        self.assertTrue(res["trigger_ready"])
        self.assertEqual(res["order_type"], "MARKET_OR_LIMIT")
        self.assertIsNone(res["failed_check"])

    def test_evaluate_full_trigger_candle_unconfirmed_gives_limit_only(self):
        """No-chase and flow pass, but candle not yet confirmed -> returns LIMIT_ONLY."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        # Red candle with no hammer
        df.loc[len(df)-2] = {"open": 2003.0, "high": 2004.0, "low": 1998.0, "close": 1999.0, "tick_volume": 100.0}
        df.loc[len(df)-1] = {"open": 1999.0, "high": 2000.0, "low": 1998.0, "close": 1999.5, "tick_volume": 10.0}

        flow = {"ask_lifters_pct": 58.0, "bid_hitters_pct": 42.0}
        res = self.engine.evaluate_full_trigger(
            df_m5=df,
            tick_flow_data=flow,
            live_price=2000.0,
            planned_entry=2000.0,
            direction="BUY",
            atr=8.0,
            entry_zone_low=1995.0,
            entry_zone_high=2005.0
        )
        self.assertFalse(res["trigger_ready"])
        self.assertEqual(res["failed_check"], "CLOSED_M5_CANDLE")
        self.assertEqual(res["order_type"], "LIMIT_ONLY")

    def test_evaluate_full_trigger_no_chase_blocks_everything(self):
        """Price drifted > 0.30 * ATR blocks execution completely (order_type=NONE)."""
        df = create_baseline_m5_df(25, avg_vol=100.0)
        flow = {"ask_lifters_pct": 58.0, "bid_hitters_pct": 42.0}
        res = self.engine.evaluate_full_trigger(
            df_m5=df,
            tick_flow_data=flow,
            live_price=2015.0,  # 15 pts away on 8.0 ATR (max allowed 2.4 pts)
            planned_entry=2000.0,
            direction="BUY",
            atr=8.0
        )
        self.assertFalse(res["trigger_ready"])
        self.assertEqual(res["failed_check"], "NO_CHASE")
        self.assertEqual(res["order_type"], "NONE")


class TestPhase3ExecutionEngine(unittest.TestCase):
    def test_send_limit_order_mock(self):
        """MT5ExecutionEngine.send_limit_order constructs correct TRADE_ACTION_PENDING request."""
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_PENDING = 5
        mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
        mock_mt5.ORDER_TYPE_SELL_LIMIT = 3
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_sym_info = MagicMock()
        mock_sym_info.digits = 2
        mock_sym_info.volume_min = 0.01
        mock_sym_info.volume_max = 50.0
        mock_sym_info.volume_step = 0.01
        mock_sym_info.filling_mode = 2
        mock_mt5.symbol_info.return_value = mock_sym_info

        mock_order_res = MagicMock()
        mock_order_res.retcode = 10009
        mock_order_res.order = 998877
        mock_mt5.order_send.return_value = mock_order_res

        with patch("core.execution_engine.mt5", mock_mt5):
            with patch("core.ai_ledger.AITradeLedger.record_executed_trade"):
                engine = MT5ExecutionEngine(symbol="XAUUSD", magic_number=777)
                success, msg, order_id = engine.send_limit_order(
                    action="BUY",
                    volume=0.10,
                    price=2000.50,
                    sl=1995.00,
                    tp=2010.00,
                    comment="Chanakya_Test_Limit"
                )
                self.assertTrue(success)
                self.assertEqual(order_id, 998877)
                mock_mt5.order_send.assert_called_once()
                sent_req = mock_mt5.order_send.call_args[0][0]
                self.assertEqual(sent_req["action"], mock_mt5.TRADE_ACTION_PENDING)
                self.assertEqual(sent_req["type"], mock_mt5.ORDER_TYPE_BUY_LIMIT)
                self.assertEqual(sent_req["price"], 2000.50)
                self.assertEqual(sent_req["sl"], 1995.00)
                self.assertEqual(sent_req["tp"], 2010.00)

    def test_cancel_pending_order_mock(self):
        """MT5ExecutionEngine.cancel_pending_order removes pending order via TRADE_ACTION_REMOVE."""
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_REMOVE = 8
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_mt5.order_send.return_value = mock_res

        with patch("core.execution_engine.mt5", mock_mt5):
            engine = MT5ExecutionEngine(symbol="XAUUSD", magic_number=777)
            success, msg = engine.cancel_pending_order(998877)
            self.assertTrue(success)
            mock_mt5.order_send.assert_called_once()
            sent_req = mock_mt5.order_send.call_args[0][0]
            self.assertEqual(sent_req["action"], mock_mt5.TRADE_ACTION_REMOVE)
            self.assertEqual(sent_req["order"], 998877)


class TestPhase3DualAccountLimitOrder(unittest.TestCase):
    def test_execute_dual_sniper_limit_order_mode(self):
        """DualAccountManager correctly places pending limit order when order_type is LIMIT_ONLY."""
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_PENDING = 5
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY_LIMIT = 2
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_acc_info = MagicMock()
        mock_acc_info.equity = 10000.0
        mock_acc_info.margin_free = 8000.0
        mock_acc_info.trade_allowed = True
        mock_mt5.account_info.return_value = mock_acc_info

        mock_term_info = MagicMock()
        mock_term_info.trade_allowed = True
        mock_mt5.terminal_info.return_value = mock_term_info

        mock_tick = MagicMock()
        mock_tick.bid = 2001.0
        mock_tick.ask = 2001.3
        mock_mt5.symbol_info_tick.return_value = mock_tick
        mock_mt5.positions_get.return_value = []

        mock_order_res = MagicMock()
        mock_order_res.retcode = 10009
        mock_order_res.order = 112233
        mock_order_res.deal = 112233
        mock_mt5.order_send.return_value = mock_order_res

        with patch("core.dual_account_manager.mt5", mock_mt5):
            with patch("core.dual_account_manager.AITradeLedger"):
                mgr = DualAccountManager(symbol="XAUUSD")
                test_profile = AccountProfile(
                    account_id="1",
                    name="TestAccount",
                    terminal_path="p",
                    currency="USD",
                    magic_number=111,
                    mode="STANDARD",
                    is_active=True,
                    max_open_trades=1,
                    max_lot_size=0.10,
                    min_lot_size=0.01,
                    min_free_margin=100.0
                )
                test_profile.connect = lambda: True
                test_profile.shutdown = lambda: None
                mgr.reload_config = lambda: None
                mgr.accounts = [test_profile]

                sniper_state = {
                    "order_type": "LIMIT_ONLY",
                    "trigger_ready": False,
                    "planned_entry": 2000.0
                }

                results = mgr.execute_dual_sniper_signal(
                    action="BUY",
                    entry_price=2000.0,
                    stop_loss=1995.0,
                    take_profit=2010.0,
                    consensus_score=85,
                    sniper_state=sniper_state
                )

                self.assertEqual(len(results), 1)
                self.assertTrue(results[0]["success"])
                self.assertEqual(results[0]["order_mode"], "LIMIT_ONLY")

                sent_req = mock_mt5.order_send.call_args[0][0]
                self.assertEqual(sent_req["action"], mock_mt5.TRADE_ACTION_PENDING)
                self.assertEqual(sent_req["type"], mock_mt5.ORDER_TYPE_BUY_LIMIT)
                self.assertEqual(sent_req["price"], 2000.0)


if __name__ == "__main__":
    unittest.main()
