"""
Execution Engine for Claude XAUUSD AI Trader.
Sends buy/sell orders with SL/TP to MetaTrader 5, manages trailing stops,
partial closes at TP1, and breakeven adjustments.
"""

from typing import Dict, Any, Optional, Tuple
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config import CONFIG


class MT5ExecutionEngine:
    def __init__(self, symbol: str = CONFIG.SYMBOL, magic_number: int = CONFIG.MAGIC_NUMBER):
        self.symbol = symbol
        self.magic_number = magic_number

    def send_market_order(
        self,
        action: str,
        volume: float,
        sl: float,
        tp: float,
        comment: str = "Claude_AI_Gold"
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

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": round(float(sl), digits),
            "tp": round(float(tp), digits),
            "deviation": 25,  # Max slippage in points
            "magic": self.magic_number,
            "comment": comment[:31],  # Max 31 chars
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Check filling mode support (FOK vs IOC)
        if info:
            if info.filling_mode == mt5.ORDER_FILLING_FOK:
                request["type_filling"] = mt5.ORDER_FILLING_FOK
            elif info.filling_mode == mt5.ORDER_FILLING_RETURN:
                request["type_filling"] = mt5.ORDER_FILLING_RETURN

        result = mt5.order_send(request)
        if result is None:
            return False, f"Order send returned None: {mt5.last_error()}", None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"Order failed [Code {result.retcode}]: {result.comment}", None

        return True, f"Successfully executed {action} {volume} lots @ {price} | Ticket: {result.order}", result.order

    def close_position(self, ticket: int, comment: str = "Claude_Close") -> Tuple[bool, str]:
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

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": price,
            "deviation": 25,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"Position {ticket} closed successfully."
        else:
            err = result.comment if result else str(mt5.last_error())
            return False, f"Failed to close position {ticket}: {err}"

    def move_to_breakeven(self, ticket: int, buffer_points: float = 5.0) -> Tuple[bool, str]:
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

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": new_sl,
            "tp": pos.tp,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"Moved ticket {ticket} SL to Breakeven @ {new_sl}"
        else:
            err = result.comment if result else str(mt5.last_error())
            return False, f"Failed to update SL for {ticket}: {err}"
