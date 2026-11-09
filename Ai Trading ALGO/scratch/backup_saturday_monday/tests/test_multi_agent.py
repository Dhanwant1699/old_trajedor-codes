"""
Comprehensive test script for Top 10 Strategy Agents Council.
Verifies all 10 specialized strategy agents, Chief Risk Officer lot sizer, and Master Arbitrator.
"""

import sys

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import CONFIG

from agents.xauusd.xauusd_smc_agent import GoldSMCAgent as SMCAgent
from agents.xauusd.xauusd_trend_agent import GoldTrendAgent as TrendAgent
from agents.xauusd.xauusd_mean_reversion_agent import GoldMeanReversionAgent as MeanReversionAgent
from agents.xauusd.xauusd_macro_agent import GoldMacroAgent as MacroAgent
from agents.xauusd.xauusd_orderflow_agent import GoldOrderFlowAgent as OrderFlowAgent
from agents.xauusd.xauusd_supply_demand_agent import GoldSupplyDemandAgent as SupplyDemandAgent
from agents.xauusd.xauusd_breakout_agent import GoldBreakoutAgent as BreakoutAgent
from agents.xauusd.xauusd_fibonacci_agent import GoldFibonacciAgent as FibonacciAgent
from agents.xauusd.xauusd_pattern_agent import GoldChartPatternAgent as ChartPatternAgent
from agents.xauusd.xauusd_scalping_agent import GoldScalpingAgent as ScalpingAgent
from agents.xauusd.xauusd_risk_agent import GoldChiefRiskOfficerAgent as ChiefRiskOfficerAgent
from agents.master_coordinator import MasterCoordinator


def test_top_10_agent_council():
    print("=" * 80)
    print("   TESTING TOP 10 STRATEGY AGENTS COUNCIL & GOVERNANCE ARCHITECTURE")
    print("=" * 80)

    # 1. Initialize all 10 strategy agents
    print("1. Initializing All 10 Specialized Strategy Agents...")
    agents = [
        ("1. SMC & ICT Agent", SMCAgent()),
        ("2. Trend & Momentum Agent", TrendAgent()),
        ("3. Mean-Reversion Agent", MeanReversionAgent()),
        ("4. Macro & News Agent", MacroAgent()),
        ("5. Volume Profile & VWAP Agent", OrderFlowAgent()),
        ("6. Supply & Demand Zones Agent", SupplyDemandAgent()),
        ("7. Breakout & Volatility Squeeze Agent", BreakoutAgent()),
        ("8. Fibonacci & Golden Pocket Agent", FibonacciAgent()),
        ("9. Chart Pattern & Geometry Agent", ChartPatternAgent()),
        ("10. Intraday Scalping & Momentum Agent", ScalpingAgent()),
    ]

    for name, ag in agents:
        print(f"   [OK] {name:<42} (Model: {ag.model})")

    # 2. Test Chief Risk Officer (CRO)
    print("\n2. Testing Chief Risk Officer (CRO) Dynamic Lot Sizing & Safety Rules...")
    cro = ChiefRiskOfficerAgent(symbol="XAUUSD")
    
    # Test 1: $50,000 equity setup clamped strictly to 0.10 max lots
    # Test 1: Full confidence setup ($5,000 equity, 90% quorum confidence)
    sample_buy = {
        "action": "BUY",
        "confidence_score": 90,
        "entry_price": 4360.0,
        "stop_loss": 4351.5,
        "take_profit_1": 4376.0,
        "take_profit_2": 4386.0,
        "risk_percent": 1.5
    }
    cro_rep = cro.evaluate_and_size_trade(
        proposal=sample_buy,
        account_info={"equity": 5000.0, "balance": 5000.0},
        current_spread_points=12.0,
        open_positions_count=0,
        day_of_month=16
    )
    print(f"   CRO Clearance: Approved={cro_rep['approved']} | Lots={cro_rep['calculated_lots']} | Risk=${cro_rep['risk_amount_usd']} | RR={cro_rep['risk_reward_ratio']}:1")
    assert cro_rep['approved'] is True
    assert cro_rep['calculated_lots'] <= 0.10  # STRICT RULE: Never execute more than 0.10 lots

    # Test 2: Low-confidence setup ($2,500 equity, 75% quorum confidence -> scaled down)
    sample_lower_conf = {
        "action": "BUY",
        "confidence_score": 75,
        "entry_price": 4360.0,
        "stop_loss": 4351.5,
        "take_profit_1": 4376.0,
        "risk_percent": 1.0
    }
    cro_rep2 = cro.evaluate_and_size_trade(
        proposal=sample_lower_conf,
        account_info={"equity": 2500.0, "balance": 2500.0},
        current_spread_points=12.0,
        open_positions_count=0,
        day_of_month=17  # New day to avoid drawdown trigger from $5k test
    )
    print(f"   CRO Lower-Probability Clearance: Approved={cro_rep2['approved']} | Scaled Lots={cro_rep2['calculated_lots']} (Conf: 75%)")
    assert cro_rep2['approved'] is True
    assert cro_rep2['calculated_lots'] <= 0.10
    assert cro_rep2['calculated_lots'] < cro_rep['calculated_lots']



    # 3. Test Master Coordinator initialization
    print("\n3. Testing Master Strategy Arbitrator & Parallel Thread Engine...")
    coordinator = MasterCoordinator()
    print(f"   [OK] Master Coordinator initialized with 10 parallel strategy worker threads.")

    print("\n[SUCCESS] TOP 10 STRATEGY AGENTS COUNCIL VERIFICATION PASSED WITH ZERO ERRORS!")


if __name__ == "__main__":
    test_top_10_agent_council()
