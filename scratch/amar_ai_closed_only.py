"""
Show ONLY closed AI trades (TRAJEDOR_SNIPER) from yesterday + today
for Amar Patil account (acc_1 / login 52053251).
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Ai Trading ALGO", ".venv", "Scripts", "python.exe"))
if os.path.exists(venv_python) and not os.environ.get("TRAJEDOR_VENV_ACTIVATED"):
    os.environ["TRAJEDOR_VENV_ACTIVATED"] = "1"
    import subprocess
    sys.exit(subprocess.call([venv_python, "-u", __file__]))

from datetime import datetime, timezone, timedelta

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 not installed."); sys.exit(1)

LINE  = "=" * 100
LINE2 = "-" * 100
AI_MAGIC = (888991, 888992, 888993)
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"

def ts(t):
    try: return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d  %H:%M:%S")
    except: return "N/A"

def main():
    ok = mt5.initialize(path=TERMINAL, timeout=8000)
    if not ok:
        print(f"Cannot connect: {mt5.last_error()}"); sys.exit(1)

    info = mt5.account_info()
    now  = datetime.now(timezone.utc)
    from_dt = now - timedelta(hours=48)

    # Pull ALL deals from last 48h
    deals = mt5.history_deals_get(from_dt, now) or []
    mt5.shutdown()

    # ── filter: only AI magic numbers + only XAUUSD + only closed (entry==1 has a matching entry==0)
    # Build position map: pos_id → list of deals
    pos_map = {}
    for d in deals:
        if d.magic not in AI_MAGIC:
            continue
        if "XAUUSD" not in d.symbol.upper():
            continue
        pos_map.setdefault(d.position_id, []).append(d)

    # Keep only fully CLOSED positions (have both entry IN and entry OUT deal)
    closed = []
    still_open = []
    for pid, ds in pos_map.items():
        entry_deal = next((d for d in ds if d.entry == 0), None)
        exit_deal  = next((d for d in ds if d.entry == 1), None)
        if entry_deal and exit_deal:
            pnl      = round(sum(d.profit + d.swap + d.commission for d in ds), 2)
            gross    = round(sum(d.profit for d in ds), 2)
            duration = exit_deal.time - entry_deal.time
            closed.append({
                "pid"      : pid,
                "dir"      : "BUY" if entry_deal.type == 0 else "SELL",
                "lots"     : entry_deal.volume,
                "entry_p"  : entry_deal.price,
                "exit_p"   : exit_deal.price,
                "pnl"      : pnl,
                "gross"    : gross,
                "entry_t"  : entry_deal.time,
                "exit_t"   : exit_deal.time,
                "duration" : duration,
                "comment"  : entry_deal.comment or "",
                "magic"    : entry_deal.magic,
            })
        elif entry_deal:
            still_open.append(entry_deal.position_id)

    # Sort by entry time
    closed.sort(key=lambda x: x["entry_t"])

    # ── Print
    print(LINE)
    print(f"  AI CLOSED TRADE ANALYSIS — Amar Vijay Patil (Login {info.login if info else 52053251})")
    print(f"  Period : Last 48 hours  ({from_dt.strftime('%Y-%m-%d %H:%M')} UTC  →  {now.strftime('%Y-%m-%d %H:%M')} UTC)")
    print(f"  Broker : {info.company if info else 'GTC Global SA'}")
    print(LINE)

    if not closed:
        print("\n  No closed AI trades found in this period.\n")
        print(LINE); return

    # ── Header
    print(f"\n  {'#':<4} {'Ticket':<13} {'Dir':<5} {'Lots':<6} {'Entry $':<10} {'Exit $':<10}"
          f"  {'Pts':>6}  {'P&L':>8}  {'Duration':<12}  {'Entry Time (UTC)':<22}  {'Exit Time (UTC)'}")
    print(f"  {LINE2}")

    wins = losses = be = 0
    total_pnl = 0.0
    total_pts = 0.0
    biggest_win = biggest_loss = None

    for i, t in enumerate(closed, 1):
        pts  = round((t["exit_p"] - t["entry_p"]) if t["dir"] == "BUY"
                     else (t["entry_p"] - t["exit_p"]), 2)
        dur  = f"{t['duration']//60}m {t['duration']%60}s"
        pnl  = t["pnl"]
        result = "WIN " if pnl > 0.01 else ("LOSS" if pnl < -0.01 else "BE  ")

        total_pnl += pnl
        total_pts += pts

        if pnl > 0.01:
            wins += 1
            if biggest_win is None or pnl > biggest_win["pnl"]: biggest_win = t
        elif pnl < -0.01:
            losses += 1
            if biggest_loss is None or pnl < biggest_loss["pnl"]: biggest_loss = t
        else:
            be += 1

        print(f"  {i:<4} {t['pid']:<13} {t['dir']:<5} {t['lots']:<6.2f} {t['entry_p']:<10.2f} {t['exit_p']:<10.2f}"
              f"  {pts:>+6.2f}  {pnl:>+8.2f}  {dur:<12}  {ts(t['entry_t']):<22}  {ts(t['exit_t'])}")

    print(f"\n  {LINE2}")

    # ── Summary stats
    total = len(closed)
    wr    = wins / max(1, wins + losses) * 100
    avg_win  = sum(t["pnl"] for t in closed if t["pnl"] >  0.01) / max(1, wins)
    avg_loss = sum(t["pnl"] for t in closed if t["pnl"] < -0.01) / max(1, losses)
    rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    print(f"\n{LINE}")
    print(f"  PERFORMANCE SUMMARY")
    print(LINE)
    print(f"\n  Total AI trades   : {total}")
    print(f"  Wins              : {wins}     ({wr:.1f}% win rate)")
    print(f"  Losses            : {losses}")
    print(f"  Breakeven         : {be}")
    print(f"  ─────────────────────────────")
    print(f"  Total Net P&L     : ${total_pnl:+.2f}")
    print(f"  Total Points      : {total_pts:+.2f} pts")
    print(f"  Avg Win           : ${avg_win:+.2f}")
    print(f"  Avg Loss          : ${avg_loss:+.2f}")
    print(f"  Reward:Risk Ratio : {rr_ratio:.2f}:1")
    if biggest_win:
        print(f"  Best Trade        : #{biggest_win['pid']}  ${biggest_win['pnl']:+.2f}  ({biggest_win['dir']} @ {biggest_win['entry_p']})")
    if biggest_loss:
        print(f"  Worst Trade       : #{biggest_loss['pid']}  ${biggest_loss['pnl']:+.2f}  ({biggest_loss['dir']} @ {biggest_loss['entry_p']})")

    # ── Pattern: detect clusters (trades within 5 pts and 5 mins of each other)
    print(f"\n{LINE}")
    print(f"  CLUSTER DETECTION — Trades Opened Too Close Together")
    print(LINE)
    cluster_found = False
    for i in range(1, len(closed)):
        prev = closed[i-1]
        curr = closed[i]
        price_gap = abs(curr["entry_p"] - prev["entry_p"])
        time_gap  = curr["entry_t"] - prev["entry_t"]
        same_dir  = curr["dir"] == prev["dir"]
        if price_gap < 10.0 and time_gap < 600 and same_dir:
            cluster_found = True
            print(f"\n  CLUSTER DETECTED:")
            print(f"    Trade #{i}   {prev['dir']} @ ${prev['entry_p']:.2f}  P&L: ${prev['pnl']:+.2f}  at {ts(prev['entry_t'])}")
            print(f"    Trade #{i+1}  {curr['dir']} @ ${curr['entry_p']:.2f}  P&L: ${curr['pnl']:+.2f}  at {ts(curr['entry_t'])}")
            print(f"    Price gap: {price_gap:.2f} pts  |  Time gap: {time_gap//60}m {time_gap%60}s  |  Same direction: {same_dir}")
            prev_result = "WIN" if prev["pnl"] > 0.01 else "LOSS"
            curr_result = "WIN" if curr["pnl"] > 0.01 else "LOSS"
            print(f"    Result: {prev_result} then {curr_result}")
            if prev["pnl"] < -0.01:
                print(f"    *** RE-ENTRY AFTER LOSS — AI re-shorted {time_gap//60}m {time_gap%60}s after a ${prev['pnl']:+.2f} loss! ***")
    if not cluster_found:
        print("\n  No dangerous clusters detected.")

    # ── Direction breakdown by session
    print(f"\n{LINE}")
    print(f"  DIRECTION & SESSION BREAKDOWN")
    print(LINE)

    sells = [t for t in closed if t["dir"] == "SELL"]
    buys  = [t for t in closed if t["dir"] == "BUY"]
    sell_pnl = sum(t["pnl"] for t in sells)
    buy_pnl  = sum(t["pnl"] for t in buys)

    print(f"\n  SELL trades : {len(sells)}   Net: ${sell_pnl:+.2f}   "
          f"Wins: {sum(1 for t in sells if t['pnl']>0.01)}  "
          f"Losses: {sum(1 for t in sells if t['pnl']<-0.01)}")
    print(f"  BUY  trades : {len(buys)}   Net: ${buy_pnl:+.2f}   "
          f"Wins: {sum(1 for t in buys  if t['pnl']>0.01)}  "
          f"Losses: {sum(1 for t in buys  if t['pnl']<-0.01)}")

    # Duration analysis
    avg_win_dur  = sum(t["duration"] for t in closed if t["pnl"]>0.01)  / max(1, wins)
    avg_loss_dur = sum(t["duration"] for t in closed if t["pnl"]<-0.01) / max(1, losses)
    print(f"\n  Avg winning trade duration : {int(avg_win_dur//60)}m {int(avg_win_dur%60)}s")
    print(f"  Avg losing  trade duration : {int(avg_loss_dur//60)}m {int(avg_loss_dur%60)}s")

    if still_open:
        print(f"\n  Still-open AI positions (not counted above): {still_open}")

    print(f"\n{LINE}\n")

if __name__ == "__main__":
    main()
