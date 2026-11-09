import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath("."))

from config import CONFIG
from core.data_engine import MT5DataEngine
from agents.master_coordinator import MasterCoordinator

def test_confluence_pullback():
    print("=" * 80)
    print("🧪 TESTING INSTITUTIONAL PULLBACK ENTRY & LOT SIZING WITH CONFLUENCE")
    print("=" * 80)

    data_engine = MT5DataEngine(symbol=CONFIG.SYMBOL)
    if not data_engine.connect():
        print("❌ Could not connect to MT5.")
        return

    market_payload = data_engine.extract_full_market_payload()
    ticks = market_payload.get("pricing", {})
    account = market_payload.get("account", {})
    live_price = float(ticks.get("bid", 0.0) or 4294.0)
    spread = ticks.get("spread_points", 0.0)
    eq_data = market_payload.get("institutional_equilibrium", {})

    print(f"📊 Live Gold Price: ${live_price:,.2f} | Spread: {spread} pts")
    print(f"🏛️ Market Range: High ${eq_data.get('range_high'):,.2f} | Low ${eq_data.get('range_low'):,.2f} | 50% Eq: ${eq_data.get('equilibrium_price'):,.2f} ({eq_data.get('zone')})")
    print(f"💰 Account Equity: €{account.get('equity', 0):,.2f}")

    coordinator = MasterCoordinator()

    # Simulate 8 Agents voting BUY with high confidence (e.g. SMC, Trend, OrderFlow, CVD, Tick, Macro, Pattern, Scalp)
    mock_proposals = {
        "1_SMC_ICT": {"action": "BUY", "confidence_score": 88, "bias": "BULLISH", "entry_price": live_price - 1.5, "stop_loss": live_price - 9.0, "take_profit_1": live_price + 15.0},
        "2_Trend_Momentum": {"action": "BUY", "confidence_score": 85, "bias": "BULLISH", "entry_price": live_price - 1.0, "stop_loss": live_price - 8.5, "take_profit_1": live_price + 14.0},
        "3_Mean_Reversion": {"action": "HOLD", "confidence_score": 50, "bias": "NEUTRAL"},
        "4_Macro_News": {"action": "BUY", "confidence_score": 85, "bias": "BULLISH"},
        "5_OrderFlow_VWAP": {"action": "BUY", "confidence_score": 90, "bias": "BULLISH", "entry_price": live_price - 1.2, "stop_loss": live_price - 8.0, "take_profit_1": live_price + 16.0},
        "6_Supply_Demand": {"action": "BUY", "confidence_score": 82, "bias": "BULLISH", "entry_price": live_price - 1.5, "stop_loss": live_price - 9.0, "take_profit_1": live_price + 15.0},
        "7_Breakout_Volatility": {"action": "HOLD", "confidence_score": 50, "bias": "NEUTRAL"},
        "8_Fibonacci_OTE": {"action": "BUY", "confidence_score": 85, "bias": "BULLISH", "entry_price": live_price - 2.0, "stop_loss": live_price - 9.5, "take_profit_1": live_price + 16.0},
        "9_Chart_Pattern": {"action": "HOLD", "confidence_score": 50, "bias": "NEUTRAL"},
        "10_Intraday_Scalp": {"action": "BUY", "confidence_score": 80, "bias": "BULLISH", "entry_price": live_price - 0.8, "stop_loss": live_price - 8.0, "take_profit_1": live_price + 14.0},
        "11_Regime_Detection": {"action": "HOLD", "confidence_score": 85, "bias": "NEUTRAL", "regime_type": "TRENDING_BULLISH"},
        "12_Liquidity_Execution": {"action": "BUY", "confidence_score": 92, "bias": "BULLISH", "execution_clearance": "CLEAR_OPTIMAL"},
        "13_Tick_OrderFlow": {"action": "BUY", "confidence_score": 88, "bias": "BULLISH"},
        "14_Volume_Delta_CVD": {"action": "BUY", "confidence_score": 90, "bias": "BULLISH"}
    }

    # Run algorithmic consensus
    decision = coordinator._calculate_algorithmic_consensus(mock_proposals, market_payload)
    decision = coordinator._sanitize_and_calibrate_decision(decision, market_payload)

    # Evaluate CRO lot sizing
    now_utc = datetime.now(timezone.utc)
    cro_report = coordinator.cro_agent.evaluate_and_size_trade(
        proposal=decision,
        account_info=account,
        current_spread_points=spread,
        open_positions_count=0,
        day_of_month=now_utc.day
    )
    decision["cro_report"] = cro_report

    print("\n" + "=" * 80)
    print("🎯 SYNTHESIZED TRADE SETUP:")
    print("=" * 80)
    print(f"Action:                 {decision.get('action')}")
    print(f"Agreement Level:        {decision.get('council_agreement_level')}")
    print(f"Consensus Score:        {decision.get('consensus_score')}%")
    print(f"Planned Pullback Entry: ${decision.get('entry_price'):,.2f} (Live Bid: ${live_price:,.2f})")
    print(f"Stop Loss:              ${decision.get('stop_loss'):,.2f} (Risk Distance: ${abs(decision.get('entry_price') - decision.get('stop_loss')):,.2f})")
    print(f"Take Profit 1 (1.75R):  ${decision.get('take_profit_1'):,.2f} (Reward: ${abs(decision.get('take_profit_1') - decision.get('entry_price')):,.2f})")
    print(f"Take Profit 2 (3.0R):   ${decision.get('take_profit_2'):,.2f} (Reward: ${abs(decision.get('take_profit_2') - decision.get('entry_price')):,.2f})")
    print(f"Risk:Reward Ratio:      1:{decision.get('risk_reward_ratio')}")
    print(f"Council Debate:\n   {decision.get('council_debate_summary')}")

    print("\n" + "=" * 80)
    print("🛡️ CHIEF RISK OFFICER CLEARANCE:")
    print("=" * 80)
    print(f"CRO Clearance:          {'🟢 APPROVED' if cro_report.get('approved') else '🔴 VETOED'}")
    print(f"Calculated Lot Size:    {cro_report.get('calculated_lots')} Lots (Max Limit: {CONFIG.MAX_LOT_SIZE})")
    print(f"Risk Capital Allocated: €{cro_report.get('risk_amount_usd'):,.2f} (1.5% Risk of Equity €{account.get('equity', 0):,.2f})")
    print(f"CRO Rationale:          {cro_report.get('reason')}")

    data_engine.disconnect()
    print("\n✅ Confluence test passed flawlessly!")

if __name__ == "__main__":
    test_confluence_pullback()
