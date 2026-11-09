path = r"trajedor/src/jarvis_executive.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Update __init__
old_init = """        self.journal = MemoryJournal()
        self.is_running = False"""

new_init = """        self.journal = MemoryJournal()
        self.is_running = False
        self.last_order_time = {}
        self.min_order_interval_secs = 180  # 3 minutes cooldown between auto-entries"""

assert old_init in c, "old_init not found"
c = c.replace(old_init, new_init, 1)

# 2. Add Auto-Dispatch block before end of run_cycle
old_end = """        print("[JARVIS MARK-85] Cycle complete. System standing by for closed candle trigger.\\n")"""

new_end = """        # 4. Autonomous Institutional Order Dispatch
        min_confidence = 80
        if thesis.action in ("BUY", "SELL") and thesis.confidence_score >= min_confidence and thesis.memory_gate_approved:
            for acc_id, acc_data in accounts.items():
                if not acc_data.get("is_active", True):
                    continue

                # Check cooldown to avoid duplicate entries within the same 3-minute window
                last_time = self.last_order_time.get(acc_id, 0.0)
                if time.time() - last_time < self.min_order_interval_secs:
                    continue

                current_ai_pos = acc_data.get("current_ai_pos_count", 0)
                max_pos = acc_data.get("max_concurrent_positions", 3)
                if current_ai_pos >= max_pos:
                    continue

                requested_lot = acc_data.get("max_single_trade_lot", 0.05)
                res = self.mt5_bridge.dispatch_order(
                    acc_id=acc_id,
                    action=thesis.action,
                    requested_lot=requested_lot,
                    sl=thesis.stop_loss,
                    tp=thesis.take_profit_1,
                    comment="TRAJEDOR_SNIPER"
                )
                if res.get("success"):
                    self.last_order_time[acc_id] = time.time()
                    print(f"  🎯 [AUTO-DISPATCH SUCCESS] >>> Fired {thesis.action} {res.get('volume')} lots on {acc_id} | Ticket: #{res.get('ticket')} @ ${res.get('price'):.2f} (SL: ${thesis.stop_loss}, TP: ${thesis.take_profit_1})", flush=True)
                else:
                    print(f"  ⚠️ [AUTO-DISPATCH NOTICE] {acc_id}: {res.get('reason')}", flush=True)

        print("[JARVIS MARK-85] Cycle complete. Standing by for next cognitive pulse.\\n")"""

assert old_end in c, "old_end not found"
c = c.replace(old_end, new_end, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("SUCCESSFULLY_PATCHED_JARVIS_EXECUTIVE")
