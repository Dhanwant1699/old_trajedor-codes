import sys
sys.path.insert(0, ".")
import MetaTrader5 as mt5
from trajedor.src.cognitive_brain import CognitiveBrain

mt5.initialize()
sym = "XAUUSD.ecn" if mt5.symbol_info("XAUUSD.ecn") else "XAUUSD"

w1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_W1, 0, 75)
d1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 100)
h4 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H4, 0, 100)
h1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 100)
m30 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M30, 0, 200)
m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 250)
m5 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 280)
m1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)

price = mt5.symbol_info_tick(sym).bid

mtf_suite = {
    "w1": w1,
    "d1": d1,
    "h4": h4,
    "h1": h1,
    "m30": m30,
    "m15": m15,
    "m5": m5,
    "m1": m1
}

brain = CognitiveBrain(symbol=sym)
print(f"\n>>> Running Cognitive Deliberation with full 8-Timeframe Suite @ ${price:.2f}...")

thesis = brain.deliberate(
    current_price=price,
    mtf_candles=mtf_suite
)

print(f"\n[THESIS SUMMARY]")
print(f"Action: {thesis.action}")
print(f"Pitch Initiator: {thesis.pitch_initiator}")
print(f"Pitch Setup Type: {thesis.pitch_setup_type}")
print(f"Confidence: {thesis.confidence_score}%")
print(f"Consensus: {thesis.council_consensus_pct}%")
print(f"SL: ${thesis.stop_loss:.2f} | TP1: ${thesis.take_profit_1:.2f} | TP2: ${thesis.take_profit_2:.2f} | R:R: 1:{thesis.risk_reward_ratio}")
print(f"\n[ROUNDTABLE TRANSCRIPT]")
for turn in thesis.roundtable_transcript:
    print(f"  {turn['speaker']}: {turn['statement']}")

mt5.shutdown()
