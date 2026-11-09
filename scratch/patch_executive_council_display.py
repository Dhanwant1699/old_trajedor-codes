exec_file = r"trajedor/src/jarvis_executive.py"
with open(exec_file, "r", encoding="utf-8") as f:
    code = f.read()

target = """        # Cognitive Deliberation with Full Candle Structure & 1:2 R:R Guard
        thesis = self.brain.deliberate(current_price=price, m5_candles=m5_rates)
        print(f"  - Action Signal: {thesis.action} (Confidence: {thesis.confidence_score}%)", flush=True)"""

repl = """        # Cognitive Deliberation with Full 6-Agent Council Consensus & 1:2 R:R Guard
        thesis = self.brain.deliberate(current_price=price, m5_candles=m5_rates)
        print(f"  - 🏛️ Council Consensus Signal: {thesis.action} ({thesis.confidence_score}% Conviction | {thesis.council_consensus_pct}% Agreement)", flush=True)
        if hasattr(thesis, "council_rationale") and thesis.council_rationale:
            for r in thesis.council_rationale:
                print(f"    • {r}", flush=True)"""

assert target in code, "target in jarvis_executive.py not found"
code = code.replace(target, repl, 1)

with open(exec_file, "w", encoding="utf-8") as f:
    f.write(code)
print("SUCCESSFULLY_PATCHED_JARVIS_EXECUTIVE_LOGGING")
