"""
Unit tests for Phase 2:
- Staged Pipeline in MasterCoordinator (flag-controlled via CONFIG.PIPELINE_MODE)
- Stage 0 DailyPlan generation & D1/H4 conflict handling
- Stage 1 Permission Gates integration
- Stage 2 Location & Premium/Discount gating
- Stage 3 Trigger & Order flow validation
- Stage 4 CRO risk check and final TradePlan assembly
"""

import unittest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
import os
import sys

# Ensure d:\Ai Trading ALGO is in path
sys.path.insert(0, r"d:\Ai Trading ALGO")

from config import CONFIG
from agents.master_coordinator import MasterCoordinator
from core.trade_plan import DailyPlan, TradePlan, GateResult, KeyLevel, BlackoutWindow, TradeBias, TradeDirection


@contextmanager
def patch_config(**kwargs):
    """Safely overrides fields on frozen CONFIG dataclass."""
    originals = {k: getattr(CONFIG, k) for k in kwargs}
    for k, v in kwargs.items():
        object.__setattr__(CONFIG, k, v)
    try:
        yield
    finally:
        for k, v in originals.items():
            object.__setattr__(CONFIG, k, v)


class TestMasterCoordinatorStagedPipeline(unittest.TestCase):

    def setUp(self):
        self.coordinator = MasterCoordinator()

    def _mock_market_data(
        self,
        d1_trend="BEARISH",
        h4_trend="BEARISH",
        h4_regime="TRENDING_BEARISH",
        harmony_score=80.0,
        spread=8.0,
        live_price=4180.0,
        ask_lifters=40.0,
        bid_hitters=60.0,
        range_high=4250.0,
        range_low=4100.0,
        key_levels=None
    ):
        levels = key_levels or [
            {"high": 4182.0, "low": 4178.0, "mid": 4180.0}
        ]
        return {
            "pricing": {"bid": live_price, "ask": live_price + 0.8, "spread_points": spread},
            "account": {"balance": 5000.0, "equity": 5000.0},
            "multi_tf_patterns": {
                "harmony_score": harmony_score,
                "harmony_pct": harmony_score,
                "timeframes": {
                    "D1": {
                        "bias": d1_trend,
                        "institutional_meta": {"range_high": range_high, "range_low": range_low}
                    },
                    "H4": {"bias": h4_trend}
                }
            },
            "regime_analysis": {
                "regime": h4_regime,
                "h4_regime": h4_regime
            },
            "liquidity_execution_quality": {
                "clearance": "CLEAR_OPTIMAL"
            },
            "market_structures": {
                "m15_execution_structure": {"atr_14": 6.50},
                "supply_demand_zones": {"supply_zones": levels, "demand_zones": levels},
                "tick_order_flow": {"ask_lifters_pct": ask_lifters, "bid_hitters_pct": bid_hitters}
            }
        }

    def test_legacy_mode_fallback(self):
        """When PIPELINE_MODE == 'legacy', runs the legacy pipeline."""
        with patch_config(PIPELINE_MODE="legacy"):
            with patch.object(self.coordinator, "_run_legacy_pipeline") as mock_legacy:
                mock_legacy.return_value = {"action": "HOLD", "pipeline_mode": "legacy"}
                res = self.coordinator.run_council_deliberation(
                    market_data={"pricing": {}},
                    news_data={},
                    current_spread_points=8.0,
                    open_positions_count=0,
                    day_of_month=2
                )
                mock_legacy.assert_called_once()
                self.assertEqual(res.get("pipeline_mode"), "legacy")

    def test_stage0_d1_h4_conflict_blocks_trade(self):
        """When D1 is BULLISH and H4 is BEARISH, DailyPlan bias is NO_TRADE and deliberation returns HOLD."""
        with patch_config(PIPELINE_MODE="staged"):
            market_data = self._mock_market_data(d1_trend="BULLISH", h4_trend="BEARISH")
            self.coordinator.current_daily_plan = None  # Force fresh daily plan
            res = self.coordinator.run_council_deliberation(
                market_data=market_data,
                news_data={},
                current_spread_points=8.0,
                open_positions_count=0,
                day_of_month=2
            )
            self.assertEqual(res["action"], "HOLD")
            self.assertIn("Macro Disagreement", res["council_debate_summary"])

    def test_stage1_spread_gate_blocks_trade(self):
        """When spread exceeds MAX_SPREAD_POINTS, Stage 1 Gatekeeper blocks with LIQUIDITY veto."""
        with patch_config(PIPELINE_MODE="staged", MAX_SPREAD_POINTS=12.0):
            # Spread is 25.0 points
            market_data = self._mock_market_data(spread=25.0)
            self.coordinator.current_daily_plan = None
            res = self.coordinator.run_council_deliberation(
                market_data=market_data,
                news_data={},
                current_spread_points=25.0,
                open_positions_count=0,
                day_of_month=2
            )
            self.assertEqual(res["action"], "HOLD")
            self.assertIn("LIQUIDITY", res["council_debate_summary"])

    def test_stage2_mid_range_blocks_trade(self):
        """When live price is > 1.0 ATR away from any key level, Stage 2 blocks with LOCATION veto."""
        with patch_config(PIPELINE_MODE="staged"):
            # Price at 4180, key level far away at 4220 (40 pts > 6.5 ATR)
            market_data = self._mock_market_data(
                live_price=4180.0,
                key_levels=[{"high": 4225.0, "low": 4220.0, "mid": 4222.0}]
            )
            self.coordinator.current_daily_plan = None
            res = self.coordinator.run_council_deliberation(
                market_data=market_data,
                news_data={},
                current_spread_points=8.0,
                open_positions_count=0,
                day_of_month=2
            )
            self.assertEqual(res["action"], "HOLD")
            self.assertIn("mid-range", res["council_debate_summary"])

    def test_stage2_discount_blocks_short(self):
        """When price is in Discount zone (< 50% 20-day range), SELL is vetoed."""
        with patch_config(PIPELINE_MODE="staged"):
            # Live price 4110 in range 4100-4250 is ~6.6% (deep discount)
            market_data = self._mock_market_data(
                live_price=4110.0,
                range_high=4250.0,
                range_low=4100.0,
                key_levels=[{"high": 4112.0, "low": 4108.0, "mid": 4110.0}]
            )
            self.coordinator.current_daily_plan = None
            res = self.coordinator.run_council_deliberation(
                market_data=market_data,
                news_data={},
                current_spread_points=8.0,
                open_positions_count=0,
                day_of_month=2
            )
            self.assertEqual(res["action"], "HOLD")
            self.assertIn("Discount zone", res["council_debate_summary"])

    def test_stage3_insufficient_orderflow_hitters_blocks_short(self):
        """When proposing SELL, if bid_hitters < 55%, Stage 3 orderflow blocks trade."""
        with patch_config(PIPELINE_MODE="staged"):
            # Live price 4220 in range 4100-4250 is 80% (Premium, valid for sell)
            # But bid_hitters is only 45% (< 55%)
            market_data = self._mock_market_data(
                live_price=4220.0,
                range_high=4250.0,
                range_low=4100.0,
                ask_lifters=55.0,
                bid_hitters=45.0,
                key_levels=[{"high": 4222.0, "low": 4218.0, "mid": 4220.0}]
            )
            self.coordinator.current_daily_plan = None
            res = self.coordinator.run_council_deliberation(
                market_data=market_data,
                news_data={},
                current_spread_points=8.0,
                open_positions_count=0,
                day_of_month=2
            )
            self.assertEqual(res["action"], "HOLD")
            self.assertIn("bid-hitters", res["council_debate_summary"])

    def test_all_stages_pass_produces_trade_plan(self):
        """When all 4 stages pass, produces a complete SELL TradePlan."""
        with patch_config(PIPELINE_MODE="staged"):
            # Live price 4220, key level 4220, range 4100-4250 (80% Premium)
            # Bid hitters 68% (> 55%), harmony 80%
            market_data = self._mock_market_data(
                live_price=4220.0,
                range_high=4250.0,
                range_low=4100.0,
                ask_lifters=32.0,
                bid_hitters=68.0,
                key_levels=[{"high": 4222.0, "low": 4218.0, "mid": 4220.0}]
            )
            self.coordinator.current_daily_plan = None
            res = self.coordinator.run_council_deliberation(
                market_data=market_data,
                news_data={},
                current_spread_points=8.0,
                open_positions_count=0,
                day_of_month=2
            )
            self.assertEqual(res["action"], "SELL")
            self.assertIn("trade_plan", res)
            self.assertIsNotNone(res["trade_plan"])
            tp = res["trade_plan"]
            self.assertEqual(tp["direction"], "SELL")
            self.assertGreater(tp["stop_price"], tp["entry_price"])
            self.assertLess(tp["target_1"], tp["entry_price"])
            self.assertGreaterEqual(tp["rr"], 1.75)


if __name__ == "__main__":
    unittest.main()
