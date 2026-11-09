"""
Risk Management Engine for Claude XAUUSD AI Trader.
Enforces institutional capital preservation, dynamic lot sizing,
minimum Risk:Reward constraints, spread filters, and daily drawdown limits.
"""

from typing import Dict, Any, Tuple, Optional
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config import CONFIG


class RiskManager:
    def __init__(self, symbol: str = CONFIG.SYMBOL):
        self.symbol = symbol
        self.daily_start_equity: Optional[float] = None
        self.last_reset_day: Optional[int] = None

    def update_daily_equity(self, current_equity: float, current_day: int):
        """Resets daily starting equity at the beginning of each day."""
        if self.last_reset_day != current_day or self.daily_start_equity is None:
            self.daily_start_equity = current_equity
            self.last_reset_day = current_day

    def check_daily_drawdown(self, current_equity: float) -> Tuple[bool, float]:
        """
        Checks if current account equity has breached the daily drawdown limit.
        Returns: (is_breached, current_drawdown_pct)
        """
        if not self.daily_start_equity or self.daily_start_equity <= 0:
            return False, 0.0

        drawdown = (self.daily_start_equity - current_equity) / self.daily_start_equity * 100.0
        if drawdown >= CONFIG.MAX_DAILY_DRAWDOWN_PCT:
            return True, round(drawdown, 2)
        return False, round(drawdown, 2)

    def calculate_lot_size(
        self,
        account_equity: float,
        entry_price: float,
        stop_loss: float,
        risk_pct: float = CONFIG.MAX_RISK_PER_TRADE_PCT
    ) -> float:
        """
        Dynamically calculates the exact lot size based on equity and distance to Stop Loss.
        Fetches contract size and lot steps directly from MT5 symbol specifications.
        """
        if entry_price <= 0 or stop_loss <= 0 or account_equity <= 0:
            return 0.01

        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            return 0.01

        # Default standard specs for Gold if MT5 symbol_info is offline
        contract_size = 100.0
        min_lot = 0.01
        max_lot = 100.0
        lot_step = 0.01

        if mt5:
            info = mt5.symbol_info(self.symbol)
            if info:
                contract_size = info.trade_contract_size or 100.0
                min_lot = info.volume_min or 0.01
                max_lot = info.volume_max or 100.0
                lot_step = info.volume_step or 0.01

        # Dollar risk amount
        risk_amount = account_equity * (risk_pct / 100.0)

        # Loss per 1.0 standard lot = sl_distance * contract_size
        loss_per_lot = sl_distance * contract_size
        if loss_per_lot <= 0:
            return min_lot

        raw_lots = risk_amount / loss_per_lot

        # Round to broker's lot step
        lots = round(raw_lots / lot_step) * lot_step
        lots = max(min_lot, min(lots, max_lot))
        return round(lots, 2)

    def validate_trade_decision(
        self,
        decision: Dict[str, Any],
        account_info: Dict[str, Any],
        current_spread_points: float,
        open_positions_count: int,
        day_of_month: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Runs rigorous pre-flight validation checks before submitting any order to MT5.
        Returns: (is_valid, rejection_reason, processed_trade_params)
        """
        action = decision.get("action", "HOLD").upper()

        if action in ["HOLD", "CLOSE_POSITION"]:
            return True, "Valid non-entry action", decision

        if action not in ["BUY", "SELL"]:
            return False, f"Invalid trade action: {action}", decision

        # 1. Max Open Positions Check
        if open_positions_count >= CONFIG.MAX_OPEN_TRADES:
            return False, f"Max open positions reached ({open_positions_count}/{CONFIG.MAX_OPEN_TRADES})", decision

        # 2. Daily Drawdown Check
        equity = account_info.get("equity", 0.0)
        self.update_daily_equity(equity, day_of_month)
        is_breached, dd_pct = self.check_daily_drawdown(equity)
        if is_breached:
            return False, f"Daily drawdown limit breached ({dd_pct}% >= {CONFIG.MAX_DAILY_DRAWDOWN_PCT}%)", decision

        # 3. Spread Check
        if current_spread_points > CONFIG.MAX_SPREAD_POINTS:
            return False, f"Spread too wide: {current_spread_points} pts (Max: {CONFIG.MAX_SPREAD_POINTS} pts)", decision

        # 4. Confidence Score Filter
        confidence = decision.get("confidence_score", 0)
        if confidence < 75:
            return False, f"Confidence score too low: {confidence}% (Minimum 75% required)", decision

        # 5. Stop Loss & Take Profit Presence
        entry = decision.get("entry_price", 0.0)
        sl = decision.get("stop_loss", 0.0)
        tp1 = decision.get("take_profit_1", 0.0)
        tp2 = decision.get("take_profit_2", 0.0)

        if not sl or not tp1 or entry <= 0:
            return False, "Missing mandatory Entry, Stop Loss, or Take Profit 1", decision

        # 6. Logical Direction Check
        if action == "BUY":
            if sl >= entry:
                return False, f"Invalid BUY setup: Stop Loss ({sl}) must be below Entry ({entry})", decision
            if tp1 <= entry:
                return False, f"Invalid BUY setup: Take Profit ({tp1}) must be above Entry ({entry})", decision
        elif action == "SELL":
            if sl <= entry:
                return False, f"Invalid SELL setup: Stop Loss ({sl}) must be above Entry ({entry})", decision
            if tp1 >= entry:
                return False, f"Invalid SELL setup: Take Profit ({tp1}) must be below Entry ({entry})", decision

        # 7. Minimum Risk-to-Reward Ratio Check
        risk_distance = abs(entry - sl)
        reward_distance = abs(tp1 - entry)
        if risk_distance > 0:
            rr_ratio = reward_distance / risk_distance
            if rr_ratio < (CONFIG.MIN_RISK_REWARD_RATIO - 0.05):
                return False, f"Risk:Reward ratio too low ({round(rr_ratio, 2)}:1 < {CONFIG.MIN_RISK_REWARD_RATIO}:1)", decision

        # 8. Calculate Position Size
        risk_pct = decision.get("risk_percent", CONFIG.MAX_RISK_PER_TRADE_PCT)
        lots = self.calculate_lot_size(equity, entry, sl, risk_pct)

        validated_params = dict(decision)
        validated_params["calculated_lots"] = lots
        validated_params["entry_price"] = entry
        validated_params["stop_loss"] = sl
        validated_params["take_profit_1"] = tp1
        validated_params["take_profit_2"] = tp2

        return True, "Trade approved by Risk Manager", validated_params
