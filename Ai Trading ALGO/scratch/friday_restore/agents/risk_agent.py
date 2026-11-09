"""
Chief Risk Officer (CRO) Agent for XAUUSD Trading Council.
Calculates dynamic lot sizing, validates mathematical Stop Loss / Take Profit parameters,
enforces daily drawdown ceilings, and acts as the final gatekeeper for trade risk.
"""

from typing import Dict, Any, Tuple, Optional
import math
from config import CONFIG
try:
    from core.risk_manager import RiskManager
except ImportError:
    from risk_manager import RiskManager



class ChiefRiskOfficerAgent:
    def __init__(self, symbol: str = CONFIG.SYMBOL):
        self.symbol = symbol
        self.risk_manager = RiskManager(symbol=symbol)

    def evaluate_and_size_trade(
        self,
        proposal: Dict[str, Any],
        account_info: Dict[str, Any],
        current_spread_points: float,
        open_positions_count: int,
        day_of_month: int
    ) -> Dict[str, Any]:
        """
        Evaluates a strategy proposal, calculates the exact lot size, and validates all risk parameters.
        Returns a structured CRO clearance report.
        """
        action = proposal.get("action", "HOLD").upper()

        if action == "HOLD":
            return {
                "agent_name": "Chief_Risk_Officer",
                "approved": True,
                "action": "HOLD",
                "reason": "Proposal is HOLD. No risk exposure.",
                "calculated_lots": 0.0,
                "risk_amount_usd": 0.0,
                "risk_reward_ratio": 0.0,
                "max_drawdown_status": "NORMAL"
            }

        equity = account_info.get("equity", 0.0)
        entry = proposal.get("entry_price", 0.0)
        sl = proposal.get("stop_loss", 0.0)
        tp1 = proposal.get("take_profit_1", 0.0)
        tp2 = proposal.get("take_profit_2", 0.0)
        target_risk_pct = proposal.get("risk_percent", CONFIG.MAX_RISK_PER_TRADE_PCT)

        # 1. Check Max Open Trades
        if open_positions_count >= CONFIG.MAX_OPEN_TRADES:
            return {
                "agent_name": "Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Max concurrent open positions reached ({open_positions_count}/{CONFIG.MAX_OPEN_TRADES}).",
                "calculated_lots": 0.0
            }

        # 2. Check Daily Drawdown
        self.risk_manager.update_daily_equity(equity, day_of_month)
        is_breached, dd_pct = self.risk_manager.check_daily_drawdown(equity)
        if is_breached:
            return {
                "agent_name": "Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Daily account drawdown limit breached ({dd_pct}% >= {CONFIG.MAX_DAILY_DRAWDOWN_PCT}%). Lockout active.",
                "calculated_lots": 0.0
            }

        # 3. Check Spread Filter
        if current_spread_points > CONFIG.MAX_SPREAD_POINTS:
            return {
                "agent_name": "Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Spread too wide ({current_spread_points} pts > {CONFIG.MAX_SPREAD_POINTS} pts max).",
                "calculated_lots": 0.0
            }

        # 4. Invalidation and Direction checks
        if entry <= 0 or sl <= 0 or tp1 <= 0:
            return {
                "agent_name": "Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": "Missing required Entry, Stop Loss, or Take Profit 1.",
                "calculated_lots": 0.0
            }

        if action == "BUY" and (sl >= entry or tp1 <= entry):
            return {
                "agent_name": "Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Invalid BUY prices: SL ({sl}) must be < Entry ({entry}) < TP1 ({tp1}).",
                "calculated_lots": 0.0
            }

        if action == "SELL" and (sl <= entry or tp1 >= entry):
            return {
                "agent_name": "Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Invalid SELL prices: SL ({sl}) must be > Entry ({entry}) > TP1 ({tp1}).",
                "calculated_lots": 0.0
            }

        # 5. Risk:Reward Ratio Calculation
        risk_dist = abs(entry - sl)
        reward_dist = abs(tp1 - entry)
        rr_ratio = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        if rr_ratio < CONFIG.MIN_RISK_REWARD_RATIO:
            # Auto-calibrate TP1 to satisfy the mandatory minimum RR ratio
            tp1 = round(entry + (risk_dist * CONFIG.MIN_RISK_REWARD_RATIO), 2) if action == "BUY" else round(entry - (risk_dist * CONFIG.MIN_RISK_REWARD_RATIO), 2)
            proposal["take_profit_1"] = tp1
            reward_dist = abs(tp1 - entry)
            rr_ratio = CONFIG.MIN_RISK_REWARD_RATIO

        # 6. Dynamic Lot Size Calculation with Probability Scaling (Capped at 0.10 max)
        confidence = float(proposal.get("confidence_score") or proposal.get("consensus_score") or 85.0)
        calculated_lots = self.risk_manager.calculate_lot_size(
            account_equity=equity,
            entry_price=entry,
            stop_loss=sl,
            risk_pct=target_risk_pct,
            confidence_score=confidence
        )
        risk_amount_usd = round(equity * (target_risk_pct / 100.0), 2)

        return {
            "agent_name": "Chief_Risk_Officer",
            "approved": True,
            "action": action,
            "reason": f"Trade cleared by CRO. Risk: {target_risk_pct}% (${risk_amount_usd}) | Probability-Scaled Lots: {calculated_lots} (Cap: {CONFIG.MAX_LOT_SIZE} max) | RR: {rr_ratio}:1 | Confidence: {confidence}%",
            "calculated_lots": calculated_lots,

            "risk_amount_usd": risk_amount_usd,
            "risk_reward_ratio": rr_ratio,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "equity": equity
        }
