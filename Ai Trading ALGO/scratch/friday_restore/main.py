"""
Main Autonomous 24/5 Multi-Agent AI Trading System for XAUUSD (Gold).
Features:
- Dedicated 5-Minute (M5) Candle Confirmation Engine (Zero calculation delay, fires instant MT5 orders).
- Non-Blocking Background 5-Minute CRO Council Deliberation Engine (All 10 Strategy Agents poll every 300s).
- Dynamic M5 Pullback Zone Tracking with institutional tolerance band (±1.0 pt Gold).
- Autonomous Pro-Trader Position Management (3-Tier Trailing SL, Breakeven Locks, News Defense).
"""

import sys
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import CONFIG
from core import MT5DataEngine, ForexNewsEngine, MT5ExecutionEngine
from core.council_state import CouncilStateManager
from core.pro_trade_manager import ProTradeManager
from core.ai_ledger import AITradeLedger
from core.dual_account_manager import DualAccountManager
from agents.master_coordinator import MasterCoordinator


# Global deliberation control events & flags
_rescan_events = {}
_worker_running = True
_ORDER_EXECUTION_LOCK = threading.Lock()


def print_banner():
    print("=" * 85)
    print("   🤖 AGENTIC MULTI-AGENT AI TRADING SYSTEM - PURE GOLD (XAUUSD) SPECIALIST")
    print(f"   Model: {CONFIG.CLAUDE_MODEL if CONFIG.AI_PROVIDER == 'anthropic' else CONFIG.NVIDIA_MODEL} | Asset: {', '.join(CONFIG.SYMBOLS)} | TF: {CONFIG.EXECUTION_TIMEFRAME}")
    print("   Top 14 Institutional Strategy Council Agents:")
    print("     1. SMC & ICT Specialist          |  8. Fibonacci & Golden Pocket (OTE) Specialist")
    print("     2. Trend & Momentum Specialist    |  9. Chart Pattern & Multi-TF Radar")
    print("     3. Mean-Reversion Specialist      | 10. Intraday Scalping & Momentum Thrust")
    print("     4. Macro & News Specialist        | 11. Market Regime Detection Agent")
    print("     5. Volume Profile & VWAP Agent    | 12. Liquidity & Spread Shield Agent")
    print("     6. Supply & Demand Zones Origin   | 13. Tick / Order Flow Aggressor Agent")
    print("     7. Breakout & Volatility Squeeze  | 14. Cumulative Volume Delta (CVD) Agent")
    print(f"   Governance: Chief Risk Officer (CRO) | Lead Arbitrator Master Coordinator")
    print(f"   Execution: 5-Minute (M5) Candle Confirmation Engine | Deliberation: 5-Min Council ({CONFIG.COUNCIL_DELIBERATION_INTERVAL_SECONDS}s)")
    print(f"   Risk: {CONFIG.MAX_RISK_PER_TRADE_PCT}%/trade | Min RR: 1:{CONFIG.MIN_RISK_REWARD_RATIO} | Max DD: {CONFIG.MAX_DAILY_DRAWDOWN_PCT}%")
    print(f"   Tolerance: ±{CONFIG.ENTRY_TOLERANCE_POINTS} pt Gold | Trigger TF: {CONFIG.TRIGGER_TIMEFRAME}")
    print("=" * 85)


def _async_council_deliberation_worker(symbols, data_engines, news_engine, coordinator):
    """
    Background worker thread that runs 5-minute CRO 14-Agent council deliberations.
    Synchronized to 5-minute M5 candle cycles without blocking execution.
    """
    global _worker_running
    last_delib_time = {sym: 0.0 for sym in symbols}

    print(f"[BACKGROUND WORKER] 🏛️ 5-Minute (M5) Candle Council Deliberation Engine Started (Interval: {CONFIG.COUNCIL_DELIBERATION_INTERVAL_SECONDS}s).")

    while _worker_running:
        try:
            now_ts = time.time()
            now_utc = datetime.now(timezone.utc)
            day_of_month = now_utc.day

            for sym in symbols:
                d_eng = data_engines.get(sym)
                if not d_eng:
                    continue

                event = _rescan_events.get(sym)
                is_forced = event.is_set() if event else False
                if is_forced and event:
                    event.clear()

                time_since = now_ts - last_delib_time.get(sym, 0.0)
                interval = CONFIG.COUNCIL_DELIBERATION_INTERVAL_SECONDS

                # Check if symbol has capacity for new positions
                open_pos = d_eng.get_open_positions()

                if (time_since >= interval or is_forced) and (len(open_pos) < CONFIG.MAX_OPEN_TRADES):
                    last_delib_time[sym] = time.time()

                    # Extract market data in background
                    market_data = d_eng.extract_full_market_payload()
                    ticks = market_data.get("pricing", {})
                    account = market_data.get("account", {})
                    current_price = float(ticks.get("bid", 0.0) or 0.0)

                    print("\n" + "=" * 85)
                    print(f"[{now_utc.strftime('%H:%M:%S UTC')}] 🏛️  [{sym}] CRO 5-MINUTE CANDLE OPINION POLL & RISK ASSESSMENT @ ${current_price:,.2f}")
                    print(f"   Session: {market_data['session']['session_name']} | Spread: {ticks.get('spread_points', 0)} pts | Balance: €{account.get('balance', 0):,.2f} | Equity: €{account.get('equity', 0):,.2f}")
                    print(f"   🛡️ Chief Risk Officer (CRO) actively asking all 14 Strategy Agents for M5 5-candle consensus...")
                    print("=" * 85)

                    news_data = news_engine.get_news_payload()

                    # Convene the 14-Agent Council
                    decision = coordinator.run_council_deliberation(
                        market_data=market_data,
                        news_data=news_data,
                        current_spread_points=ticks.get("spread_points", 0.0),
                        open_positions_count=len(open_pos),
                        day_of_month=day_of_month
                    )

                    p = decision.get("agent_proposals", {})
                    cro = decision.get("cro_report", {})

                    print(f"\n   📋 [{sym}] 5-MINUTE M5 AGENT OPINIONS:")
                    agents_summary = [
                        ("1. SMC & ICT", p.get("1_SMC_ICT", {})),
                        ("2. Trend/Momentum", p.get("2_Trend_Momentum", {})),
                        ("3. Mean-Reversion", p.get("3_Mean_Reversion", {})),
                        ("4. Macro & News", p.get("4_Macro_News", {})),
                        ("5. OrderFlow/VWAP", p.get("5_OrderFlow_VWAP", {})),
                        ("6. Supply/Demand", p.get("6_Supply_Demand", {})),
                        ("7. Breakout/Squeeze", p.get("7_Breakout_Volatility", {})),
                        ("8. Fibonacci/OTE", p.get("8_Fibonacci_OTE", {})),
                        ("9. Chart Patterns", p.get("9_Chart_Pattern", {})),
                        ("10. Scalping/Fast", p.get("10_Intraday_Scalp", {})),
                        ("11. Regime Detect", p.get("11_Regime_Detection", {})),
                        ("12. Liquidity Shield", p.get("12_Liquidity_Execution", {})),
                        ("13. Tick Flow", p.get("13_Tick_OrderFlow", {})),
                        ("14. Volume CVD", p.get("14_Volume_Delta_CVD", {})),
                    ]

                    for name, res in agents_summary:
                        action_str = res.get("action", res.get("recommended_action", "N/A"))
                        conf = res.get("confidence_score", res.get("sentiment_score", 0))
                        bias = res.get("bias", res.get("macro_bias", "NEUTRAL"))
                        setup = res.get("setup_name", res.get("pattern_identified", "N/A"))
                        print(f"   🔹 [{name:<18}] Opinion: {action_str:<10} | Conf: {conf:>3}% | Bias: {bias:<7} | Setup: {str(setup)[:28]}")

                    print("-" * 85)
                    print(f"   🛡️  [{sym} CRO REPORT] Clearance: {'🟢 APPROVED' if cro.get('approved') else '🔴 VETOED'} | Lots: {cro.get('calculated_lots', 0.0)} (Max ≤ {CONFIG.MAX_LOT_SIZE}) | Risk Status: {cro.get('reason', 'Normal')}")
                    print("-" * 85)

                    action = decision.get("action", "HOLD").upper()
                    consensus_score = decision.get("consensus_score", 0)
                    agreement_level = decision.get("council_agreement_level", "N/A")
                    debate_summary = decision.get("council_debate_summary", "No summary.")
                    entry_p = float(decision.get("entry_price", current_price) or current_price)
                    sl_p = float(decision.get("stop_loss", 0.0) or 0.0)
                    tp1_p = float(decision.get("take_profit_1", 0.0) or 0.0)
                    tp2_p = float(decision.get("take_profit_2", 0.0) or 0.0)

                    print(f"   ⚖️  [{sym}] LEAD ARBITRATOR RULING: {action} (Consensus Conviction: {consensus_score}%) | Quorum: {agreement_level}")
                    if action in ["BUY", "SELL"]:
                        print(f"   🎯 Target Setup: Entry @ {entry_p:,.2f} [Zone: {entry_p-1.0:,.2f} - {entry_p+1.0:,.2f}] | SL: {sl_p:,.2f} | TP1: {tp1_p:,.2f} | TP2: {tp2_p:,.2f}")
                    print(f"   💬 Council Debate Summary:\n      {debate_summary}\n")

                    # Update persistent state atomically
                    CouncilStateManager.update_symbol_decision(sym, decision)

            time.sleep(1.0)
        except Exception as e:
            print(f"[BACKGROUND WORKER ERROR] {e}")
            time.sleep(2.0)


def run_agentic_trader():
    global _worker_running
    print_banner()

    symbols = CONFIG.SYMBOLS
    print(f"[SYSTEM] Active Trading Symbols: {', '.join(symbols)}")

    # 1. Initialize Engines per Symbol
    data_engines = {}
    exec_engines = {}

    for idx, sym in enumerate(symbols):
        d_eng = MT5DataEngine(symbol=sym)
        if d_eng.connect():
            magic = CONFIG.MAGIC_NUMBER + (idx * 111)
            data_engines[sym] = d_eng
            exec_engines[sym] = MT5ExecutionEngine(symbol=d_eng.symbol, magic_number=magic)
            _rescan_events[sym] = threading.Event()
            _rescan_events[sym].set()  # Initial scan trigger
            print(f"   [OK] Linked {sym} (Resolved: {d_eng.symbol}) | Magic #{magic}")
        else:
            print(f"   [WARN] Could not connect to {sym} on MT5 Market Watch.")

    if not data_engines:
        print("[ERROR] Failed to connect to any symbols on MT5. Ensure MT5 is running.")
        sys.exit(1)

    news_engine = ForexNewsEngine()
    coordinator = MasterCoordinator()
    dual_account_mgr = DualAccountManager(symbol=CONFIG.SYMBOL)

    # 2. Launch Non-Blocking Background Council Deliberation Worker
    delib_thread = threading.Thread(
        target=_async_council_deliberation_worker,
        args=(symbols, data_engines, news_engine, coordinator),
        name="CouncilDeliberationWorker",
        daemon=True
    )
    delib_thread.start()

    print(f"\n[SYSTEM] Dual-Terminal Independent Multi-Account Sniper Engine Active...")
    print(f"   🇪🇺 Account #1: Master EUR (€5,585 Capital) • Mode: STANDARD_PROP (Dynamic Sizing & TP2 Runner)")
    print(f"   🇺🇸 Account #2: GTC Live Micro ($17.10 Capital) • Mode: MICRO_COMPOUNDING (0.01 Lot, $1.50 SL Cap & Instant BE)\n")

    last_heartbeat_time = 0.0
    last_trade_times = {sym: 0.0 for sym in symbols}

    try:
        while True:
            now_ts = time.time()
            current_state = CouncilStateManager.get_state()
            symbols_state = current_state.get("symbols", {})

            for sym, data_engine in data_engines.items():
                # Lightning-fast tick fetch (<0.2ms directly from MT5 memory)
                ticks = data_engine.get_current_spread_and_ticks()
                current_price = float(ticks.get("bid", 0.0) or 0.0)
                if current_price <= 0:
                    continue

                market_payload = {"pricing": ticks, "account": data_engine.get_account_info()}
                news_payload = news_engine.get_news_payload()

                # 3. Independent Dual-Account Active Position Management (Trailing Stop, Early BE, Quick Profit Lock)
                pos_actions = dual_account_mgr.evaluate_and_manage_all_accounts(
                    market_payload=market_payload,
                    news_payload=news_payload
                )
                for act in pos_actions:
                    print(f"\n   🎯 [POSITION ACTION - {act.get('account')}] Ticket #{act.get('ticket')} -> {act.get('type')}")
                    print(f"      💡 Rationale: {act.get('thought')}")
                    print(f"      ⚡ Execution: {act.get('result')}\n")

                # 4. Instant Sniper Trigger Execution for Both Accounts
                sym_setup = symbols_state.get(sym, {})
                setup_action = sym_setup.get("master_action", "HOLD").upper()
                setup_status = sym_setup.get("setup_status", "MONITORING")

                if setup_action in ["BUY", "SELL"] and setup_status in ["HUNTING_PULLBACK", "ACTIVE_SETUP", "HUNTING_SCALE_IN"]:
                    entry_price = float(sym_setup.get("entry_price", current_price) or current_price)
                    sl = float(sym_setup.get("stop_loss", 0.0) or 0.0)
                    tp1 = float(sym_setup.get("take_profit_1", 0.0) or 0.0)
                    tp2 = float(sym_setup.get("take_profit_2", 0.0) or 0.0)
                    consensus_score = int(sym_setup.get("quorum_score", 85))
                    cro_status = sym_setup.get("cro_status", "APPROVED")

                    # Dynamic check if setup already hit TP or drifted far without entry
                    is_target_hit = False
                    if setup_action == "BUY" and tp1 > 0 and current_price >= (tp1 - 0.5):
                        is_target_hit = True
                    elif setup_action == "SELL" and tp1 > 0 and current_price <= (tp1 + 0.5):
                        is_target_hit = True

                    is_drifted = abs(current_price - entry_price) > 15.0

                    if is_target_hit or is_drifted:
                        reason = f"Target {tp1:,.2f} reached or price drifted to {current_price:,.2f} before entry {entry_price:,.2f}."
                        print(f"\n   ⚡ [{sym} SETUP EXPIRED] {reason} Triggering fresh continuation pullback scan...")
                        CouncilStateManager.expire_setup_and_request_pullback_scan(sym, reason)
                        sym_setup["setup_status"] = "EXPIRED_SCANNING"
                        if sym in _rescan_events:
                            _rescan_events[sym].set()
                        continue

                    tolerance = CONFIG.ENTRY_TOLERANCE_POINTS
                    time_since_last_trade = now_ts - last_trade_times.get(sym, 0.0)

                    sniper_state = data_engine.check_m5_candle_confirmation(
                        planned_entry=entry_price,
                        action=setup_action,
                        tolerance_points=tolerance,
                        stop_loss=sl
                    )

                    if cro_status == "APPROVED" and sniper_state["trigger_ready"] and time_since_last_trade >= 90.0:
                        with _ORDER_EXECUTION_LOCK:
                            last_trade_times[sym] = now_ts + 90.0

                            print(f"\n" + "=" * 85)
                            print(f"   🚀 [{sym}] 5-MINUTE CANDLE CONFIRMATION TRIGGER FIRED!")
                            print(f"   Live Price: ${sniper_state['current_price']:,.2f} | M5 Zone: ${sniper_state['zone_str']}")
                            print(f"   📊 5-Candle Momentum: {sniper_state.get('m5_candle_trend')}")
                            print(f"   ⚡ Routing Independent Execution to Both Accounts (Acc #1 Master + Acc #2 Micro)...")
                            print("=" * 85)

                            exec_results = dual_account_mgr.execute_dual_sniper_signal(
                                action=setup_action,
                                entry_price=entry_price,
                                stop_loss=sl,
                                take_profit=tp1,
                                consensus_score=consensus_score,
                                sniper_state=sniper_state
                            )

                            success_count = sum(1 for r in exec_results if r.get("success"))
                            if success_count > 0:
                                CouncilStateManager.set_setup_status(sym, "IN_TRADE", f"{success_count} Account(s) Executed Active")
                            else:
                                last_trade_times[sym] = now_ts

            # Periodic heartbeat (every 15 seconds)
            if now_ts - last_heartbeat_time >= 15.0:
                last_heartbeat_time = now_ts
                now_utc_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                prices_str = " | ".join([f"{s}: ${data_engines[s].get_current_spread_and_ticks().get('bid', 0.0):,.2f}" for s in symbols if s in data_engines])
                print(f"[{now_utc_str}] ⚡ [SNIPER WATCHER] Live: {prices_str} | Dual-Account Independent Loop Active")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping Top 10 Strategy Agents Council gracefully...")
        _worker_running = False
    finally:
        _worker_running = False
        for d_eng in data_engines.values():
            d_eng.disconnect()
        print("[SHUTDOWN] MT5 disconnected. Bot stopped.")


if __name__ == "__main__":
    run_agentic_trader()
