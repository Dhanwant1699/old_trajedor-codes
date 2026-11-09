import sys
import os
import json
import time
from datetime import datetime, timezone

# Ensure path
sys.path.insert(0, os.path.abspath("."))

from config import CONFIG
from core.data_engine import MT5DataEngine
from core.news_engine import ForexNewsEngine
from agents.master_coordinator import MasterCoordinator

def test_council():
    print("=" * 80)
    print("🚀 TESTING LIVE 14-AGENT COUNCIL & REAL-TIME COMMUNICATION")
    print("=" * 80)

    # 1. Connect MT5 Data Engine
    data_engine = MT5DataEngine(symbol=CONFIG.SYMBOL)
    if not data_engine.connect():
        print("❌ Failed to connect to MT5 Data Engine.")
        return

    print("✅ MT5 Data Engine Connected successfully!")
    market_payload = data_engine.extract_full_market_payload()
    ticks = market_payload.get("pricing", {})
    account = market_payload.get("account", {})
    current_price = float(ticks.get("bid", 0.0) or 0.0)
    spread = ticks.get("spread_points", 0.0)
    print(f"📊 Live Market: Bid = ${ticks.get('bid')}, Ask = ${ticks.get('ask')}, Spread = {spread} pts")
    print(f"💰 Account: Balance = €{account.get('balance'):,.2f}, Equity = €{account.get('equity'):,.2f}")

    # 2. News Engine
    news_engine = ForexNewsEngine()
    news_payload = news_engine.get_news_payload()
    print(f"📰 News Status: Blackout Active = {news_payload.get('news_blackout_active')}, Reason = {news_payload.get('blackout_reason')}")

    # 3. Initialize Master Coordinator
    coordinator = MasterCoordinator()
    print("✅ MasterCoordinator initialized with 14 Strategy Agents + CRO.")

    # 4. Run Deliberation
    now_utc = datetime.now(timezone.utc)
    print("\n🏛️ Convening 14-Agent Council Deliberation...")
    start_time = time.time()
    decision = coordinator.run_council_deliberation(
        market_data=market_payload,
        news_data=news_payload,
        current_spread_points=spread,
        open_positions_count=0,
        day_of_month=now_utc.day
    )
    elapsed = time.time() - start_time
    print(f"⏱️ Council deliberation completed in {elapsed:.2f} seconds.")

    # 5. Inspect individual agent proposals
    proposals = decision.get("agent_proposals", {})
    print("\n" + "=" * 80)
    print(f"📋 ALL {len(proposals)} AGENTS COMMUNICATION & SIGNALS REPORT:")
    print("=" * 80)
    for agent_key, prop in sorted(proposals.items()):
        act = prop.get("action", prop.get("recommended_action", "N/A"))
        conf = prop.get("confidence_score", prop.get("sentiment_score", 0))
        bias = prop.get("bias", prop.get("macro_bias", prop.get("regime_type", "NEUTRAL")))
        setup = prop.get("setup_name", prop.get("pattern_identified", prop.get("regime_type", "N/A")))
        entry = prop.get("entry_price", "N/A")
        sl = prop.get("stop_loss", "N/A")
        tp = prop.get("take_profit_1", prop.get("take_profit", "N/A"))
        print(f"🔹 [{agent_key:<22}] Vote: {act:<6} | Conf: {conf:>3}% | Bias: {str(bias):<16} | Entry: {entry} | SL: {sl} | TP: {tp}")

    # 6. Lead Arbitrator & Consensus
    print("\n" + "=" * 80)
    print("⚖️ LEAD ARBITRATOR MASTER CONSENSUS RULING:")
    print("=" * 80)
    action = decision.get("action")
    consensus_score = decision.get("consensus_score")
    agreement_level = decision.get("council_agreement_level")
    entry_p = decision.get("entry_price")
    sl_p = decision.get("stop_loss")
    tp1_p = decision.get("take_profit_1")
    tp2_p = decision.get("take_profit_2")
    rr = decision.get("risk_reward_ratio")
    summary = decision.get("council_debate_summary")
    votes = decision.get("voting_summary", {})

    print(f"Action:              {action}")
    print(f"Consensus Score:     {consensus_score}% ({agreement_level})")
    print(f"Vote Tally:          BUY: {votes.get('BUY', 0)} | SELL: {votes.get('SELL', 0)} | HOLD: {votes.get('HOLD', 0)}")
    print(f"Entry Planned:       ${float(entry_p or 0.0):,.2f} (Current Bid: ${current_price:,.2f})")
    print(f"Stop Loss:           ${float(sl_p or 0.0):,.2f}")
    print(f"Take Profit 1 (1.75R): ${float(tp1_p or 0.0):,.2f}")
    print(f"Take Profit 2 (3.0R):  ${float(tp2_p or 0.0):,.2f}")
    print(f"Risk:Reward Ratio:   1:{rr}")
    print(f"Debate Summary:\n   {summary}")

    # 7. CRO Report & Lot Sizing
    cro = decision.get("cro_report", {})
    print("\n" + "=" * 80)
    print("🛡️ CHIEF RISK OFFICER (CRO) LOT SIZING & SAFETY REPORT:")
    print("=" * 80)
    print(f"Status:              {'🟢 APPROVED' if cro.get('approved') else '🔴 VETOED'}")
    print(f"Calculated Lot Size: {cro.get('calculated_lots')} Lots (Max Limit: {CONFIG.MAX_LOT_SIZE})")
    print(f"Risk Reason / Note:  {cro.get('reason')}")
    print(f"Risk Amount:         €{cro.get('risk_amount_eur', 0):,.2f}")

    data_engine.disconnect()
    print("\n✅ Test finished successfully.")

if __name__ == "__main__":
    test_council()
