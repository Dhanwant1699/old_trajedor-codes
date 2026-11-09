"""Exact timing analysis of all AI trades to expose the 3-min firing loop."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Ai Trading ALGO", ".venv", "Scripts", "python.exe"))
if os.path.exists(venv_python) and not os.environ.get("TRAJEDOR_VENV_ACTIVATED"):
    os.environ["TRAJEDOR_VENV_ACTIVATED"] = "1"
    import subprocess
    sys.exit(subprocess.call([venv_python, "-u", __file__]))

from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5

AI_MAGIC = (888991, 888992, 888993)
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"

def ts(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

ok = mt5.initialize(path=TERMINAL, timeout=8000)
if not ok:
    print("MT5 offline:", mt5.last_error())
    sys.exit(1)

now = datetime.now(timezone.utc)
from_dt = now - timedelta(hours=48)
deals = mt5.history_deals_get(from_dt, now) or []
mt5.shutdown()

# Build position map
pos_map = {}
for d in deals:
    if d.magic not in AI_MAGIC:
        continue
    if "XAUUSD" not in d.symbol.upper():
        continue
    pos_map.setdefault(d.position_id, []).append(d)

# Build closed trades only
trades = []
for pid, ds in pos_map.items():
    e = next((d for d in ds if d.entry == 0), None)
    x = next((d for d in ds if d.entry == 1), None)
    if not e or not x:
        continue
    pnl = round(sum(d.profit + d.swap + d.commission for d in ds), 2)
    pts = round((x.price - e.price) if e.type == 0 else (e.price - x.price), 2)
    dur = x.time - e.time
    trades.append({
        "pid":     pid,
        "dir":     "BUY" if e.type == 0 else "SELL",
        "entry_p": e.price,
        "exit_p":  x.price,
        "pts":     pts,
        "pnl":     pnl,
        "entry_t": e.time,
        "exit_t":  x.time,
        "dur":     dur,
    })

trades.sort(key=lambda t: t["entry_t"])

L = "=" * 90
print()
print(L)
print("  EXACT TIMING OF EVERY AI TRADE — WHY IT FIRES EVERY 3 MINUTES")
print(L)
print()
print("  #     Dir    Entry       Exit       Pts    P&L       Result  At Time (UTC)           Gap / Comment")
print("  " + "-" * 100)

for i, t in enumerate(trades):
    result = "WIN " if t["pnl"] > 0.01 else ("LOSS" if t["pnl"] < -0.01 else "BE  ")
    entry_str = ts(t["entry_t"])

    if i > 0:
        gap_secs = t["entry_t"] - trades[i-1]["entry_t"]
        gap_str  = "%dm %ds" % (gap_secs // 60, gap_secs % 60)
        note = ""
        if gap_secs < 200:
            note = " <-- BACK-TO-BACK (cooldown barely expired!)"
        elif 170 < gap_secs < 210:
            note = " <-- exactly 3min cooldown clock"
        elif gap_secs < 400:
            note = " <-- 3-6 min gap (next cooldown cycle)"
        # highlight if prev was a loss and this fires immediately after
        if trades[i-1]["pnl"] < -0.01:
            note += "  *** RE-ENTRY AFTER LOSS ***"
    else:
        gap_str = "first"
        note = ""

    print("  %-5d %-5s %-11.2f %-11.2f %-7.2f %-9.2f [%s] %-24s %s%s" % (
        i+1, t["dir"], t["entry_p"], t["exit_p"], t["pts"], t["pnl"],
        result, entry_str, gap_str, note
    ))

# ------------------------------------------------------------------
print()
print(L)
print("  ROOT CAUSE EXPLANATION — WHY THE AI HAS NO BRAKE")
print(L)
print("""
  Every 10 seconds the AI loop runs. Inside that loop:

  STEP 1:  "Is there a trade signal?" → YES (DXY strong, 72% retail long = SELL always)
  STEP 2:  "Did cooldown expire (3 min)?" → Checks self.last_order_time[acc_id]
  STEP 3:  "Is there an open position within 5pts?" → Checks current open positions
  STEP 4:  If all checks pass → FIRE trade

  THE PROBLEM — what the AI does NOT check:
  ✗  Did my LAST trade just close in a LOSS?
  ✗  Am I in a losing streak (2, 3 losses in a row)?
  ✗  Is the market currently moving AGAINST my thesis (bullish sweep)?
  ✗  Am I re-entering the same losing zone?

  So the loop runs:
    09:01:40 → SELL fired (cooldown just expired after last trade)
    09:04:42 → Previous SELL hit TP (small win) → cooldown expired → SELL again → LOSS
    09:07:49 → Previous SELL hit SL (loss) → cooldown expired → SELL AGAIN → LOSS
               ^ The AI literally doesn't know it just lost. It only sees the clock.
""")

# ------------------------------------------------------------------
print(L)
print("  CONSECUTIVE LOSS SEQUENCES DETECTED")
print(L)
print()
loss_streaks = []
streak = []
for t in trades:
    if t["pnl"] < -0.01:
        streak.append(t)
    else:
        if len(streak) >= 2:
            loss_streaks.append(streak[:])
        streak = []
if len(streak) >= 2:
    loss_streaks.append(streak)

if not loss_streaks:
    print("  No consecutive loss streaks found.")
else:
    for s in loss_streaks:
        total_loss = sum(t["pnl"] for t in s)
        span = s[-1]["entry_t"] - s[0]["entry_t"]
        print("  LOSS STREAK: %d trades in %dm %ds | Total damage: $%.2f" % (
            len(s), span//60, span%60, total_loss))
        for t in s:
            print("    -> %s @ $%.2f  P&L: $%.2f  at %s" % (
                t["dir"], t["entry_p"], t["pnl"], ts(t["entry_t"])))
        print()

# ------------------------------------------------------------------
print(L)
print("  SMARTER SOLUTION (not 15-min hard block)")
print(L)
print("""
  YOUR CONCERN: "15-min block can miss good entries"  <- VALID. 

  Better approach = LOSS-ADAPTIVE CONFIDENCE ESCALATOR:

  Normal market:  Need 5/6 agents to agree → fire trade  (current)

  After 1 LOSS:   Need 6/6 agents (UNANIMOUS) for next 10 minutes.
                  -> Most signals won't qualify → no re-entry into the same mess
                  -> But if ALL 6 agents strongly agree → still enters (won't miss great setup)

  After 2 LOSSES in 20 min: Pause ALL trading for 20 minutes flat.
                  -> Market is clearly against us right now
                  -> 20 mins is enough for the structure to reprice

  After 3 LOSSES in 30 min: STOP for rest of session. Send alert.
                  -> Something fundamentally wrong (news event, macro shock)
                  -> No amount of signal quality fixes a broken session

  This way:
  - You don't miss good entries (6/6 consensus is rare but fires when real)
  - You stop the bleeding when the AI is wrong about direction
  - No arbitrary time block — the market itself decides via agent consensus
""")
print(L)
