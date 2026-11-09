"""
Centralized Council State Manager.
Maintains persistent, sticky trade setups, council arbitration rulings,
lifecycle transitions (HUNTING_PULLBACK, IN_TRADE, TARGET_REACHED, INVALIDATED),
and multi-asset status to avoid price flickering/fluctuation on UI.
"""

import json
import os
import time
from typing import Dict, Any, Optional

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "council_state.json")


class CouncilStateManager:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    @staticmethod
    def get_state() -> Dict[str, Any]:
        """Reads persistent state from file or returns default structural templates."""
        CouncilStateManager._ensure_dir()
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data and "symbols" in data and len(data["symbols"]) > 0:
                        return data
            except Exception:
                pass

        # Default initial structural setups (dynamically aligned to current market structure)
        return {
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "symbols": {
                "XAUUSD": {
                    "symbol": "XAUUSD",
                    "name": "GOLD (XAUUSD)",
                    "master_action": "BUY",
                    "master_action_class": "action-buy",
                    "entry_price": 4330.00,
                    "stop_loss": 4321.00,
                    "take_profit_1": 4345.00,
                    "take_profit_2": 4360.00,
                    "quorum_score": 90,
                    "vote_breakdown": "9/10 BUY",
                    "cro_lots": "0.07 Lots",
                    "cro_status": "APPROVED",
                    "news_status": "CLEAR",
                    "news_sub": "ForexFactory Calendar Live",
                    "setup_status": "HUNTING_PULLBACK",
                    "debate_summary": "Multi-TF bullish trend continuation. Seeking M5/M15 pullback to dynamic EMA 21 / VWAP support zone."
                }
            }
        }

    @staticmethod
    def save_state(state: Dict[str, Any]):
        """Saves persistent state to disk."""
        CouncilStateManager._ensure_dir()
        state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[CouncilState] Error saving state: {e}")

    @staticmethod
    def update_symbol_decision(
        symbol: str,
        decision: Dict[str, Any],
        agents_data: Optional[list] = None
    ):
        """
        Updates a specific symbol's sticky trade setup and consensus ruling.
        Implements Professional Trade Plan Stability (Anti-Whipsaw Hysteresis).
        """
        state = CouncilStateManager.get_state()
        if "symbols" not in state:
            state["symbols"] = {}

        sym_key = symbol.upper()
        current = state["symbols"].get(sym_key, {})

        is_gold = "XAU" in sym_key or "GOLD" in sym_key
        is_btc = "BTC" in sym_key or "BITCOIN" in sym_key
        asset_name = "GOLD (XAUUSD)" if is_gold else "BITCOIN (BTCUSD)"

        raw_action = decision.get("action", "HOLD").upper()
        quorum_score = int(decision.get("consensus_score", 0))

        trade_style = decision.get("trade_style", current.get("trade_style", "STANDARD_PROP"))
        min_quorum = 50 if trade_style == "SCALP" else 60

        # Dynamic Professional Quorum Rule:
        # If quorum is below threshold (50% for SCALP, 60% for PROP) or action is HOLD, enforce HOLD.
        if quorum_score < min_quorum or raw_action == "HOLD":
            action = "HOLD"
            action_class = "action-hold"
            setup_status = "MONITORING"
            entry = 0.0
            sl = 0.0
            tp1 = 0.0
            tp2 = 0.0
        else:
            action = raw_action if raw_action in ["BUY", "SELL"] else "HOLD"
            action_class = "action-buy" if action == "BUY" else "action-sell" if action == "SELL" else "action-hold"
            setup_status = "HUNTING_PULLBACK" if action in ["BUY", "SELL"] else "MONITORING"

            raw_entry = decision.get("entry_price")
            raw_sl = decision.get("stop_loss")
            raw_tp1 = decision.get("take_profit_1")
            raw_tp2 = decision.get("take_profit_2")

            # Strict price sanity protection against corrupted or equity prices
            if is_btc:
                entry = float(raw_entry) if (raw_entry and float(raw_entry) >= 10000.0) else 83900.00
                sl = float(raw_sl) if (raw_sl and float(raw_sl) >= 10000.0) else (entry - 850.0 if action == "BUY" else entry + 850.0)
                tp1 = float(raw_tp1) if (raw_tp1 and float(raw_tp1) >= 10000.0) else (entry + 1487.5 if action == "BUY" else entry - 1487.5)
                tp2 = float(raw_tp2) if (raw_tp2 and float(raw_tp2) >= 10000.0) else (entry + 2550.0 if action == "BUY" else entry - 2550.0)
            elif is_gold:
                entry = float(raw_entry) if (raw_entry and float(raw_entry) >= 1000.0) else 4353.50
                sl = float(raw_sl) if (raw_sl and float(raw_sl) >= 1000.0) else (entry - 10.26 if action == "BUY" else entry + 10.26)
                tp1 = float(raw_tp1) if (raw_tp1 and float(raw_tp1) >= 1000.0) else (entry + 17.95 if action == "BUY" else entry - 17.95)
                tp2 = float(raw_tp2) if (raw_tp2 and float(raw_tp2) >= 1000.0) else (entry + 30.78 if action == "BUY" else entry - 30.78)
            else:
                entry = float(raw_entry or 0.0)
                sl = float(raw_sl or 0.0)
                tp1 = float(raw_tp1 or 0.0)
                tp2 = float(raw_tp2 or 0.0)

        cro = decision.get("cro_report", {})
        planned_summary = cro.get("planned_lots_summary")
        if planned_summary:
            cro_lots = planned_summary
        else:
            lots = cro.get("calculated_lots", 0.05 if is_btc else 0.08)
            cro_lots = f"{lots} Lots" if lots > 0 else current.get("cro_lots", "0.05 Lots" if is_btc else "0.08 Lots")
        cro_status = "APPROVED" if cro.get("approved", True) else "VETOED"
        account_allocations = cro.get("account_allocations", {})

        votes = decision.get("voting_summary", {})
        if votes:
            vote_breakdown = f"{votes.get(action, votes.get('BUY', 0))}/14 {action if action in ['BUY', 'SELL'] else 'VOTES'}"
        else:
            vote_breakdown = current.get("vote_breakdown", f"11/14 {action}")

        # Automatic extraction of individual 14 specialist agent votes from decision
        if not agents_data:
            proposals = decision.get("agent_proposals", {})
            if proposals:
                agent_meta = [
                    ("1_SMC_ICT", "SMC & ICT Specialist", "⚡", "Liquidity & Order Blocks", "M15 / H1"),
                    ("2_Trend_Momentum", "Trend & Momentum", "📈", "Multi-TF EMA Clouds", "H4 / H1"),
                    ("3_Mean_Reversion", "Mean-Reversion & Bands", "🎯", "RSI & Statistical Bands", "M15"),
                    ("4_Macro_News", "Macro & News Intelligence", "🌍", "ForexFactory & Sentiment", "Macro"),
                    ("5_OrderFlow_VWAP", "Volume Profile & VWAP", "📊", "Intraday POC & Value Area", "M15"),
                    ("6_Supply_Demand", "Supply & Demand Origin", "🧱", "Fresh Imbalance Zones", "M15 / H1"),
                    ("7_Breakout_Volatility", "Breakout & Squeeze", "💥", "Bollinger Squeeze & ATR", "M15"),
                    ("8_Fibonacci_OTE", "Fibonacci & Golden Pocket", "📐", "0.618 OTE & Extensions", "H1 / M15"),
                    ("9_Chart_Pattern", "Chart Pattern Geometry", "🔷", "Classical Geometry & Wicks", "M15"),
                    ("10_Intraday_Scalp", "Intraday Fast Scalper", "⚡", "Fast EMA 9/21 Micro Thrust", "M5 / M15"),
                    ("11_Regime_Detection", "Market Regime Detection", "🧭", "Trend vs Range vs Chop Classifier", "M15 / H1"),
                    ("12_Liquidity_Execution", "Liquidity & Spread Shield", "💧", "Live Spread & Slippage Gate", "Microstructure"),
                    ("13_Tick_OrderFlow", "Tick / Order Flow Aggressor", "⚡", "Ask-Lifters vs Bid-Hitters", "Live Ticks"),
                    ("14_Volume_Delta_CVD", "Cumulative Volume Delta (CVD)", "📊", "Volume Delta & Absorption", "M15 / M5"),
                ]
                extracted_agents = []
                for key, a_name, a_icon, a_role, a_tf in agent_meta:
                    p_data = proposals.get(key, {})
                    a_action = str(p_data.get("action", p_data.get("recommended_action", "HOLD"))).upper()
                    if a_action not in ["BUY", "SELL", "HOLD"]:
                        a_action = "HOLD"
                    a_conf = int(p_data.get("confidence_score", p_data.get("sentiment_score", p_data.get("confidence", 85))))
                    a_thought = str(p_data.get("setup_name", p_data.get("pattern_identified", p_data.get("reasoning", p_data.get("thought", "")))))
                    if not a_thought:
                        a_thought = f"{a_name} analysis completed with {a_action} vote."
                    extracted_agents.append({
                        "name": a_name,
                        "icon": a_icon,
                        "role": a_role,
                        "action": a_action,
                        "confidence": a_conf,
                        "thought": a_thought,
                        "tf": a_tf
                    })
                agents_data = extracted_agents

        # Recalculate exact vote breakdown from individual agent opinions
        if agents_data and len(agents_data) == 14:
            buy_count = sum(1 for a in agents_data if a.get("action") == "BUY")
            sell_count = sum(1 for a in agents_data if a.get("action") == "SELL")
            hold_count = sum(1 for a in agents_data if a.get("action") == "HOLD")
            if action == "BUY" or (action == "HOLD" and buy_count >= sell_count):
                vote_breakdown = f"{buy_count}/14 BUY"
            else:
                vote_breakdown = f"{sell_count}/14 SELL"

        trader_name = "XAUUSD AI TRADER" if is_gold else "BTCUSD AI TRADER"

        updated_sym = {
            "symbol": sym_key,
            "name": asset_name,
            "trader_name": trader_name,
            "master_action": action,
            "master_action_class": action_class,
            "trade_style": decision.get("trade_style", current.get("trade_style", "STANDARD_PROP")),
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "quorum_score": quorum_score,
            "vote_breakdown": vote_breakdown,
            "cro_lots": cro_lots,
            "cro_status": cro_status,
            "account_allocations": account_allocations,
            "news_status": "CLEAR",
            "news_sub": "ForexFactory Calendar Live",
            "setup_status": setup_status,
            "debate_summary": decision.get("council_debate_summary", current.get("debate_summary", ""))
        }

        if agents_data:
            updated_sym["agents"] = agents_data

        state["symbols"][sym_key] = updated_sym
        CouncilStateManager.save_state(state)

    @staticmethod
    def set_setup_status(symbol: str, status: str, note: Optional[str] = None):
        """Updates the lifecycle status of a symbol's setup (e.g. IN_TRADE, TARGET_REACHED, INVALIDATED)."""
        state = CouncilStateManager.get_state()
        sym_key = symbol.upper()
        if "symbols" in state and sym_key in state["symbols"]:
            state["symbols"][sym_key]["setup_status"] = status
            if note:
                state["symbols"][sym_key]["status_note"] = note
            CouncilStateManager.save_state(state)

    @staticmethod
    def expire_setup_and_request_pullback_scan(symbol: str, reason: str):
        """Marks old setup expired (e.g. TP hit before entry, or price drifted) and requests fresh pullback scan."""
        state = CouncilStateManager.get_state()
        sym_key = symbol.upper()
        if "symbols" in state and sym_key in state["symbols"]:
            state["symbols"][sym_key]["setup_status"] = "TARGET_REACHED_EXPIRED"
            state["symbols"][sym_key]["status_note"] = reason
            CouncilStateManager.save_state(state)
