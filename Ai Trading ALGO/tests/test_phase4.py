"""
Unit Tests for Phase 4: Audit Decision Logging, Replay Engine, and Dashboard Stage Visualizer.
"""

import os
import sys
import unittest
import json
import tempfile
from unittest.mock import MagicMock, patch

# Ensure root codebase is in python path
sys.path.insert(0, r"d:\Ai Trading ALGO")

from config import CONFIG
from core.trade_plan import DailyPlan, KeyLevel, TradeBias, GateResult, TradeDirection, TradePlan
from core.ai_ledger import AITradeLedger
from scripts.replay_staged_pipeline import run_pipeline_replay, get_curated_replay_scenarios
from core.dashboard_server import get_staged_pipeline_status
from agents.master_coordinator import MasterCoordinator


class TestPhase4AuditLogging(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_log_file = os.path.join(self.temp_dir, "test_stage_decisions.json")

    def test_record_staged_decision_format(self):
        """AITradeLedger.record_staged_decision properly logs structured stage audit entries."""
        with patch("core.ai_ledger.DECISION_LOG_FILE", self.temp_log_file):
            with patch("core.ai_ledger.LEDGER_DIR", self.temp_dir):
                entry = AITradeLedger.record_staged_decision(
                    symbol="XAUUSD",
                    stage_reached=0,
                    status="VETOED",
                    failed_gate="MACRO_HARMONY",
                    reason="[STAGE 0 VETO]: D1 Bearish opposes H4 Bullish",
                    daily_plan={"d1_trend": "BEARISH", "h4_trend": "BULLISH", "bias": "STANDBY"},
                    live_price=2000.50
                )

                self.assertEqual(entry["symbol"], "XAUUSD")
                self.assertEqual(entry["stage_reached"], 0)
                self.assertEqual(entry["stage_name"], "STAGE_0_DAILY_PLAN")
                self.assertEqual(entry["status"], "VETOED")
                self.assertEqual(entry["failed_gate"], "MACRO_HARMONY")
                self.assertEqual(entry["live_price"], 2000.50)

                # Verify file persistence
                self.assertTrue(os.path.exists(self.temp_log_file))
                with open(self.temp_log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]["id"], entry["id"])

                # Verify retrieval
                recent = AITradeLedger.get_recent_staged_decisions(limit=10)
                self.assertEqual(len(recent), 1)
                self.assertEqual(recent[0]["stage_reached"], 0)


class TestPhase4ReplayEngine(unittest.TestCase):
    def test_curated_scenarios_coverage(self):
        """Verifies replay scenarios cover all 5 pipeline stages."""
        scenarios = get_curated_replay_scenarios()
        self.assertGreaterEqual(len(scenarios), 8)
        stages_covered = {sc.expected_stage_veto for sc in scenarios}
        self.assertEqual(stages_covered, {0, 1, 2, 3, 4})

    def test_replay_pipeline_execution_100_percent_compliance(self):
        """Replay runner executes all scenarios and achieves 100% rule compliance."""
        results = run_pipeline_replay(verbose=False)
        self.assertEqual(results["total_scenarios"], 8)
        self.assertEqual(results["accuracy_pct"], 100.0)
        self.assertEqual(results["compliant_count"], 8)
        # Stage counts
        self.assertEqual(results["stage_counts"][0], 1)  # Macro conflict
        self.assertEqual(results["stage_counts"][1], 2)  # News & Spread
        self.assertEqual(results["stage_counts"][2], 2)  # Location & Premium
        self.assertEqual(results["stage_counts"][3], 2)  # Order flow & Candle
        self.assertEqual(results["stage_counts"][4], 1)  # Pristine approved


class TestPhase4DashboardStageVisualizer(unittest.TestCase):
    def test_get_staged_pipeline_status_vetoed_stage_0(self):
        """get_staged_pipeline_status correctly marks Stage 0 VETOED when macro disagrees."""
        mock_state = {
            "symbols": {
                "XAUUSD": {
                    "master_action": "HOLD",
                    "debate_summary": "[STAGE 0 VETO]: Macro Disagreement — D1 (BEARISH) opposes H4 (NEUTRAL)",
                    "gate_result": {"passed": False, "failed_gate": "MACRO_HARMONY"},
                    "daily_plan": {"d1_trend": "BEARISH", "h4_trend": "NEUTRAL", "bias": "STANDBY"}
                }
            }
        }
        with patch("core.council_state.CouncilStateManager.get_state", return_value=mock_state):
            status = get_staged_pipeline_status("XAUUSD")
            self.assertEqual(status["symbol"], "XAUUSD")
            self.assertEqual(status["failed_gate"], "MACRO_HARMONY")
            stages = status["stages"]
            self.assertEqual(len(stages), 5)
            self.assertEqual(stages[0]["status"], "VETOED")
            self.assertEqual(stages[1]["status"], "STANDBY")

    def test_get_staged_pipeline_status_approved_stage_4(self):
        """get_staged_pipeline_status marks all stages PASSED/APPROVED on valid buy setup."""
        mock_state = {
            "symbols": {
                "XAUUSD": {
                    "master_action": "BUY",
                    "setup_status": "IN_TRADE",
                    "debate_summary": "[STAGED PIPELINE APPROVED]: All gates passed",
                    "gate_result": {"passed": True, "failed_gate": None},
                    "daily_plan": {"d1_trend": "BULLISH", "h4_trend": "BULLISH", "bias": "BUY_DIPS"},
                    "entry_zone_low": 2000.0,
                    "entry_zone_high": 2005.0,
                    "cro_lots": "0.10 Lots",
                    "cro_status": "APPROVED"
                }
            }
        }
        with patch("core.council_state.CouncilStateManager.get_state", return_value=mock_state):
            status = get_staged_pipeline_status("XAUUSD")
            stages = status["stages"]
            self.assertEqual(stages[0]["status"], "PASSED")
            self.assertEqual(stages[1]["status"], "PASSED")
            self.assertEqual(stages[2]["status"], "PASSED")
            self.assertEqual(stages[3]["status"], "PASSED")
            self.assertEqual(stages[4]["status"], "EXECUTED")


class TestPhase4CoordinatorAuditLogging(unittest.TestCase):
    def test_coordinator_logs_decision_on_stage_0_veto(self):
        """MasterCoordinator logs audit entry to AITradeLedger when Stage 0 vetoes."""
        coordinator = MasterCoordinator()
        coordinator.symbol = "XAUUSD"
        # Mock daily plan returning NO_TRADE
        no_trade_plan = DailyPlan(
            bias=TradeBias.NO_TRADE,
            d1_trend="BEARISH",
            h4_trend="BULLISH",
            h4_regime="CHOP",
            premium_discount_pct=50.0
        )
        coordinator._get_or_update_daily_plan = MagicMock(return_value=no_trade_plan)

        with patch("core.ai_ledger.AITradeLedger.record_staged_decision") as mock_log:
            decision = coordinator._run_staged_pipeline(
                market_data={"pricing": {"bid": 2000.0}},
                news_data={},
                current_spread_points=8.0,
                open_positions_count=0,
                day_of_month=2
            )
            self.assertEqual(decision["action"], "HOLD")
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            self.assertEqual(call_kwargs["stage_reached"], 0)
            self.assertEqual(call_kwargs["status"], "VETOED")
            self.assertEqual(call_kwargs["failed_gate"], "MACRO_HARMONY")


if __name__ == "__main__":
    unittest.main()
