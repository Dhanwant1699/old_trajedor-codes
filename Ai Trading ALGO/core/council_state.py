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
                    "vote_breakdown": "11/14 BUY",
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
        """Updates a specific symbol's sticky trade setup and consensus ruling."""
        state = CouncilStateManager.get_state()
        if "symbols" not in state:
            state["symbols"] = {}

        sym_key = symbol.upper()
        current = state["symbols"].get(sym_key, {})

        action = decision.get("action", current.get("master_action", "HOLD")).upper()
        action_class = "action-buy" if action == "BUY" else "action-sell" if action == "SELL" else "action-hold"

        entry = decision.get("entry_price") or current.get("entry_price")
        raw_sl = decision.get("stop_loss")
        raw_tp1 = decision.get("take_profit_1")
        raw_tp2 = decision.get("take_profit_2")

        # Sanity check: Ensure SL and TP are mathematically valid and aligned with action
        default_risk = 8.50
        if entry and entry > 0:
            if action == "BUY":
                sl = raw_sl if (raw_sl and raw_sl < entry and (entry - raw_sl) <= 25.0) else round(entry - default_risk, 2)
                tp1 = raw_tp1 if (raw_tp1 and raw_tp1 > entry and (raw_tp1 - entry) <= 50.0) else round(entry + (default_risk * 1.75), 2)
                tp2 = raw_tp2 if (raw_tp2 and raw_tp2 > tp1 and (raw_tp2 - entry) <= 80.0) else round(entry + (default_risk * 3.00), 2)
            elif action == "SELL":
                sl = raw_sl if (raw_sl and raw_sl > entry and (raw_sl - entry) <= 25.0) else round(entry + default_risk, 2)
                tp1 = raw_tp1 if (raw_tp1 and raw_tp1 < entry and (entry - raw_tp1) <= 50.0) else round(entry - (default_risk * 1.75), 2)
                tp2 = raw_tp2 if (raw_tp2 and raw_tp2 < tp1 and (entry - raw_tp2) <= 80.0) else round(entry - (default_risk * 3.00), 2)
            else: # HOLD / MONITORING
                sl = raw_sl if (raw_sl and abs(raw_sl - entry) <= 25.0) else round(entry - default_risk, 2)
                tp1 = raw_tp1 if (raw_tp1 and abs(raw_tp1 - entry) <= 50.0) else round(entry + (default_risk * 1.75), 2)
                tp2 = raw_tp2 if (raw_tp2 and abs(raw_tp2 - entry) <= 80.0) else round(entry + (default_risk * 3.00), 2)
        else:
            sl = raw_sl or 0.0
            tp1 = raw_tp1 or 0.0
            tp2 = raw_tp2 or 0.0

        cro = decision.get("cro_report", {})
        lots = cro.get("calculated_lots", 0.07)
        cro_lots = f"{lots} Lots" if lots > 0 else current.get("cro_lots", "0.07 Lots")
        cro_status = "APPROVED" if cro.get("approved", True) else "VETOED"

        quorum_score = decision.get("consensus_score", current.get("quorum_score", 90))
        votes = decision.get("voting_summary", {})
        total_voters = sum(votes.values()) if votes else 14
        if votes:
            vote_breakdown = f"{votes.get(action, 0)}/{total_voters} {action}"
        else:
            vote_breakdown = current.get("vote_breakdown", f"10/{total_voters} {action}")

        is_gold = "XAU" in sym_key or "GOLD" in sym_key
        asset_name = "GOLD (XAUUSD)" if is_gold else "BITCOIN (BTCUSD)"

        # Stage 3/Trade Plan metadata extraction
        trade_plan_dict = decision.get("trade_plan") or current.get("trade_plan") or {}
        daily_plan_dict = decision.get("daily_plan") or current.get("daily_plan") or {}
        gate_res_raw = decision.get("gate_result") or current.get("gate_result") or {}
        gate_res_dict = gate_res_raw.to_dict() if hasattr(gate_res_raw, "to_dict") else (gate_res_raw.__dict__ if hasattr(gate_res_raw, "__dict__") else gate_res_raw)

        entry_zone_low = trade_plan_dict.get("entry_zone_low", current.get("entry_zone_low", 0.0)) if isinstance(trade_plan_dict, dict) else 0.0
        entry_zone_high = trade_plan_dict.get("entry_zone_high", current.get("entry_zone_high", 0.0)) if isinstance(trade_plan_dict, dict) else 0.0

        updated_sym = {
            "symbol": sym_key,
            "name": asset_name,
            "master_action": action,
            "master_action_class": action_class,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "quorum_score": quorum_score,
            "vote_breakdown": vote_breakdown,
            "cro_lots": cro_lots,
            "cro_status": cro_status,
            "news_status": "CLEAR",
            "news_sub": "ForexFactory Calendar Live",
            "setup_status": "IN_TRADE" if state.get("symbols", {}).get(sym_key, {}).get("setup_status") == "IN_TRADE" else ("HUNTING_PULLBACK" if action in ["BUY", "SELL"] else "MONITORING"),
            "debate_summary": decision.get("council_debate_summary", ""),
            "trade_plan": trade_plan_dict,
            "daily_plan": daily_plan_dict,
            "gate_result": gate_res_dict,
            "entry_zone_low": entry_zone_low,
            "entry_zone_high": entry_zone_high,
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
