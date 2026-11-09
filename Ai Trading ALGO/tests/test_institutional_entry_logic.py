"""
Unit test for Institutional Equilibrium, Premium/Discount Gating, and Anti-Waterfall Confirmation.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pandas as pd
from core.data_engine import MT5DataEngine
from agents.master_coordinator import MasterCoordinator

def test_equilibrium_and_zones():
    d_eng = MT5DataEngine(symbol="XAUUSD")
    # Test swing range: low 4330.0, high 4350.0 -> Range = 20.0, Eq = 4340.0
    eq_data = d_eng.get_equilibrium_and_zones(current_price=4346.40, swing_high=4350.0, swing_low=4330.0)
    
    assert eq_data["equilibrium_price"] == 4340.0
    assert eq_data["range_pct"] == 82.0
    assert eq_data["zone"] == "EXTREME_PREMIUM"
    assert eq_data["buying_permitted"] is False
    assert eq_data["selling_permitted"] is True
    print("✅ test_equilibrium_and_zones passed: Extreme Premium correctly forbids buying!")

def test_waterfall_dump_filter():
    d_eng = MT5DataEngine(symbol="XAUUSD")
    # Verify method exists and runs
    res = d_eng.check_m1_sniper_trigger(
        planned_entry=4342.0,
        action="BUY",
        tolerance_points=2.0
    )
    assert isinstance(res, dict)
    print("✅ test_waterfall_dump_filter verified!")

def test_coordinator_equilibrium_gate():
    coord = MasterCoordinator()
    
    # Test algorithmic consensus when price is in EXTREME_PREMIUM
    market_data = {
        "pricing": {"bid": 4346.40, "ask": 4346.55, "spread_points": 15.0},
        "market_structures": {
            "m15_execution_structure": {
                "ema_9": 4345.0, "ema_21": 4346.0, "ema_50": 4344.0, "ema_200": 4335.0,
                "trend_bias": "BULLISH", "rsi_14": 74.0, "atr_14": 4.5,
                "swing_high": 4350.0, "swing_low": 4330.0
            },
            "m5_micro_momentum": {
                "ema_9": 4344.0, "ema_21": 4345.5,
                "fast_ema_cross": "BEARISH", "rsi_14": 68.0
            }
        },
        "institutional_equilibrium": {
            "zone": "EXTREME_PREMIUM",
            "range_pct": 82.0,
            "buying_permitted": False,
            "selling_permitted": True
        },
        "regime_analysis": {
            "regime": "TRENDING_BEARISH",
            "confidence": 85
        }
    }
    
    votes = {
        f"Agent_{i}": {"action": "BUY", "confidence_score": 85, "entry_price": 4345.0, "stop_loss": 4338.0, "take_profit": 4360.0}
        for i in range(8)
    }
    votes["11_Regime_Detection"] = {"action": "HOLD", "confidence_score": 88, "bias": "BEARISH", "regime_type": "TRENDING_BEARISH"}
    
    decision = coord._calculate_algorithmic_consensus(votes, market_data)
    action = decision["action"]
    summary = decision.get("council_debate_summary", "")
    
    # In TRENDING_BEARISH, buy votes are converted to HOLD (action must be HOLD)
    assert action == "HOLD"
    print(f"✅ test_coordinator_regime_veto passed: Action is HOLD despite 8 raw buy votes! (Regime Veto Active)")

    # Now test with neutral regime but EXTREME_PREMIUM buying forbidden
    market_data["regime_analysis"]["regime"] = "RANGING"
    votes_neutral = {
        f"Agent_{i}": {"action": "BUY", "confidence_score": 85, "entry_price": 4345.0, "stop_loss": 4338.0, "take_profit": 4360.0}
        for i in range(8)
    }
    votes_neutral["11_Regime_Detection"] = {"action": "HOLD", "confidence_score": 75, "bias": "NEUTRAL", "regime_type": "RANGING"}
    decision2 = coord._calculate_algorithmic_consensus(votes_neutral, market_data)
    assert decision2["action"] == "HOLD"
    assert "Institutional Auction Veto" in decision2.get("council_debate_summary", "")
    print(f"✅ test_coordinator_equilibrium_gate passed: Extreme Premium vetoes 8 BUY votes!")

if __name__ == "__main__":
    test_equilibrium_and_zones()
    test_waterfall_dump_filter()
    test_coordinator_equilibrium_gate()
    print("\n🎉 ALL INSTITUTIONAL PLANNING & VETO TESTS PASSED!")
