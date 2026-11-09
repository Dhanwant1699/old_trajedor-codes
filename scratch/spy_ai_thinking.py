"""
SPY ON THE AI'S THINKING - Expose exactly why it keeps firing the same trade.
Run: python scratch/spy_ai_thinking.py
"""
import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Auto-activate venv if present
venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Ai Trading ALGO", ".venv", "Scripts", "python.exe"))
if os.path.exists(venv_python) and not os.environ.get("TRAJEDOR_VENV_ACTIVATED"):
    os.environ["TRAJEDOR_VENV_ACTIVATED"] = "1"
    import subprocess
    sys.exit(subprocess.call([venv_python, "-u", __file__]))

from trajedor.src.cognitive_brain import CognitiveBrain
from trajedor.src.macro_sentinel import MacroSentinel
from trajedor.src.sentiment_sentinel import SentimentSentinel
from trajedor.src.mt5_multi_account import MT5MultiAccountBridge

LINE = "=" * 80

def print_section(title):
    print(f"\n{LINE}")
    print(f"  {title}")
    print(LINE)

def spy():
    print(LINE)
    print("  🔍 TRAJEDOR AI THINKING SPY — What Is The AI Actually Deciding & Why?")
    print(LINE)

    # ---------------------------------------------------------------
    # STEP 1: What price is AI seeing?
    # ---------------------------------------------------------------
    print_section("STEP 1 — WHAT PRICE IS THE AI SEEING?")
    bridge = MT5MultiAccountBridge()
    tick = bridge.get_live_gold_tick()
    price = float(tick.get("bid", 0.0) or tick.get("price", 0.0) or 0.0)
    spread = tick.get("spread", "?")
    status = tick.get("status", "UNKNOWN")
    print(f"  Gold Price (bid) : ${price:.2f}")
    print(f"  Spread           : {spread} pts")
    print(f"  MT5 Status       : {status}")
    if price == 0.0 or price == 4139.52:
        print()
        print("  ⚠️  WARNING: Price is the FALLBACK HARDCODED value ($4139.52)!")
        print("  ⚠️  This means MT5 is NOT connected or not returning live price.")
        print("  ⚠️  The AI is running on a FAKE FROZEN price every single cycle.")
        print("  ⚠️  Same fake price → same analysis → same signal → same trade fired!")

    # ---------------------------------------------------------------
    # STEP 2: What are the M5 candles telling the AI?
    # ---------------------------------------------------------------
    print_section("STEP 2 — WHAT M5 CANDLES IS THE AI READING?")
    m5_rates = None
    try:
        import MetaTrader5 as mt5
        ok = mt5.initialize(timeout=5000)
        if ok:
            m5_rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 30)
            if m5_rates is None or len(m5_rates) == 0:
                m5_rates = mt5.copy_rates_from_pos("XAUUSD.ecn", mt5.TIMEFRAME_M5, 0, 30)
            mt5.shutdown()
    except Exception as e:
        print(f"  MT5 Import Error: {e}")

    if m5_rates is not None and len(m5_rates) >= 5:
        highs = [float(c[2]) for c in m5_rates]
        lows = [float(c[3]) for c in m5_rates]
        closes = [float(c[4]) for c in m5_rates]
        session_high = max(highs)
        session_low = min(lows)
        last_3_displacement = closes[-1] - closes[-4] if len(closes) >= 4 else 0.0
        range_span = max(5.0, session_high - session_low)
        p = price if price > 0 else closes[-1]
        range_pct = (p - session_low) / range_span
        print(f"  ✅ LIVE M5 candles loaded: {len(m5_rates)} candles")
        print(f"  Session High     : ${session_high:.2f}")
        print(f"  Session Low      : ${session_low:.2f}")
        print(f"  Range Span       : {range_span:.2f} pts")
        print(f"  Range %          : {range_pct*100:.1f}%  (0%=floor, 100%=ceiling, 50%=midpoint)")
        print(f"  Last 3-candle    : {last_3_displacement:+.2f} pts displacement")
        if abs(last_3_displacement) < 1.0:
            print(f"  ⚠️  Very low displacement — market is FLAT/CONSOLIDATING")
    else:
        # This is the key problem — show what fallback values the brain uses
        p = price if price > 0 else 4139.52
        session_high = p + 15.0
        session_low  = p - 15.0
        range_span = 30.0
        range_pct = 0.50
        print(f"  ❌ NO live M5 candles — AI is using FALLBACK synthetic range!")
        print(f"  Fake session_high : ${session_high:.2f}  (= price + 15)")
        print(f"  Fake session_low  : ${session_low:.2f}  (= price - 15)")
        print(f"  Fake range_pct    : {range_pct*100:.1f}%  ← ALWAYS 50% (midpoint!)")
        print()
        print("  ⚠️  Because range_pct is ALWAYS 50%, Agent 2 (Location) always votes:")
        print("  ⚠️  range_pct >= 0.50 → SELL  (line 123 in cognitive_brain.py)")
        print("  ⚠️  This means Agent 2 gives the SAME vote EVERY single cycle.")

    # ---------------------------------------------------------------
    # STEP 3: What is macro saying?
    # ---------------------------------------------------------------
    print_section("STEP 3 — WHAT IS MACRO SENTINEL FEEDING THE BRAIN?")
    macro_sentinel = MacroSentinel()
    macro = macro_sentinel.get_live_macro_suite()
    dxy = macro.get("dxy", {})
    us10y = macro.get("us10y_yield", {})
    oil = macro.get("crude_oil", {})
    score = macro.get("gold_macro_impact_score", 0)
    bias = macro.get("gold_bias", "UNKNOWN")

    print(f"  DXY              : {dxy.get('price')}  Change: {dxy.get('change_pct',0):+.2f}%  Status: {dxy.get('status')}")
    print(f"  US 10Y Yield     : {us10y.get('price')}%  Change: {us10y.get('change',0):+.3f}  Status: {us10y.get('status')}")
    print(f"  Crude Oil        : ${oil.get('price')}  Status: {oil.get('status')}")
    print(f"  Gold Macro Score : {score:+d} / 100")
    print(f"  Gold Bias        : {bias}")

    if dxy.get("status") == "FALLBACK":
        print()
        print("  ⚠️  DXY is FALLBACK — Yahoo Finance is not responding!")
        print("  ⚠️  Score will be 0 by default → Agent 1 votes NEUTRAL every cycle!")
    if score == 0:
        print()
        print("  ℹ️  Macro score = 0 → Agent 1 (Macro) votes NEUTRAL")
        print("  ℹ️  This is NOT bullish or bearish — just no data.")

    # ---------------------------------------------------------------
    # STEP 4: What is sentiment saying?
    # ---------------------------------------------------------------
    print_section("STEP 4 — WHAT IS SENTIMENT SENTINEL FEEDING THE BRAIN?")
    sentiment = SentimentSentinel()
    condition = sentiment.evaluate_market_condition("XAUUSD")
    print(f"  Session Phase    : {condition.session_phase}")
    print(f"  Volatility       : {condition.volatility_regime}")
    print(f"  Retail LONG      : {condition.retail_sentiment_long_pct}%")
    print(f"  Retail SHORT     : {condition.retail_sentiment_short_pct}%")
    print(f"  Smart Money Bias : {condition.smart_money_bias}")
    print(f"  Retail Trap?     : {condition.retail_trap_detected}")

    if condition.retail_sentiment_long_pct == 71.4:
        print()
        print("  ⚠️  Retail sentiment = 71.4% LONG — this is the HARDCODED FALLBACK!")
        print("  ⚠️  Stocktwits API failed → AI uses same 71.4% every single cycle.")
        print("  ⚠️  71.4% > 70% → Smart Money = 'HUNTING_RETAIL_STOPS' EVERY cycle.")
        print("  ⚠️  Agent 5 (Sentiment) votes SELL EVERY cycle (retail trapped long).")

    # ---------------------------------------------------------------
    # STEP 5: Run the FULL council deliberation and show every vote
    # ---------------------------------------------------------------
    print_section("STEP 5 — FULL 6-AGENT COUNCIL DELIBERATION (LIVE)")
    brain = CognitiveBrain(symbol="XAUUSD")
    thesis = brain.deliberate(current_price=price if price > 0 else 4139.52, m5_candles=m5_rates)

    print(f"\n  🎯 FINAL DECISION   : {thesis.action}")
    print(f"  📊 CONFIDENCE       : {thesis.confidence_score}%")
    print(f"  📈 ENTRY PRICE      : ${thesis.entry_price:.2f}")
    print(f"  🛑 STOP LOSS        : ${thesis.stop_loss:.2f}")
    print(f"  🎯 TAKE PROFIT 1    : ${thesis.take_profit_1:.2f}")
    print(f"  ⚖️  RISK:REWARD      : 1:{thesis.risk_reward_ratio}")
    print(f"  🔒 MEMORY GATE      : {'✅ APPROVED' if thesis.memory_gate_approved else '❌ BLOCKED'}")
    print(f"\n  📣 JARVIS MONOLOGUE :")
    print(f"     {thesis.reasoning_monologue}")

    print(f"\n  🗳️  INDIVIDUAL AGENT VOTES:")
    print(f"  {'Agent':<22} {'Vote':<10}")
    print(f"  {'-'*34}")
    for agent, vote in thesis.council_votes.items():
        emoji = "✅" if vote == "BUY" else ("🔴" if vote == "SELL" else "⏸️ ")
        print(f"  {agent:<22} {emoji} {vote}")

    print(f"\n  📋 AGENT REASONING (WHY EACH VOTED THIS WAY):")
    for r in thesis.council_rationale:
        print(f"  → {r}")

    # ---------------------------------------------------------------
    # STEP 6: OPEN POSITIONS — what is already open?
    # ---------------------------------------------------------------
    print_section("STEP 6 — WHAT POSITIONS ARE CURRENTLY OPEN?")
    accounts = bridge.get_live_telemetry()
    total_ai_positions = 0
    for acc_id, acc_data in accounts.items():
        status_str = acc_data.get("status", "UNKNOWN")
        positions = acc_data.get("open_positions", [])
        ai_pos = [p for p in positions if p.get("is_ai")]
        total_ai_positions += len(ai_pos)
        print(f"\n  Account: {acc_id} — Status: {status_str}")
        if not ai_pos:
            print(f"    No AI positions open.")
        for p in ai_pos:
            direction = p.get("type", "?")
            entry = p.get("open_price", 0)
            sl = p.get("sl", 0)
            tp = p.get("tp", 0)
            profit = p.get("profit", 0)
            vol = p.get("volume", 0)
            dist_from_current = abs(price - entry) if price > 0 else "?"
            print(f"    Ticket #{p.get('ticket')}  {direction}  {vol} lots @ ${entry:.2f}")
            print(f"      SL: ${sl:.2f}  TP: ${tp:.2f}  P&L: €{profit:.2f}")
            print(f"      Distance from current price: {dist_from_current:.1f} pts")
            if isinstance(dist_from_current, float) and dist_from_current < 5.0:
                print(f"      ⚠️  WITHIN 5pt CLUSTER ZONE — new trade at same price zone will be BLOCKED")
            elif isinstance(dist_from_current, float) and dist_from_current >= 5.0:
                print(f"      ⚠️  OUTSIDE 5pt zone → anti-cluster check will PASS → new same-direction trade CAN fire!")

    # ---------------------------------------------------------------
    # STEP 7: THE DIAGNOSIS — WHY THE SAME TRADE FIRES AGAIN
    # ---------------------------------------------------------------
    print_section("STEP 7 — ROOT DIAGNOSIS: WHY THE SAME SIGNAL FIRES EVERY CYCLE")

    problems = []

    if price == 0.0 or price == 4139.52:
        problems.append(
            "FROZEN PRICE: MT5 not connected → AI uses hardcoded $4139.52 every single cycle.\n"
            "   Same price → same range calculation → same votes → same trade signal EVERY time."
        )

    if m5_rates is None or len(m5_rates) < 5:
        problems.append(
            "NO LIVE CANDLES: AI uses 'price ± 15' as fake session range.\n"
            "   range_pct is always 50% → Location Agent always votes SELL every cycle.\n"
            "   Same vote from Agent 2 every 10 seconds = same decision every 10 seconds."
        )

    if condition.retail_sentiment_long_pct == 71.4:
        problems.append(
            "HARDCODED SENTIMENT: Stocktwits API offline → same 71.4% Long fallback.\n"
            "   71.4% > 70% threshold → Smart Money = HUNTING_RETAIL_STOPS every cycle.\n"
            "   Agent 5 (Sentiment) votes SELL every single cycle."
        )

    if dxy.get("status") == "FALLBACK":
        problems.append(
            "MACRO DATA OFFLINE: Yahoo Finance not responding → DXY/Yields = fallback.\n"
            "   Macro score = 0 → Agent 1 votes NEUTRAL every cycle."
        )

    if not problems:
        problems.append(
            "All data sources appear to be live. The repeat trade is likely due to:\n"
            "   - 5pt anti-clustering threshold being too small (Gold drifts past 5pts easily)\n"
            "   - No check for same-direction trades already open\n"
            "   - Memory gate doesn't block after a loss"
        )

    print()
    for i, p in enumerate(problems, 1):
        print(f"  ❌ PROBLEM {i}: {p}")
        print()

    print()
    print("  📌 SUMMARY: The AI is NOT making different decisions each minute.")
    print("  📌 It's making the EXACT SAME decision every 10 seconds because")
    print("  📌 it sees the EXACT SAME inputs every 10 seconds (frozen/fallback data).")
    print("  📌 Every 3 minutes when the cooldown expires → same signal → new trade fired.")
    print()
    print(LINE)

if __name__ == "__main__":
    spy()
