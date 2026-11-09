"""
Chief Risk Officer (CRO) Agent for Gold (XAUUSD) Trading Council.
Specialized exclusively for Gold risk parameters: Gold point value ($1.0 pt = $100 per lot),
1.5% max equity risk per trade, 0.10 hard lot ceiling, and strict Gold daily drawdown ceilings.
"""

from typing import Dict, Any, Tuple, Optional
import math
from config import CONFIG
try:
    from core.risk_manager import RiskManager
except ImportError:
    from risk_manager import RiskManager


class GoldChiefRiskOfficerAgent:
    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = "XAUUSD"
        self.risk_manager = RiskManager(symbol=self.symbol)

    def evaluate_and_size_trade(
        self,
        proposal: Dict[str, Any],
        account_info: Dict[str, Any],
        current_spread_points: float,
        open_positions_count: int,
        day_of_month: int
    ) -> Dict[str, Any]:
        """
        Evaluates a Gold strategy proposal, calculates the exact lot size for Gold,
        and validates all risk parameters. Returns a structured CRO clearance report.
        """
        action = proposal.get("action", "HOLD").upper()

        if action == "HOLD":
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": True,
                "action": "HOLD",
                "reason": "Proposal is HOLD. No risk exposure on Gold.",
                "calculated_lots": 0.0,
                "risk_amount_usd": 0.0,
                "risk_reward_ratio": 0.0,
                "max_drawdown_status": "NORMAL"
            }

        equity = account_info.get("equity", 0.0)
        entry = proposal.get("entry_price", 0.0)
        sl = proposal.get("stop_loss", 0.0)
        tp1 = proposal.get("take_profit_1", 0.0)
        max_allowed_risk_pct = float(getattr(CONFIG, "MAX_PORTFOLIO_AGGREGATE_RISK_PCT", 5.0))
        target_risk_pct = min(float(proposal.get("risk_percent", CONFIG.MAX_RISK_PER_TRADE_PCT)), max_allowed_risk_pct)

        # 1. Check Max Open Trades
        if open_positions_count >= CONFIG.MAX_OPEN_TRADES:
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Max concurrent open positions reached on Gold ({open_positions_count}/{CONFIG.MAX_OPEN_TRADES}).",
                "calculated_lots": 0.0
            }

        # 2. Check Daily Drawdown
        if equity > 0:
            self.risk_manager.update_daily_equity(equity, day_of_month)
            is_breached, dd_pct = self.risk_manager.check_daily_drawdown(equity)
            if is_breached:
                return {
                    "agent_name": "Gold_Chief_Risk_Officer",
                    "approved": False,
                    "action": "VETO",
                    "reason": f"Daily account drawdown limit breached ({dd_pct}% >= {CONFIG.MAX_DAILY_DRAWDOWN_PCT}%). Lockout active.",
                    "calculated_lots": 0.0
                }

        # 3. Check Spread Filter (Gold max 45 pts)
        max_allowed_spread = float(CONFIG.MAX_SPREAD_POINTS or 45.0)
        if current_spread_points > max_allowed_spread:
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Gold spread too wide ({current_spread_points} pts > {max_allowed_spread} pts max).",
                "calculated_lots": 0.0
            }

        # 4. Invalidation and Direction checks
        if entry <= 0 or sl <= 0 or tp1 <= 0:
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": "Invalid or missing Entry / SL / TP pricing.",
                "calculated_lots": 0.0
            }

        if action == "BUY" and (sl >= entry or tp1 <= entry):
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"BUY geometry invalid: Entry ({entry}) must be > SL ({sl}) and < TP1 ({tp1}).",
                "calculated_lots": 0.0
            }

        if action == "SELL" and (sl <= entry or tp1 >= entry):
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"SELL geometry invalid: Entry ({entry}) must be < SL ({sl}) and > TP1 ({tp1}).",
                "calculated_lots": 0.0
            }

        # 5. Risk / Reward Calculation
        risk_dist = abs(entry - sl)
        reward_dist = abs(tp1 - entry)
        if risk_dist <= 0:
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": "Stop Loss distance is zero.",
                "calculated_lots": 0.0
            }

        rr_ratio = reward_dist / risk_dist
        if rr_ratio < CONFIG.MIN_RISK_REWARD_RATIO:
            return {
                "agent_name": "Gold_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Gold R:R ({rr_ratio:.2f}) is below institutional minimum (1:{CONFIG.MIN_RISK_REWARD_RATIO}).",
                "calculated_lots": 0.0
            }

        # 6. Exact Dynamic Lot Sizing for Gold ($1.0 pt = $100 per standard lot)
        risk_amount_usd = equity * (target_risk_pct / 100.0) if equity > 0 else 50.0
        # For Gold 1 standard lot = 100 oz. 1 point move = $100 per lot.
        contract_size = 100.0
        dollar_risk_per_lot = risk_dist * contract_size
        calculated_lots = (risk_amount_usd / dollar_risk_per_lot) if dollar_risk_per_lot > 0 else 0.01

        # Enforce Hard 5% Total Portfolio Risk Safety Cap
        max_risk_dollars = equity * (max_allowed_risk_pct / 100.0) if equity > 0 else 50.0
        if dollar_risk_per_lot * calculated_lots > max_risk_dollars and dollar_risk_per_lot > 0:
            calculated_lots = max_risk_dollars / dollar_risk_per_lot

        # Enforce Hard Lot Ceilings
        calculated_lots = max(CONFIG.MIN_LOT_SIZE, calculated_lots)
        calculated_lots = min(CONFIG.MAX_LOT_SIZE, calculated_lots)
        calculated_lots = round(calculated_lots, 2)

        # Multi-Account N-Terminal Planned Sizing
        try:
            from core.multi_account_risk_planner import MultiAccountRiskPlanner
            multi_plan = MultiAccountRiskPlanner.plan_lot_sizes_for_all_accounts(
                symbol="XAUUSD",
                entry_price=entry,
                stop_loss=sl,
                consensus_score=proposal.get("consensus_score", 85.0),
                live_accounts_telemetry=account_info.get("accounts_telemetry")
            )
        except Exception as e:
            multi_plan = {"account_allocations": {}, "summary_string": f"{calculated_lots} Lots", "total_system_lots": calculated_lots}

        return {
            "agent_name": "Gold_Chief_Risk_Officer",
            "approved": True,
            "action": action,
            "reason": f"Gold Trade Cleared: RR=1:{rr_ratio:.2f} | Risk=${risk_amount_usd:.2f} | Lots: {multi_plan.get('summary_string')}",
            "calculated_lots": calculated_lots,
            "risk_amount_usd": round(risk_amount_usd, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "max_drawdown_status": "NORMAL",
            "account_allocations": multi_plan.get("account_allocations", {}),
            "planned_lots_summary": multi_plan.get("summary_string", f"{calculated_lots} Lots"),
            "total_system_lots": multi_plan.get("total_system_lots", calculated_lots)
        }


# Aliases for clean cross-council naming
XAUUSDChiefRiskOfficer = GoldChiefRiskOfficerAgent
GoldRiskManagementAgent = GoldChiefRiskOfficerAgent
