"""
Pull full trade history (yesterday + today) from Amar Patil's account (acc_1)
and print a clean analysis of what happened.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Ai Trading ALGO", ".venv", "Scripts", "python.exe"))
if os.path.exists(venv_python) and not os.environ.get("TRAJEDOR_VENV_ACTIVATED"):
    os.environ["TRAJEDOR_VENV_ACTIVATED"] = "1"
    import subprocess
    sys.exit(subprocess.call([venv_python, "-u", __file__]))

from datetime import datetime, timezone, timedelta

LINE = "=" * 90

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 not installed.")
    sys.exit(1)

ACC = {
    "trader": "Amar Vijay Patil",
    "login": 52053251,
    "terminal": r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "magic": 888991,
    "currency": "USD"
}

def fmt_time(ts):
    if not ts:
        return "N/A"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return str(ts)

def main():
    print(LINE)
    print(f"  TRADE HISTORY REPORT — {ACC['trader']} (Login: {ACC['login']})")
    print(f"  Period: Yesterday + Today (Last 48 hours)")
    print(LINE)

    ok = mt5.initialize(path=ACC["terminal"], timeout=8000)
    if not ok:
        print(f"\n  ERROR: Cannot connect to MT5 terminal.")
        print(f"  Error: {mt5.last_error()}")
        sys.exit(1)

    info = mt5.account_info()
    if info:
        print(f"\n  Account   : {info.login} | {info.name}")
        print(f"  Broker    : {info.company}")
        print(f"  Balance   : ${info.balance:.2f}  Equity: ${info.equity:.2f}")
        print(f"  Floating  : ${info.profit:.2f}")

    # Time range: last 48h
    now_utc = datetime.now(timezone.utc)
    from_date = now_utc - timedelta(hours=48)

    # Fetch deals (closed trades) from history
    deals = mt5.history_deals_get(from_date, now_utc)
    orders = mt5.history_orders_get(from_date, now_utc)

    # Also fetch open positions right now
    open_positions = mt5.positions_get() or []

    mt5.shutdown()

    # -------------------------------------------------------
    # OPEN POSITIONS
    # -------------------------------------------------------
    print(f"\n{LINE}")
    print(f"  CURRENTLY OPEN POSITIONS ({len(open_positions)} total)")
    print(LINE)

    ai_open = [p for p in open_positions if p.magic == ACC["magic"] or p.magic in (888991, 888992, 888993)]
    other_open = [p for p in open_positions if p not in ai_open]

    if not open_positions:
        print("  None open.")
    else:
        print(f"\n  {'#':<4} {'Ticket':<12} {'Type':<6} {'Symbol':<10} {'Lots':<6} {'Open@':<10} {'Current@':<10} {'SL':<10} {'TP':<10} {'P&L':>8}  {'Comment'}")
        print(f"  {'-'*110}")
        for i, p in enumerate(open_positions, 1):
            direction = "BUY" if p.type == 0 else "SELL"
            is_ai = p.magic in (888991, 888992, 888993)
            tag = "[AI]" if is_ai else "[MAN]"
            pnl_str = f"${p.profit:+.2f}"
            print(f"  {i:<4} {p.ticket:<12} {direction:<6} {p.symbol:<10} {p.volume:<6.2f} {p.price_open:<10.2f} {p.price_current:<10.2f} {p.sl:<10.2f} {p.tp:<10.2f} {pnl_str:>8}  {tag} {p.comment}")

    # -------------------------------------------------------
    # CLOSED DEALS - Full History
    # -------------------------------------------------------
    print(f"\n{LINE}")
    print(f"  CLOSED DEALS HISTORY — Last 48 Hours")
    print(LINE)

    if not deals:
        print("  No deals found in this period.")
    else:
        # Separate entry and exit deals
        entries = [d for d in deals if d.entry == 0]   # DEAL_ENTRY_IN
        exits   = [d for d in deals if d.entry == 1]   # DEAL_ENTRY_OUT

        print(f"\n  Total deals       : {len(deals)}")
        print(f"  Entry deals (open): {len(entries)}")
        print(f"  Exit  deals (close): {len(exits)}")

        # Reconstruct trades from deals
        trades = []
        deal_map = {}
        for d in deals:
            deal_map[d.position_id] = deal_map.get(d.position_id, [])
            deal_map[d.position_id].append(d)

        print(f"\n  Unique positions  : {len(deal_map)}")

        # --- Per trade breakdown ---
        print(f"\n  {'#':<4} {'Ticket':<12} {'Dir':<5} {'Sym':<10} {'Lots':<6} {'Entry@':<10} {'Exit@':<10} {'PnL':>8}  {'Duration':<18} {'Entry Time':<25} {'Tag'}")
        print(f"  {'-'*130}")

        total_pnl = 0.0
        wins = 0
        losses = 0
        be = 0
        ai_trades = 0
        manual_trades = 0
        total_ai_pnl = 0.0
        total_manual_pnl = 0.0
        all_trades_detail = []

        for pos_id, pos_deals in sorted(deal_map.items(), key=lambda x: min(d.time for d in x[1])):
            # Find entry and exit
            entry_deal = next((d for d in pos_deals if d.entry == 0), None)
            exit_deal  = next((d for d in pos_deals if d.entry == 1), None)

            if not entry_deal:
                continue

            direction = "BUY" if entry_deal.type == 0 else "SELL"
            symbol = entry_deal.symbol
            lots = entry_deal.volume
            entry_price = entry_deal.price
            entry_time = entry_deal.time
            magic = entry_deal.magic
            comment = entry_deal.comment or ""
            is_ai = magic in (888991, 888992, 888993)

            if exit_deal:
                exit_price = exit_deal.price
                exit_time = exit_deal.time
                pnl = sum(d.profit for d in pos_deals)
                duration_secs = exit_time - entry_time
                mins = duration_secs // 60
                secs = duration_secs % 60
                duration_str = f"{mins}m {secs}s"
                status = "CLOSED"
            else:
                exit_price = 0.0
                exit_time = 0
                pnl = sum(d.profit for d in pos_deals)
                duration_str = "OPEN"
                status = "OPEN"

            total_pnl += pnl
            if pnl > 0.01:
                wins += 1
            elif pnl < -0.01:
                losses += 1
            else:
                be += 1

            if is_ai:
                ai_trades += 1
                total_ai_pnl += pnl
            else:
                manual_trades += 1
                total_manual_pnl += pnl

            tag = "[AI]" if is_ai else "[MAN]"
            pnl_str = f"${pnl:+.2f}"
            i = len(all_trades_detail) + 1
            print(f"  {i:<4} {pos_id:<12} {direction:<5} {symbol:<10} {lots:<6.2f} {entry_price:<10.2f} {exit_price:<10.2f} {pnl_str:>8}  {duration_str:<18} {fmt_time(entry_time):<25} {tag} {comment[:30]}")

            all_trades_detail.append({
                "pos_id": pos_id,
                "direction": direction,
                "symbol": symbol,
                "lots": lots,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "duration_str": duration_str,
                "entry_time": entry_time,
                "is_ai": is_ai,
                "comment": comment,
                "status": status
            })

        # -------------------------------------------------------
        # SUMMARY STATISTICS
        # -------------------------------------------------------
        total_trades = len(all_trades_detail)
        closed_trades = [t for t in all_trades_detail if t["status"] == "CLOSED"]
        win_rate = (wins / max(1, wins + losses)) * 100

        print(f"\n{LINE}")
        print(f"  PERFORMANCE SUMMARY — Amar Patil Account")
        print(LINE)
        print(f"\n  Total Positions   : {total_trades}")
        print(f"  Wins              : {wins}   (${sum(t['pnl'] for t in all_trades_detail if t['pnl'] > 0.01):+.2f})")
        print(f"  Losses            : {losses}   (${sum(t['pnl'] for t in all_trades_detail if t['pnl'] < -0.01):+.2f})")
        print(f"  Breakeven         : {be}")
        print(f"  Win Rate          : {win_rate:.1f}%")
        print(f"  Total P&L         : ${total_pnl:+.2f}")
        print()
        print(f"  AI Trades         : {ai_trades}   Net: ${total_ai_pnl:+.2f}")
        print(f"  Manual Trades     : {manual_trades}   Net: ${total_manual_pnl:+.2f}")

        # -------------------------------------------------------
        # PATTERN ANALYSIS — Detect repeat entries
        # -------------------------------------------------------
        print(f"\n{LINE}")
        print(f"  PATTERN ANALYSIS — Why Same Trade Fired Again & Again?")
        print(LINE)

        # Group AI trades by direction
        ai_trade_list = [t for t in all_trades_detail if t["is_ai"]]
        sells = [t for t in ai_trade_list if t["direction"] == "SELL"]
        buys  = [t for t in ai_trade_list if t["direction"] == "BUY"]

        print(f"\n  AI SELL trades  : {len(sells)}")
        print(f"  AI BUY  trades  : {len(buys)}")

        if sells:
            sell_prices = [t["entry_price"] for t in sells]
            price_range = max(sell_prices) - min(sell_prices)
            print(f"\n  SELL entries ranged from ${min(sell_prices):.2f} to ${max(sell_prices):.2f} — spread: {price_range:.2f} pts")
            print(f"\n  --- All SELL trades in order ---")
            for i, t in enumerate(sells, 1):
                pnl_str = f"${t['pnl']:+.2f}"
                result = "WIN" if t["pnl"] > 0.01 else ("LOSS" if t["pnl"] < -0.01 else "OPEN/BE")
                print(f"  {i}. @ ${t['entry_price']:.2f}  [{result}] {pnl_str}  dur={t['duration_str']}  at {fmt_time(t['entry_time'])}")
                if i > 1:
                    gap = abs(t["entry_price"] - sells[i-2]["entry_price"])
                    time_gap = t["entry_time"] - sells[i-2]["entry_time"]
                    print(f"     ^ Gap from prev entry: {gap:.2f} pts | Time gap: {time_gap//60}m {time_gap%60}s")

        # Check if trades opened right after losses
        print(f"\n  --- Did AI re-enter immediately after losses? ---")
        for i in range(1, len(ai_trade_list)):
            prev = ai_trade_list[i-1]
            curr = ai_trade_list[i]
            if prev["pnl"] < -0.01 and prev["status"] == "CLOSED":
                time_gap = curr["entry_time"] - prev["entry_time"]
                print(f"  LOSS at {fmt_time(prev['entry_time'])} (${prev['pnl']:+.2f})")
                print(f"  -> Next trade opened {time_gap//60}m {time_gap%60}s later at ${curr['entry_price']:.2f}  [{curr['direction']}]")
                if time_gap < 300:
                    print(f"  *** IMMEDIATE RE-ENTRY! Less than 5 minutes after a loss! ***")
                print()

    print(LINE)

if __name__ == "__main__":
    main()
