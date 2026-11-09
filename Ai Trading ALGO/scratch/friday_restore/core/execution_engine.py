"""
Execution Engine for Claude XAUUSD AI Trader.
Sends buy/sell orders with SL/TP to MetaTrader 5, manages 3-tier institutional trailing stops,
partial closes at TP1, and breakeven adjustments.
"""

from typing import Dict, Any, Optional, Tuple, List
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config import CONFIG


class MT5ExecutionEngine:
    def __init__(self, symbol: str = CONFIG.SYMBOL, magic_number: int = CONFIG.MAGIC_NUMBER):
        self.symbol = symbol
        self.magic_number = magic_number

    def _get_filling_mode(self, info) -> int:
        """Dynamically detects broker-supported execution filling mode via bitmask."""
        if not info or mt5 is None:
            return 1  # ORDER_FILLING_IOC
        fm = getattr(info, "filling_mode", 1)
        if fm & 2:  # SYMBOL_FILLING_IOC
            return mt5.ORDER_FILLING_IOC
        elif fm & 1:  # SYMBOL_FILLING_FOK
            return mt5.ORDER_FILLING_FOK
        elif fm & 4:  # SYMBOL_FILLING_RETURN
            return mt5.ORDER_FILLING_RETURN
        return mt5.ORDER_FILLING_FOK

    def send_market_order(
        self,
        action: str,
        volume: float,
        sl: float,
        tp: float,
        comment: str = "Chanakya_Trade",
        consensus_score: int = 85
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Executes a market BUY or SELL order on MT5 with hard Stop Loss and Take Profit.
        Returns: (success, message, ticket_id)
        """
        if mt5 is None:
            return False, "MetaTrader5 module not initialized", None

        # Fetch live tick
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return False, f"Failed to get live tick for {self.symbol}", None

        info = mt5.symbol_info(self.symbol)
        digits = info.digits if info else 2

        if action.upper() == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = round(tick.ask, digits)
        elif action.upper() == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
            price = round(tick.bid, digits)
        else:
            return False, f"Unsupported order action: {action}", None

        # Validate volume bounds
        if info:
            volume = max(info.volume_min, min(float(volume), CONFIG.MAX_LOT_SIZE))
            if hasattr(info, "volume_step") and info.volume_step > 0:
                steps = round(volume / info.volume_step)
                volume = round(steps * info.volume_step, 2)

        # Format trade comment to Chanakya signature
        if not comment or comment in ["AI_Council_Trade", "AI_Trade", "Chanakya_Trade"]:
            trade_comment = "Chanakya_Buy" if action.upper() == "BUY" else "Chanakya_Sell"
        else:
            trade_comment = comment

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": round(float(sl), digits) if sl else 0.0,
            "tp": round(float(tp), digits) if tp else 0.0,
            "deviation": 25,  # Max slippage in points
            "magic": self.magic_number,
            "comment": trade_comment[:31],  # Max 31 chars
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        result = mt5.order_send(request)
        if result is None:
            return False, f"Order send returned None: {mt5.last_error()}", None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"Order failed [Code {result.retcode}]: {result.comment}", None

        # Record in AI Trade Ledger
        try:
            from core.ai_ledger import AITradeLedger
            AITradeLedger.record_executed_trade(
                ticket=result.order,
                symbol=self.symbol,
                action=action,
                volume=volume,
                price=price,
                sl=sl,
                tp=tp,
                consensus_score=consensus_score,
                comment=trade_comment
            )
        except Exception as e:
            print(f"[ExecutionEngine] Ledger recording warning: {e}")

        return True, f"Successfully executed {action} {volume} lots @ {price} | Ticket: {result.order}", result.order

    def close_position(self, ticket: int, comment: str = "Chanakya_Close") -> Tuple[bool, str]:
        """Closes an open position by ticket ID."""
        if mt5 is None:
            return False, "MetaTrader5 module not initialized"

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, f"Position with ticket {ticket} not found."

        pos = position[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return False, "Failed to get current price tick."

        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        info = mt5.symbol_info(pos.symbol)
        filling_mode = self._get_filling_mode(info)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": price,
            "deviation": 25,
            "magic": self.magic_number,
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"Position {ticket} closed successfully."
        else:
            err = result.comment if result else str(mt5.last_error())
            return False, f"Failed to close position {ticket}: {err}"

    def close_partial_position(self, ticket: int, volume_to_close: float, comment: str = "Chanakya_Partial_TP") -> Tuple[bool, str]:
        """
        Closes a partial lot volume of an open position to lock in cash profits,
        leaving the remaining volume running with a trailing stop.
        """
        if mt5 is None:
            return False, "MetaTrader5 module not initialized"

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, f"Position with ticket {ticket} not found."

        pos = position[0]
        info = mt5.symbol_info(pos.symbol)
        min_volume = info.volume_min if info else 0.01

        volume_to_close = round(float(volume_to_close), 2)
        if volume_to_close >= pos.volume:
            return self.close_position(ticket, comment=comment)

        if volume_to_close < min_volume:
            return False, f"Volume {volume_to_close} is below broker minimum {min_volume}"

        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return False, "Failed to get current price tick."

        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": volume_to_close,
            "type": close_type,
            "price": price,
            "deviation": 25,
            "magic": self.magic_number,
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if info:
            if info.filling_mode == mt5.ORDER_FILLING_FOK:
                request["type_filling"] = mt5.ORDER_FILLING_FOK
            elif info.filling_mode == mt5.ORDER_FILLING_RETURN:
                request["type_filling"] = mt5.ORDER_FILLING_RETURN

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            rem_vol = round(pos.volume - volume_to_close, 2)
            return True, f"Booked partial profit: Closed {volume_to_close} lots on Ticket #{ticket}. Remaining: {rem_vol} lots."
        else:
            err = result.comment if result else str(mt5.last_error())
            return False, f"Failed to partially close ticket {ticket}: {err}"

    def update_sl_tp(self, ticket: int, new_sl: float, new_tp: float) -> Tuple[bool, str]:
        """Updates both Stop Loss and Take Profit of an active position in MetaTrader 5."""
        if mt5 is None:
            return False, "MetaTrader5 module not initialized"

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, f"Position {ticket} not found"

        pos = position[0]
        info = mt5.symbol_info(pos.symbol)
        digits = info.digits if info else 2
        sl = round(float(new_sl), digits) if new_sl else pos.sl
        tp = round(float(new_tp), digits) if new_tp else pos.tp

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": sl,
            "tp": tp,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"Successfully adjusted SL={sl}, TP={tp} for ticket #{ticket}"
        else:
            err = result.comment if result else str(mt5.last_error())
            return False, f"Failed to update SL/TP for ticket #{ticket}: {err}"

    def update_stop_loss(self, ticket: int, new_sl: float) -> Tuple[bool, str]:
        """Updates the Stop Loss of an active position in MetaTrader 5."""
        if mt5 is None:
            return False, "MetaTrader5 module not initialized"

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, f"Position {ticket} not found"

        pos = position[0]
        info = mt5.symbol_info(pos.symbol)
        digits = info.digits if info else 2
        new_sl = round(float(new_sl), digits)

        if round(pos.sl, digits) == new_sl:
            return True, "SL already at target price"

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": new_sl,
            "tp": pos.tp,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"Successfully adjusted SL for ticket #{ticket} to {new_sl}"
        else:
            err = result.comment if result else str(mt5.last_error())
            return False, f"Failed to update SL for ticket #{ticket}: {err}"

    def move_to_breakeven(self, ticket: int, buffer_points: float = 6.0) -> Tuple[bool, str]:
        """Moves Stop Loss to entry price (+ small buffer) for risk-free trade."""
        if mt5 is None:
            return False, "MetaTrader5 module not initialized"

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, f"Position {ticket} not found"

        pos = position[0]
        info = mt5.symbol_info(pos.symbol)
        point = info.point if info else 0.01

        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = round(pos.price_open + (buffer_points * point), info.digits)
            if pos.sl >= new_sl:
                return True, "SL already at or better than breakeven"
        else:
            new_sl = round(pos.price_open - (buffer_points * point), info.digits)
            if pos.sl > 0 and pos.sl <= new_sl:
                return True, "SL already at or better than breakeven"

        return self.update_stop_loss(ticket, new_sl)

    def manage_position_risk_and_trailing(
        self,
        position: Dict[str, Any],
        current_price: float,
        atr: float = 6.0,
        recent_candle_low: Optional[float] = None,
        recent_candle_high: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Applies 3-Tier Professional Institutional Trailing Stop Loss Management:
        - Tier 1: Risk-Free Breakeven (+ buffer) when price reaches +1.0R (or 50% TP distance)
        - Tier 2: Lock Profit (+0.8R) when price reaches +1.5R gain
        - Tier 3: Dynamic Trailing (behind recent M15 swing pivots or 1.5x ATR) beyond TP1
        """
        ticket = position.get("ticket")
        pos_type = position.get("type", "BUY").upper()
        entry = float(position.get("open_price", 0.0))
        current_sl = float(position.get("sl", 0.0))
        tp = float(position.get("tp", 0.0) or 0.0)

        if not ticket or entry <= 0:
            return False, "Invalid position parameters"

        info = mt5.symbol_info(self.symbol) if mt5 else None
        point = info.point if info else 0.01
        digits = info.digits if info else 2
        buffer_pts = CONFIG.TRAILING_BUFFER_POINTS * point

        # Calculate Initial Risk (R)
        if current_sl > 0:
            initial_risk = abs(entry - current_sl)
        else:
            initial_risk = max(atr, 5.0)

        if initial_risk <= 0:
            initial_risk = 5.0

        target_new_sl = None
        reason = ""

        if pos_type == "BUY":
            profit_dist = current_price - entry
            r_multiple = profit_dist / initial_risk

            # Tier 3: Dynamic ATR / Swing Trail (if profit >= 1.5R or near TP1)
            if (tp > 0 and current_price >= tp * 0.98) or r_multiple >= 1.5:
                candidate_sl = round(current_price - (CONFIG.TRAILING_ATR_MULTIPLIER * atr), digits)
                if recent_candle_low and recent_candle_low > candidate_sl and recent_candle_low < current_price:
                    candidate_sl = round(recent_candle_low - (2 * point), digits)
                
                if candidate_sl > current_sl and candidate_sl > (entry + buffer_pts):
                    target_new_sl = candidate_sl
                    reason = f"Tier 3 Trailing Stop at +{r_multiple:.2f}R"

            # Tier 2: Lock Profit (+0.4R) at +0.8R gain
            elif r_multiple >= CONFIG.TRAILING_LOCK_TRIGGER_R:
                lock_sl = round(entry + (0.4 * initial_risk), digits)
                if lock_sl > current_sl:
                    target_new_sl = lock_sl
                    reason = f"Tier 2 Lock Green Profit (+0.4R) at +{r_multiple:.2f}R"

            # Tier 1: Move to Breakeven (+ buffer) early at +0.5R gain
            elif r_multiple >= CONFIG.TRAILING_BE_TRIGGER_R or (tp > 0 and profit_dist >= (tp - entry) * 0.35):
                be_sl = round(entry + buffer_pts, digits)
                if be_sl > current_sl:
                    target_new_sl = be_sl
                    reason = f"Tier 1 Breakeven Risk-Free at +{r_multiple:.2f}R"

        elif pos_type == "SELL":
            profit_dist = entry - current_price
            r_multiple = profit_dist / initial_risk

            # Tier 3: Dynamic ATR / Swing Trail
            if (tp > 0 and current_price <= tp * 1.02) or r_multiple >= 1.5:
                candidate_sl = round(current_price + (CONFIG.TRAILING_ATR_MULTIPLIER * atr), digits)
                if recent_candle_high and recent_candle_high < candidate_sl and recent_candle_high > current_price:
                    candidate_sl = round(recent_candle_high + (2 * point), digits)

                if current_sl == 0 or candidate_sl < current_sl:
                    if candidate_sl < (entry - buffer_pts):
                        target_new_sl = candidate_sl
                        reason = f"Tier 3 Trailing Stop at +{r_multiple:.2f}R"

            # Tier 2: Lock Profit (+0.4R) at +0.8R gain
            elif r_multiple >= CONFIG.TRAILING_LOCK_TRIGGER_R:
                lock_sl = round(entry - (0.4 * initial_risk), digits)
                if current_sl == 0 or lock_sl < current_sl:
                    target_new_sl = lock_sl
                    reason = f"Tier 2 Lock Green Profit (+0.4R) at +{r_multiple:.2f}R"

            # Tier 1: Move to Breakeven (+ buffer) early at +0.5R gain
            elif r_multiple >= CONFIG.TRAILING_BE_TRIGGER_R or (tp > 0 and profit_dist >= (entry - tp) * 0.35):
                be_sl = round(entry - buffer_pts, digits)
                if current_sl == 0 or be_sl < current_sl:
                    target_new_sl = be_sl
                    reason = f"Tier 1 Breakeven Risk-Free at +{r_multiple:.2f}R"

        if target_new_sl is not None and target_new_sl != current_sl:
            success, msg = self.update_stop_loss(ticket, target_new_sl)
            if success:
                return True, f"[{reason}] Ticket #{ticket} SL moved to {target_new_sl}"
            else:
                return False, f"[{reason}] Failed: {msg}"

        return False, "No SL adjustment needed"
