"""
Unit tests for Phase 1:
  - VoteValidator (confidence clamp, contradiction detection, invalidation price)
  - Gatekeeper (all 5 gates individually, plus the critical replay scenario)

Run with:
  python -m pytest tests/test_phase1_gates_and_validator.py -v
  OR
  python tests/test_phase1_gates_and_validator.py
"""

import sys
import os

# Make sure the project root is on the path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import from scratch copies (during Phase 1 before files are moved to core/)
scratch = os.path.join(os.path.dirname(__file__), "..", "scratch")
sys.path.insert(0, scratch)

import unittest

# Import the modules we're testing
try:
    from core.vote_validator import validate_agent_output, validate_with_retry
    from core.gatekeeper import Gatekeeper, build_snapshot_from_payload
    from core.trade_plan import GateResult, TradePlan, DailyPlan, TradeBias, TradeDirection, KeyLevel
except ModuleNotFoundError:
    from vote_validator import validate_agent_output, validate_with_retry
    from gatekeeper import Gatekeeper, build_snapshot_from_payload
    from trade_plan import GateResult, TradePlan, DailyPlan, TradeBias, TradeDirection, KeyLevel


# ============================================================
# ===  VOTE VALIDATOR TESTS                               ====
# ============================================================

class TestVoteValidatorConfidenceClamping(unittest.TestCase):
    """Task 1.2 - confidence clamping (fixes the 121% bug)"""

    def test_confidence_121_clamped_to_100(self):
        raw = {"vote": "BUY", "confidence": 121, "evidence": ["price above EMA 50"], "invalidation_price": 4100.0}
        result = validate_agent_output(raw, "test_agent", live_price=4200.0)
        self.assertEqual(result["confidence"], 100)
        self.assertTrue(result["valid"])

    def test_confidence_negative_clamped_to_0(self):
        raw = {"vote": "NO_SIGNAL", "confidence": -5, "evidence": [], "invalidation_price": 0.0}
        result = validate_agent_output(raw, "test_agent", live_price=4200.0)
        self.assertEqual(result["confidence"], 0)

    def test_confidence_in_range_unchanged(self):
        raw = {"vote": "BUY", "confidence": 78, "evidence": ["EMA 9 crossed above EMA 21"], "invalidation_price": 4100.0}
        result = validate_agent_output(raw, "test_agent", live_price=4200.0)
        self.assertEqual(result["confidence"], 78)

    def test_confidence_float_parsed(self):
        raw = {"vote": "BUY", "confidence": 85.7, "evidence": ["volume surge 1.5x avg"], "invalidation_price": 4100.0}
        result = validate_agent_output(raw, "test_agent", live_price=4200.0)
        self.assertEqual(result["confidence"], 85)


class TestVoteValidatorContradictions(unittest.TestCase):
    """Task 1.2 - contradiction detection (bearish pattern + BUY = INVALID, etc.)"""

    LIVE = 4200.0

    def test_shooting_star_plus_buy_is_invalid(self):
        raw = {
            "vote": "BUY",
            "confidence": 80,
            "evidence": ["Shooting Star candle formed at resistance", "volume above average"],
            "invalidation_price": 4100.0,
        }
        result = validate_agent_output(raw, "pattern_agent", live_price=self.LIVE)
        self.assertEqual(result["vote"], "INVALID")
        self.assertFalse(result["valid"])
        self.assertIn("Shooting Star", result["rejection_reason"])

    def test_rsi_74_plus_buy_is_invalid(self):
        raw = {
            "vote": "BUY",
            "confidence": 90,
            "evidence": ["RSI: 74.3 on M15", "price above EMA 50"],
            "invalidation_price": 4100.0,
        }
        result = validate_agent_output(raw, "mean_reversion_agent", live_price=self.LIVE)
        self.assertEqual(result["vote"], "INVALID")
        self.assertIn("RSI", result["rejection_reason"])

    def test_aggressive_selling_plus_buy_is_invalid(self):
        raw = {
            "vote": "BUY",
            "confidence": 70,
            "evidence": ["Aggressive selling: bid hitters 60.5%", "spread widening"],
            "invalidation_price": 4100.0,
        }
        result = validate_agent_output(raw, "tick_flow_agent", live_price=self.LIVE)
        self.assertEqual(result["vote"], "INVALID")
        self.assertFalse(result["valid"])

    def test_bearish_engulfing_plus_buy_is_invalid(self):
        raw = {
            "vote": "BUY",
            "confidence": 65,
            "evidence": ["Bearish Engulfing candle at H4 resistance zone"],
            "invalidation_price": 4100.0,
        }
        result = validate_agent_output(raw, "pattern_agent", live_price=self.LIVE)
        self.assertEqual(result["vote"], "INVALID")

    def test_valid_buy_no_contradiction(self):
        raw = {
            "vote": "BUY",
            "confidence": 75,
            "evidence": ["Hammer candle at demand zone 4180", "volume ratio 1.3x"],
            "invalidation_price": 4150.0,
        }
        result = validate_agent_output(raw, "pattern_agent", live_price=4200.0)
        self.assertEqual(result["vote"], "BUY")
        self.assertTrue(result["valid"])

    def test_valid_sell_no_contradiction(self):
        raw = {
            "vote": "SELL",
            "confidence": 82,
            "evidence": ["Evening Star at supply zone 4280", "RSI 71.2 on H4"],
            "invalidation_price": 4350.0,
        }
        result = validate_agent_output(raw, "pattern_agent", live_price=4220.0)
        self.assertEqual(result["vote"], "SELL")
        self.assertTrue(result["valid"])

    def test_no_signal_always_valid(self):
        raw = {"vote": "NO_SIGNAL", "confidence": 50, "evidence": [], "invalidation_price": 0.0}
        result = validate_agent_output(raw, "macro_agent", live_price=4200.0)
        self.assertEqual(result["vote"], "NO_SIGNAL")
        self.assertTrue(result["valid"])


class TestVoteValidatorInvalidationPrice(unittest.TestCase):
    """Task 1.2 - invalidation price must be on correct side of live_price"""

    LIVE = 4200.0

    def test_buy_invalidation_below_live_ok(self):
        raw = {"vote": "BUY", "confidence": 75, "evidence": ["demand zone 4150"], "invalidation_price": 4150.0}
        result = validate_agent_output(raw, "agent", live_price=self.LIVE)
        self.assertTrue(result["valid"])

    def test_buy_invalidation_above_live_is_invalid(self):
        raw = {"vote": "BUY", "confidence": 75, "evidence": ["trend up"], "invalidation_price": 4250.0}
        result = validate_agent_output(raw, "agent", live_price=self.LIVE)
        self.assertEqual(result["vote"], "INVALID")

    def test_sell_invalidation_above_live_ok(self):
        raw = {"vote": "SELL", "confidence": 75, "evidence": ["supply zone 4280"], "invalidation_price": 4280.0}
        result = validate_agent_output(raw, "agent", live_price=self.LIVE)
        self.assertTrue(result["valid"])

    def test_sell_invalidation_below_live_is_invalid(self):
        raw = {"vote": "SELL", "confidence": 75, "evidence": ["bearish trend"], "invalidation_price": 4150.0}
        result = validate_agent_output(raw, "agent", live_price=self.LIVE)
        self.assertEqual(result["vote"], "INVALID")

    def test_malformed_json_returns_no_signal(self):
        raw = "this is not json {"
        result = validate_agent_output(raw, "agent", live_price=self.LIVE)
        self.assertEqual(result["vote"], "NO_SIGNAL")


class TestVoteValidatorRetry(unittest.TestCase):
    """validate_with_retry falls back to NO_SIGNAL after 2 failures"""

    def test_retry_fallback_to_no_signal(self):
        call_count = [0]

        def bad_call():
            call_count[0] += 1
            # Returns a self-contradicting vote every time
            return {
                "vote": "BUY",
                "confidence": 80,
                "evidence": ["Shooting Star bearish candle"],
                "invalidation_price": 4100.0,
            }

        result = validate_with_retry(bad_call, "pattern_agent", live_price=4200.0)
        self.assertEqual(result["vote"], "NO_SIGNAL")
        self.assertEqual(call_count[0], 2)  # retried exactly once


# ============================================================
# ===  GATEKEEPER TESTS                                   ====
# ============================================================

def _base_snapshot(**overrides) -> dict:
    """Builds a default PASSING snapshot; override specific keys to test failures."""
    base = {
        "spread_points": 8.0,
        "execution_clearance": "CLEAR_OPTIMAL",
        "harmony_score": 80.0,
        "d1_trend": "BULLISH",
        "h4_trend": "BULLISH",
        "h4_regime": "TRENDING_BULLISH",
        "daily_dd_pct": 0.5,
        "open_positions_count": 0,
        "last_loss_utc": "",
        "blackout_windows": [],
        "news_blackout_active": False,
        "blackout_reason": "",
        "setup_type": "REVERSAL",
    }
    base.update(overrides)
    return base


class TestGatekeeperAllPass(unittest.TestCase):
    def setUp(self):
        self.gk = Gatekeeper()

    def test_all_gates_pass_for_buy(self):
        snap = _base_snapshot()
        result = self.gk.check_all(snap, "BUY")
        self.assertTrue(result.passed)
        self.assertIsNone(result.failed_gate)

    def test_all_gates_pass_for_sell_in_bearish_trend(self):
        snap = _base_snapshot(d1_trend="BEARISH", h4_trend="BEARISH", h4_regime="TRENDING_BEARISH")
        result = self.gk.check_all(snap, "SELL")
        self.assertTrue(result.passed)


class TestGatekeeperNewsBlackout(unittest.TestCase):
    def setUp(self):
        self.gk = Gatekeeper()

    def test_active_blackout_window_blocks(self):
        from datetime import timedelta
        now = __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc)
        start = (now - __import__("datetime").timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end   = (now + __import__("datetime").timedelta(minutes=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
        snap = _base_snapshot(blackout_windows=[{"start_utc": start, "end_utc": end, "event": "US CPI", "impact": "HIGH"}])
        result = self.gk.check_all(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "NEWS_BLACKOUT")

    def test_news_blackout_flag_blocks(self):
        snap = _base_snapshot(news_blackout_active=True, blackout_reason="FOMC in 10 min")
        result = self.gk.check_all(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "NEWS_BLACKOUT")

    def test_no_blackout_passes(self):
        snap = _base_snapshot()
        result = self.gk.gate_news_blackout(snap, "BUY")
        self.assertTrue(result.passed)


class TestGatekeeperLiquidity(unittest.TestCase):
    def setUp(self):
        self.gk = Gatekeeper()

    def test_wide_spread_blocks(self):
        snap = _base_snapshot(spread_points=25.0)
        result = self.gk.check_all(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "LIQUIDITY")

    def test_liquidity_blackout_blocks(self):
        snap = _base_snapshot(execution_clearance="LIQUIDITY_BLACKOUT")
        result = self.gk.check_all(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "LIQUIDITY")

    def test_acceptable_spread_passes(self):
        snap = _base_snapshot(spread_points=9.0)
        result = self.gk.gate_liquidity(snap, "BUY")
        self.assertTrue(result.passed)


class TestGatekeeperH4Regime(unittest.TestCase):
    def setUp(self):
        self.gk = Gatekeeper()

    def test_trending_bearish_vetoes_buy(self):
        snap = _base_snapshot(h4_regime="TRENDING_BEARISH")
        result = self.gk.gate_h4_regime(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "H4_REGIME")

    def test_trending_bullish_vetoes_sell(self):
        snap = _base_snapshot(h4_regime="TRENDING_BULLISH")
        result = self.gk.gate_h4_regime(snap, "SELL")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "H4_REGIME")

    def test_range_vetoes_breakout(self):
        snap = _base_snapshot(h4_regime="MEAN_REVERTING_RANGE", setup_type="BREAKOUT")
        result = self.gk.gate_h4_regime(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "H4_REGIME")

    def test_range_allows_reversal(self):
        snap = _base_snapshot(h4_regime="MEAN_REVERTING_RANGE", setup_type="REVERSAL")
        result = self.gk.gate_h4_regime(snap, "BUY")
        self.assertTrue(result.passed)


class TestGatekeeperMacroHarmony(unittest.TestCase):
    def setUp(self):
        self.gk = Gatekeeper()

    def test_low_harmony_blocks(self):
        snap = _base_snapshot(harmony_score=50.0)
        result = self.gk.gate_macro_harmony(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "MACRO_HARMONY")
        self.assertIn("50", result.reason)

    def test_d1_bearish_blocks_buy(self):
        snap = _base_snapshot(harmony_score=80.0, d1_trend="BEARISH")
        result = self.gk.gate_macro_harmony(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "MACRO_HARMONY")

    def test_h4_bearish_blocks_buy(self):
        snap = _base_snapshot(harmony_score=80.0, h4_trend="BEARISH")
        result = self.gk.gate_macro_harmony(snap, "BUY")
        self.assertFalse(result.passed)

    def test_d1_bullish_blocks_sell(self):
        snap = _base_snapshot(harmony_score=80.0, d1_trend="BULLISH")
        result = self.gk.gate_macro_harmony(snap, "SELL")
        self.assertFalse(result.passed)

    def test_sufficient_harmony_neutral_trends_passes(self):
        snap = _base_snapshot(harmony_score=75.0, d1_trend="NEUTRAL", h4_trend="NEUTRAL")
        result = self.gk.gate_macro_harmony(snap, "BUY")
        self.assertTrue(result.passed)


class TestGatekeeperAccountSafety(unittest.TestCase):
    def setUp(self):
        self.gk = Gatekeeper()

    def test_max_drawdown_blocks(self):
        snap = _base_snapshot(daily_dd_pct=3.5)
        result = self.gk.gate_account_safety(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "ACCOUNT_SAFETY")

    def test_max_open_trades_blocks(self):
        snap = _base_snapshot(open_positions_count=1)
        result = self.gk.gate_account_safety(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "ACCOUNT_SAFETY")

    def test_cooldown_blocks(self):
        from datetime import datetime, timezone, timedelta
        recent_loss = (datetime.now(tz=timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        snap = _base_snapshot(last_loss_utc=recent_loss)
        result = self.gk.gate_account_safety(snap, "BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "ACCOUNT_SAFETY")
        self.assertIn("cooldown", result.reason.lower())

    def test_cooldown_expired_passes(self):
        from datetime import datetime, timezone, timedelta
        old_loss = (datetime.now(tz=timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        snap = _base_snapshot(last_loss_utc=old_loss)
        result = self.gk.gate_account_safety(snap, "BUY")
        self.assertTrue(result.passed)


# ============================================================
# ===  CRITICAL REPLAY TEST — Today's Failed Trade Scenario ===
# ============================================================

class TestCriticalReplayScenario(unittest.TestCase):
    """
    Task 1.6: Replay test that feeds the EXACT scenario from today's failed trade
    (D1 bearish, harmony 50%, Lifters 39.5%/Hitters 60.5%, regime bullish on M15 not H4)
    and asserts the system returns NO_TRADE with the correct failed_gate named.

    This is the test that PROVES the new gatekeeper would have prevented the bad entry.
    """

    def setUp(self):
        self.gk = Gatekeeper()

    def test_todays_failed_scenario_blocked_at_harmony(self):
        """
        Scenario: AI entered BUY while:
        - D1 was BEARISH
        - M30, M15 were BEARISH
        - Harmony score was only 50%
        - Tick flow showed Ask-Lifters 39.5% (aggressive SELLING)
        Expected: BLOCKED at MACRO_HARMONY (harmony 50% < 70%)
        """
        snapshot = {
            "spread_points": 8.0,
            "execution_clearance": "CLEAR_OPTIMAL",
            "harmony_score": 50.0,          # TODAY: was only 50%
            "d1_trend": "BEARISH",          # TODAY: D1 was clearly bearish
            "h4_trend": "BULLISH",          # H4 disagreed (conflict)
            "h4_regime": "TRENDING_BULLISH",# Regime was computed on M15, not H4
            "daily_dd_pct": 0.5,
            "open_positions_count": 0,
            "last_loss_utc": "",
            "blackout_windows": [],
            "news_blackout_active": False,
            "setup_type": "REVERSAL",
        }

        result = self.gk.check_all(snapshot, direction="BUY")

        self.assertFalse(result.passed, "System should have returned NO_TRADE but PASSED all gates!")
        self.assertEqual(
            result.failed_gate, "MACRO_HARMONY",
            f"Expected failure at MACRO_HARMONY but got: {result.failed_gate}"
        )
        self.assertIn("50", result.reason, "Reason should mention the harmony score")

    def test_d1_bearish_blocks_buy_regardless_of_harmony(self):
        """
        Even if somehow harmony were 80%, D1=BEARISH must block a BUY.
        """
        snapshot = _base_snapshot(
            harmony_score=80.0,
            d1_trend="BEARISH",     # Explicit opposition
            h4_trend="BULLISH",
        )
        result = self.gk.check_all(snapshot, direction="BUY")
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_gate, "MACRO_HARMONY")

    def test_tick_flow_contradiction_caught_by_vote_validator(self):
        """
        Today the Tick Flow agent saw Lifters=39.5%, Hitters=60.5% (AGGRESSIVE_SELLING)
        but still voted BUY. The VoteValidator must catch this as INVALID.
        """
        raw_tick_vote = {
            "vote": "BUY",
            "confidence": 75,
            "evidence": [
                "aggressive selling: bid hitters 60.5%, lifters only 39.5%",
                "spread normal at 8 pts"
            ],
            "invalidation_price": 4170.0,
        }
        result = validate_agent_output(raw_tick_vote, "tick_flow_agent", live_price=4189.0)
        self.assertEqual(result["vote"], "INVALID",
            "TickFlow agent vote BUY with evidence of aggressive selling must be INVALID")
        self.assertFalse(result["valid"])

    def test_rsi_overbought_buy_vote_caught(self):
        """
        Mean-Reversion showed RSI=74.3 (overbought) but voted BUY. Must be INVALID.
        """
        raw = {
            "vote": "BUY",
            "confidence": 85,
            "evidence": ["RSI: 74.3 overbought on M15", "EMA cross bullish"],
            "invalidation_price": 4170.0,
        }
        result = validate_agent_output(raw, "mean_reversion_agent", live_price=4189.0)
        self.assertEqual(result["vote"], "INVALID")

    def test_bearish_shooting_star_buy_vote_caught(self):
        """
        Pattern agent detected BEARISH_SHOOTING_STAR but voted BUY. Must be INVALID.
        """
        raw = {
            "vote": "BUY",
            "confidence": 80,
            "evidence": ["Shooting Star bearish candle on M15 resistance"],
            "invalidation_price": 4170.0,
        }
        result = validate_agent_output(raw, "pattern_agent", live_price=4189.0)
        self.assertEqual(result["vote"], "INVALID")


# ============================================================
# ===  TRADE PLAN DATACLASS TESTS                        ====
# ============================================================

class TestTradePlanValidation(unittest.TestCase):
    """Task 1.3 - TradePlan validation logic"""

    def _make_buy_plan(self, **overrides):
        defaults = dict(
            direction=TradeDirection.BUY,
            entry_zone_low=4180.0,
            entry_zone_high=4185.0,
            entry_price=4183.0,
            stop_price=4174.0,
            target_1=4199.0,
            target_2=4215.0,
            rr=1.78,
            invalidation_reason="M15 close below 4174",
            source_setup="H4_SUPPLY_ZONE + OTE_0618",
        )
        defaults.update(overrides)
        return TradePlan(**defaults)

    def test_valid_buy_plan(self):
        plan = self._make_buy_plan()
        self.assertTrue(plan.is_valid(min_rr=1.75))

    def test_insufficient_rr_invalid(self):
        plan = self._make_buy_plan(rr=1.50)
        self.assertFalse(plan.is_valid(min_rr=1.75))

    def test_wrong_price_order_invalid(self):
        # SL above entry is wrong for BUY
        plan = self._make_buy_plan(stop_price=4195.0)
        self.assertFalse(plan.is_valid())

    def test_risk_distance(self):
        plan = self._make_buy_plan(entry_price=4183.0, stop_price=4174.0)
        self.assertAlmostEqual(plan.risk_distance(), 9.0)

    def test_chase_distance(self):
        plan = self._make_buy_plan(entry_price=4183.0)
        self.assertAlmostEqual(plan.chase_distance(4187.0), 4.0)


# ============================================================
# ===  RUN TESTS                                         ====
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 1 Unit Tests — Gatekeeper + VoteValidator + TradePlan")
    print("=" * 70)
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
