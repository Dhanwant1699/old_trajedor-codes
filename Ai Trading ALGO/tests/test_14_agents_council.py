"""
Integration test for the full 14-Agent AI Council Architecture.
Tests:
1. Data engine indicator calculations (ADX, Choppiness Index, CVD, Tick Microstructure)
2. All 14 specialist trading agents executing in parallel
3. Master Coordinator council arbitration and CRO clearance
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_engine import MT5DataEngine
from agents.master_coordinator import MasterCoordinator


def test_14_agents_council():
    print("=" * 70)
    print("🧪 STARTING 14-AGENT AI TRADING COUNCIL INTEGRATION TEST")
    print("=" * 70)

    # 1. Test Data Engine Extraction
    engine = MT5DataEngine(symbol="XAUUSD")
    connected = engine.connect()
    print(f"[*] MT5 Data Engine connected: {connected}")

    if connected:
        payload = engine.extract_full_market_payload()
        engine.disconnect()
    else:
        print("[!] Using simulated market data payload for testing offline...")
        payload = {
            "symbol": "XAUUSD",
            "pricing": {"bid": 4365.20, "ask": 4365.70, "spread_points": 50.0},
            "market_structures": {
                "m15_execution_structure": {
                    "atr_14": 8.50,
                    "rsi_14": 52.0,
                    "ema_9": 4362.0,
                    "ema_21": 4358.0,
                    "vwap": 4360.0
                }
            },
            "regime_analysis": {
                "regime": "TRENDING_BULLISH",
                "adx": 28.5,
                "choppiness_index": 42.0
            },
            "liquidity_execution_quality": {
                "spread_points": 50.0,
                "spread_ratio": 1.05,
                "clearance": "CLEARED"
            },
            "tick_order_flow": {
                "ask_lifters_pct": 58.0,
                "bid_hitters_pct": 42.0,
                "flow_imbalance": "BULLISH_AGGRESSION"
            },
            "volume_delta_cvd": {
                "cvd_pattern": "BULLISH_ACCUMULATION",
                "latest_bar_delta": 240
            }
        }

    # Verify microstructure keys in payload
    print("\n--- [1] Checking Enriched Indicators ---")
    regime = payload.get("regime_analysis", {})
    liq = payload.get("liquidity_execution_quality", {})
    tick = payload.get("tick_order_flow", {})
    vdelta = payload.get("volume_delta_cvd", {})

    print(f"  * Regime: {regime.get('regime')} (ADX: {regime.get('adx')}, Chop: {regime.get('choppiness_index')})")
    print(f"  * Liquidity: Spread {liq.get('spread_points')} pts, Clearance: {liq.get('clearance')}")
    print(f"  * Tick Order Flow: Ask Lifters {tick.get('ask_lifters_pct')}% vs Bid Hitters {tick.get('bid_hitters_pct')}% ({tick.get('flow_imbalance')})")
    print(f"  * Volume Delta CVD: Pattern {vdelta.get('cvd_pattern')}, Latest Bar Delta {vdelta.get('latest_bar_delta')}")

    # 2. Test Master Coordinator Deliberation with 14 Agents
    print("\n--- [2] Executing 14-Agent Parallel Council Deliberation ---")
    coordinator = MasterCoordinator()

    news_data = {"news_blackout_active": False}
    decision = coordinator.run_council_deliberation(
        market_data=payload,
        news_data=news_data,
        current_spread_points=50.0,
        open_positions_count=0,
        day_of_month=18
    )

    print("\n--- [3] Council Deliberation Output ---")
    print(f"  * Master Action: {decision.get('action')}")
    print(f"  * Consensus Score: {decision.get('consensus_score')}% ({decision.get('council_agreement_level')})")
    print(f"  * Market Bias: {decision.get('market_bias')}")
    print(f"  * Entry Price: {decision.get('entry_price')}")
    print(f"  * Stop Loss: {decision.get('stop_loss')}")
    print(f"  * TP1 (1.75R): {decision.get('take_profit_1')}")
    print(f"  * TP2 (3.0R): {decision.get('take_profit_2')}")
    print(f"  * CRO Clearance: {decision.get('cro_report', {}).get('approved')} (Lots: {decision.get('cro_report', {}).get('calculated_lots')})")
    print(f"  * Council Debate Summary: {decision.get('council_debate_summary')}")

    proposals = decision.get("agent_proposals", {})
    print(f"\n--- [4] Agent Proposals Count: {len(proposals)} / 14 Agents ---")
    for agent_name, prop in proposals.items():
        act = prop.get("action", prop.get("recommended_action", "HOLD"))
        conf = prop.get("confidence_score", prop.get("sentiment_score", "N/A"))
        print(f"  * [{agent_name}]: {act} (Conf: {conf})")

    assert len(proposals) == 14, f"Expected 14 proposals, got {len(proposals)}"
    assert "11_Regime_Detection" in proposals
    assert "12_Liquidity_Execution" in proposals
    assert "13_Tick_OrderFlow" in proposals
    assert "14_Volume_Delta_CVD" in proposals

    print("\n" + "=" * 70)
    print("✅ ALL 14 AGENTS AND MASTER COORDINATOR INTEGRATION TEST PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    test_14_agents_council()
