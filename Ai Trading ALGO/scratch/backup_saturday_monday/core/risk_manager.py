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
        if current_equity <= 0:
            return
        if self.last_reset_day != current_day or self.daily_start_equity is None or self.daily_start_equity <= 0:
            self.daily_start_equity = current_equity
            self.last_reset_day = current_day

    def check_daily_drawdown(self, current_equity: float) -> Tuple[bool, float]:
        """
        Checks if current account equity has breached the daily drawdown limit.
        Returns: (is_breached, current_drawdown_pct)
        """
        if not self.daily_start_equity or self.daily_start_equity <= 0 or current_equity <= 0:
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
        risk_pct: float = CONFIG.MAX_RISK_PER_TRADE_PCT,
        confidence_score: float = 80.0,
        symbol: Optional[str] = None,
        max_lot_cap: Optional[float] = None
    ) -> float:
        """
        Dynamically calculates the exact lot size based on equity, distance to Stop Loss,
        asset contract size (BTC: 1.0 vs Gold: 100.0), and scales proportionally with conviction.

        Enforces:
        - Exact contract size per asset (BTC: 1 lot = 1 BTC, Gold: 1 lot = 100 oz).
        - Clamps smoothly up to the account / symbol's configured max lot cap (e.g. 0.50 lots on BTC).
        """
        if entry_price <= 0 or stop_loss <= 0 or account_equity <= 0:
            return CONFIG.MIN_LOT_SIZE

        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            return CONFIG.MIN_LOT_SIZE

        target_sym = symbol or self.symbol
        is_btc = "BTC" in str(target_sym).upper() or "BITCOIN" in str(target_sym).upper()

        # Default standard contract specs
        contract_size = 1.0 if is_btc else 100.0
        min_lot = CONFIG.MIN_LOT_SIZE
        if max_lot_cap is not None:
            effective_max_cap = float(max_lot_cap)
        else:
            effective_max_cap = CONFIG.BTC_MAX_LOT_SIZE if is_btc else CONFIG.MAX_LOT_SIZE
        lot_step = 0.01

        if mt5:
            info = mt5.symbol_info(target_sym)
            if info:
                contract_size = info.trade_contract_size or (1.0 if is_btc else 100.0)
                min_lot = max(CONFIG.MIN_LOT_SIZE, info.volume_min or 0.01)
                lot_step = info.volume_step or 0.01

        # 1. Base Dollar risk amount based on equity and risk % (Strictly capped at <= 5.0% of equity)
        max_allowed_risk_pct = float(getattr(CONFIG, "MAX_PORTFOLIO_AGGREGATE_RISK_PCT", 5.0))
        safe_risk_pct = min(float(risk_pct), max_allowed_risk_pct)
        risk_amount = account_equity * (safe_risk_pct / 100.0)

        # 2. Loss per 1.0 standard lot = sl_distance * contract_size
        loss_per_lot = sl_distance * contract_size
        if loss_per_lot <= 0:
            return min_lot

        raw_math_lots = risk_amount / loss_per_lot

        # 3. Exact Consensus Quorum Meter Tiered Lot Scaling:
        # Dynamically adapts to SCALP (50%+) and STANDARD_PROP (60%+) modes:
        # - Super Quorum (>= 93% score): 100% of maximum allocated lots (Full Conviction)
        # - High Quorum (85% - 92% score): 70% of allocated lots (Standard Conviction)
        # - Moderate Quorum (70% - 84% score): 55% of allocated lots (Strong SCALP)
        # - Standard Quorum (60% - 69% score): 40% of allocated lots (Min STANDARD_PROP)
        # - SCALP Quorum (50% - 59% score): 30% of allocated lots (Min SCALP)
        # - Low Quorum (< 50% score): 20% micro lot (Exploratory)
        quorum = float(confidence_score)
        if quorum >= 93.0:
            quorum_tier_pct = 1.00  # 100% Full Lot
        elif quorum >= 85.0:
            quorum_tier_pct = 0.70  # 70% Lot
        elif quorum >= 70.0:
            quorum_tier_pct = 0.55  # 55% Lot (Strong SCALP)
        elif quorum >= 60.0:
            quorum_tier_pct = 0.40  # 40% Lot (Min STANDARD_PROP)
        elif quorum >= 50.0:
            quorum_tier_pct = 0.30  # 30% Lot (Min SCALP)
        else:
            quorum_tier_pct = 0.20  # Micro Lot

        scaled_lots = raw_math_lots * quorum_tier_pct
        if effective_max_cap > 0:
            scaled_lots = min(scaled_lots, effective_max_cap * quorum_tier_pct)

        # 4. Round to broker's lot step
        lots = round(scaled_lots / lot_step) * lot_step

        # 5. Clamp strictly between min_lot and configured max lot cap
        final_lots = max(min_lot, min(lots, effective_max_cap))
        return round(final_lots, 2)

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


        equity = account_info.get("equity", 0.0)
        if equity <= 0:
            return False, "Invalid account equity (<= 0)", decision

        # 1. Daily Drawdown Guardrail
        self.update_daily_equity(equity, day_of_month)
        is_dd_breached, dd_pct = self.check_daily_drawdown(equity)
        if is_dd_breached:
            return False, f"Daily drawdown limit hit ({dd_pct}% >= {CONFIG.MAX_DAILY_DRAWDOWN_PCT}%). Trading paused today.", decision

        # 2. Max Open Trades Filter
        if open_positions_count >= CONFIG.MAX_OPEN_TRADES:
            return False, f"Max concurrent trades reached ({open_positions_count}/{CONFIG.MAX_OPEN_TRADES})", decision

        # 3. Spread Filter
        sym = decision.get("symbol", CONFIG.SYMBOL)
        is_btc = "BTC" in str(sym).upper()
        max_allowed_spread = CONFIG.BTC_MAX_SPREAD_POINTS if is_btc else CONFIG.MAX_SPREAD_POINTS
        if current_spread_points > max_allowed_spread:
            return False, f"Spread too wide: {current_spread_points} pts (Max: {max_allowed_spread} pts)", decision

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

        # 8. Calculate Position Size scaled by probability & strictly capped at 5% portfolio risk
        max_allowed_risk_pct = float(getattr(CONFIG, "MAX_PORTFOLIO_AGGREGATE_RISK_PCT", 5.0))
        risk_pct = min(float(decision.get("risk_percent", CONFIG.MAX_RISK_PER_TRADE_PCT)), max_allowed_risk_pct)
        lots = self.calculate_lot_size(equity, entry, sl, risk_pct, confidence_score=confidence)

        # Enforce maximum 5.0% dollar risk cap
        contract_size = 1.0 if ("BTC" in str(self.symbol).upper() or "BITCOIN" in str(self.symbol).upper()) else 100.0
        dollar_risk = risk_distance * contract_size * lots
        if equity > 0 and (dollar_risk / equity * 100.0) > (max_allowed_risk_pct + 0.05):
            max_risk_dollars = equity * (max_allowed_risk_pct / 100.0)
            if risk_distance * contract_size > 0:
                lots = max(CONFIG.MIN_LOT_SIZE, round(max_risk_dollars / (risk_distance * contract_size), 2))

        validated_params = dict(decision)
        validated_params["calculated_lots"] = lots
        validated_params["entry_price"] = entry
        validated_params["stop_loss"] = sl
        validated_params["take_profit_1"] = tp1
        validated_params["take_profit_2"] = tp2

        return True, "Trade approved by Risk Manager", validated_params
