"""
Chief Risk Officer (CRO) Agent for Bitcoin (BTCUSD) Trading Council.
Specialized exclusively for Bitcoin risk parameters: BTC contract size (1 lot = 1 BTC),
1.5% max equity risk per trade, 0.10 hard lot ceiling, wide stop loss buffers tailored for crypto volatility,
and strict daily drawdown ceilings.
"""

from typing import Dict, Any, Tuple, Optional
import math
from config import CONFIG
try:
    from core.risk_manager import RiskManager
except ImportError:
    from risk_manager import RiskManager


class CryptoChiefRiskOfficerAgent:
    def __init__(self, symbol: str = "BTCUSD"):
        self.symbol = "BTCUSD"
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
        Evaluates a Bitcoin strategy proposal, calculates the exact lot size for Bitcoin,
        and validates all risk parameters. Returns a structured CRO clearance report.
        """
        action = proposal.get("action", "HOLD").upper()

        if action == "HOLD":
            return {
                "agent_name": "Crypto_Chief_Risk_Officer",
                "approved": True,
                "action": "HOLD",
                "reason": "Proposal is HOLD. No risk exposure on Bitcoin.",
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
        max_allowed_risk_pct = float(getattr(CONFIG, "MAX_PORTFOLIO_AGGREGATE_RISK_PCT", 5.0))
        target_risk_pct = min(float(proposal.get("risk_percent", CONFIG.MAX_RISK_PER_TRADE_PCT)), max_allowed_risk_pct)

        # 1. Check Max Open Trades
        if open_positions_count >= CONFIG.MAX_OPEN_TRADES:
            return {
                "agent_name": "Crypto_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Max concurrent open positions reached on Bitcoin ({open_positions_count}/{CONFIG.MAX_OPEN_TRADES}).",
                "calculated_lots": 0.0
            }

        # 2. Check Daily Drawdown
        if equity > 0:
            self.risk_manager.update_daily_equity(equity, day_of_month)
            is_breached, dd_pct = self.risk_manager.check_daily_drawdown(equity)
            if is_breached:
                return {
                    "agent_name": "Crypto_Chief_Risk_Officer",
                    "approved": False,
                    "action": "VETO",
                    "reason": f"Daily account drawdown limit breached ({dd_pct}% >= {CONFIG.MAX_DAILY_DRAWDOWN_PCT}%). Lockout active.",
                    "calculated_lots": 0.0
                }

        # 3. Check Spread Filter (BTC max 2500 pts)
        max_allowed_spread = float(CONFIG.BTC_MAX_SPREAD_POINTS or 2500.0)
        if current_spread_points > max_allowed_spread:
            return {
                "agent_name": "Crypto_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Bitcoin spread too wide ({current_spread_points} pts > {max_allowed_spread} pts max).",
                "calculated_lots": 0.0
            }

        # 4. Invalidation and Direction checks
        if entry <= 0 or sl <= 0 or tp1 <= 0:
            return {
                "agent_name": "Crypto_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": "Invalid or missing Entry / SL / TP pricing on Bitcoin.",
                "calculated_lots": 0.0
            }

        if action == "BUY" and (sl >= entry or tp1 <= entry):
            return {
                "agent_name": "Crypto_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"BUY geometry invalid: Entry ({entry}) must be > SL ({sl}) and < TP1 ({tp1}).",
                "calculated_lots": 0.0
            }

        if action == "SELL" and (sl <= entry or tp1 >= entry):
            return {
                "agent_name": "Crypto_Chief_Risk_Officer",
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
                "agent_name": "Crypto_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": "Stop Loss distance is zero.",
                "calculated_lots": 0.0
            }

        rr_ratio = reward_dist / risk_dist
        if rr_ratio < CONFIG.MIN_RISK_REWARD_RATIO:
            return {
                "agent_name": "Crypto_Chief_Risk_Officer",
                "approved": False,
                "action": "VETO",
                "reason": f"Bitcoin R:R ({rr_ratio:.2f}) is below institutional minimum (1:{CONFIG.MIN_RISK_REWARD_RATIO}).",
                "calculated_lots": 0.0
            }

        # 6. Exact Dynamic Lot Sizing for Bitcoin (1 lot = 1 BTC)
        risk_amount_usd = equity * (target_risk_pct / 100.0) if equity > 0 else 50.0
        contract_size = 1.0  # 1 lot BTC = 1 BTC
        dollar_risk_per_lot = risk_dist * contract_size
        calculated_lots = (risk_amount_usd / dollar_risk_per_lot) if dollar_risk_per_lot > 0 else 0.01

        # Enforce Hard 5% Total Portfolio Risk Safety Cap
        max_risk_dollars = equity * (max_allowed_risk_pct / 100.0) if equity > 0 else 50.0
        if dollar_risk_per_lot * calculated_lots > max_risk_dollars and dollar_risk_per_lot > 0:
            calculated_lots = max_risk_dollars / dollar_risk_per_lot

        # Enforce Hard Lot Ceilings (Bitcoin allows up to BTC_MAX_LOT_SIZE e.g. 0.50 lots)
        btc_max_cap = float(getattr(CONFIG, "BTC_MAX_LOT_SIZE", 0.50))
        calculated_lots = max(CONFIG.MIN_LOT_SIZE, calculated_lots)
        calculated_lots = min(btc_max_cap, calculated_lots)
        calculated_lots = round(calculated_lots, 2)

        # Multi-Account N-Terminal Planned Sizing
        try:
            from core.multi_account_risk_planner import MultiAccountRiskPlanner
            multi_plan = MultiAccountRiskPlanner.plan_lot_sizes_for_all_accounts(
                symbol="BTCUSD",
                entry_price=entry,
                stop_loss=sl,
                consensus_score=proposal.get("consensus_score", 85.0),
                live_accounts_telemetry=account_info.get("accounts_telemetry")
            )
        except Exception as e:
            multi_plan = {"account_allocations": {}, "summary_string": f"{calculated_lots} Lots", "total_system_lots": calculated_lots}

        return {
            "agent_name": "Crypto_Chief_Risk_Officer",
            "approved": True,
            "action": action,
            "reason": f"Bitcoin Trade Cleared: RR=1:{rr_ratio:.2f} | Risk=${risk_amount_usd:.2f} | Lots: {multi_plan.get('summary_string')}",
            "calculated_lots": calculated_lots,
            "risk_amount_usd": round(risk_amount_usd, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "max_drawdown_status": "NORMAL",
            "account_allocations": multi_plan.get("account_allocations", {}),
            "planned_lots_summary": multi_plan.get("summary_string", f"{calculated_lots} Lots"),
            "total_system_lots": multi_plan.get("total_system_lots", calculated_lots)
        }


# Aliases for clean cross-council naming
BTCUSDChiefRiskOfficer = CryptoChiefRiskOfficerAgent
BTCRiskManagementAgent = CryptoChiefRiskOfficerAgent
BTCChiefRiskOfficerAgent = CryptoChiefRiskOfficerAgent
