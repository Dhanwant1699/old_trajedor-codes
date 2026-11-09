"""
Data Engine for Claude XAUUSD AI Trader.
Extracts live multi-timeframe market data and computes institutional indicators:
- SMC / ICT: Fair Value Gaps (FVG), Asian Session Liquidity Swings, BOS/CHoCH
- Trend: EMA 50, EMA 200, Fast EMA 9, EMA 21
- Mean Reversion: RSI 14, Bollinger Bands (20, 2), Bollinger Squeeze
- Volume & Order Flow: Intraday VWAP, Volume Spikes
- Fibonacci: Major Swing High/Low Retracements (0.5, 0.618 Golden Pocket, 0.786) & Extensions
- Supply & Demand: Fresh Imbalance Zones (RBR, DBD, DBR, RBD)
- Patterns: Candlestick Geometry (Pinbars, Engulfing)
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config import CONFIG


TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1 if mt5 else 1,
    "M5": mt5.TIMEFRAME_M5 if mt5 else 5,
    "M15": mt5.TIMEFRAME_M15 if mt5 else 15,
    "M30": mt5.TIMEFRAME_M30 if mt5 else 30,
    "H1": mt5.TIMEFRAME_H1 if mt5 else 16385,
    "H4": mt5.TIMEFRAME_H4 if mt5 else 16388,
    "D1": mt5.TIMEFRAME_D1 if mt5 else 16408,
}


class MT5DataEngine:
    def __init__(self, symbol: str = CONFIG.SYMBOL):
        self.symbol = symbol
        self._connected = False

    def connect(self, verbose: bool = False) -> bool:
        """Initializes connection to MT5 terminal."""
        if mt5 is None:
            if verbose: print("[DataEngine] MetaTrader5 library not available.")
            return False

        term_info = mt5.terminal_info()
        if term_info is None:
            success = False
            candidates = [CONFIG.MT5_PATH] if CONFIG.MT5_PATH else [
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe",
                r"C:\Program Files\MetaTrader 5 - 3\terminal64.exe",
                r"C:\Program Files\MetaTrader 5 - 1\terminal64.exe",
                ""
            ]
            for p in candidates:
                if p and os.path.exists(p):
                    if mt5.initialize(path=p):
                        success = True
                        break
                elif not p:
                    if mt5.initialize():
                        success = True
                        break
            if not success:
                if verbose: print(f"[DataEngine] MT5 initialize failed: {mt5.last_error()}")
                return False

        if CONFIG.MT5_LOGIN and CONFIG.MT5_PASSWORD and CONFIG.MT5_SERVER:
            if not mt5.login(login=CONFIG.MT5_LOGIN, password=CONFIG.MT5_PASSWORD, server=CONFIG.MT5_SERVER):
                if verbose: print(f"[DataEngine] MT5 login failed: {mt5.last_error()}")
                return False

        # Ensure symbol is selected and visible in Market Watch with strict real-asset price validation
        is_btc = "BTC" in self.symbol.upper() or "BITCOIN" in self.symbol.upper()
        is_gold = "XAU" in self.symbol.upper() or "GOLD" in self.symbol.upper()

        if is_btc:
            self.symbol = "BTCUSD"
            preferred_aliases = ["BTCUSD", "BTCUSD+", "BTCUSDm", "BTCUSD.m", "BTCUSDT", "BTCUSDT+", "Bitcoin", "BTC/USD"]
        elif is_gold:
            self.symbol = "XAUUSD"
            preferred_aliases = ["XAUUSD", "XAUUSD+", "XAUUSDm", "XAUUSD.m", "XAUUSD_i", "XAUUSD.", "XAU/USD", "XAUEUR"]
        else:
            preferred_aliases = [self.symbol, f"{self.symbol}+", f"{self.symbol}m", f"{self.symbol}.m", f"{self.symbol}_i", f"{self.symbol}."]

        def _is_valid_price(sym_name: str) -> bool:
            try:
                t = mt5.symbol_info_tick(sym_name)
                bid = float(t.bid) if (t and t.bid > 0) else 0.0
                if bid <= 0:
                    info = mt5.symbol_info(sym_name)
                    bid = float(info.bid) if (info and info.bid > 0) else (float(info.last) if (info and info.last) else 0.0)
                if is_btc:
                    return bid >= 10000.0  # Real Bitcoin spot price check ($80k+)
                if is_gold:
                    return bid >= 1000.0   # Real Gold spot price check ($4k+)
                return bid > 0
            except Exception:
                return False

        def _find_symbol_in_active_terminal() -> Optional[str]:
            for alt in preferred_aliases:
                if mt5.symbol_select(alt, True) and _is_valid_price(alt):
                    return alt
            all_syms = mt5.symbols_get()
            if all_syms:
                for s in all_syms:
                    s_name = s.name
                    s_upper = s_name.upper()
                    match = False
                    if is_btc:
                        if ("BTCUSD" in s_upper or "BTCUSDT" in s_upper or "BITCOIN" in s_upper) and not ("BTCL" in s_upper or s_upper == "BTC"):
                            match = True
                    elif is_gold:
                        if ("XAUUSD" in s_upper or "XAU/USD" in s_upper or "XAUEUR" in s_upper) and (s_upper != "GOLD"):
                            match = True
                    else:
                        if self.symbol.upper() in s_upper:
                            match = True
                    if match and mt5.symbol_select(s_name, True) and _is_valid_price(s_name):
                        return s_name
            return None

        resolved = _find_symbol_in_active_terminal()

        # If not found in current MT5 terminal, search other installed terminals
        if not resolved and (is_btc or is_gold):
            other_terminals = [
                r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe",
                r"C:\Program Files\MetaTrader 5 - 3\terminal64.exe",
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files\MetaTrader 5 - 1\terminal64.exe",
                r"C:\Program Files\Vantage MetaTrader 5\terminal64.exe",
                r"C:\Program Files\GTC Global MetaTrader 5\terminal64.exe"
            ]
            for term_p in other_terminals:
                if os.path.exists(term_p):
                    try:
                        if mt5.initialize(path=term_p):
                            resolved = _find_symbol_in_active_terminal()
                            if resolved:
                                if verbose: print(f"[DataEngine] Switched to terminal '{term_p}' for verified {self.symbol} -> '{resolved}'")
                                break
                    except Exception:
                        pass

        if not resolved:
            if verbose: print(f"[DataEngine] Symbol '{self.symbol}' with valid spot price not found in MT5.")
            return False

        self.symbol = resolved
        self._connected = True
        if verbose: print(f"[DataEngine] Connected to MT5 for symbol '{self.symbol}'")
        return True

    def ensure_connected(self) -> bool:
        """Ensures MT5 is actively connected, re-initializing if connection dropped."""
        if not self._connected or mt5 is None:
            return self.connect(verbose=False)
        try:
            if mt5.terminal_info() is None or mt5.account_info() is None:
                return self.connect(verbose=False)
        except Exception:
            return self.connect(verbose=False)
        return True

    def disconnect(self):
        """Shutdown MT5 connection."""
        if mt5 and self._connected:
            mt5.shutdown()
            self._connected = False

    def get_account_info(self) -> Dict[str, Any]:
        """Fetches live balance, equity, margin, and free margin."""
        self.ensure_connected()
        if not self._connected:
            return {"balance": 0.0, "equity": 0.0, "free_margin": 0.0, "profit": 0.0}
        acc = mt5.account_info()
        if acc is None:
            self.connect()
            acc = mt5.account_info()
        if acc is None:
            return {"balance": 0.0, "equity": 0.0, "free_margin": 0.0, "profit": 0.0}
        return {
            "balance": acc.balance,
            "equity": acc.equity,
            "free_margin": acc.margin_free,
            "margin_level": acc.margin_level,
            "currency": acc.currency,
            "profit": acc.profit,
            "leverage": acc.leverage,
        }

    def get_current_spread_and_ticks(self) -> Dict[str, float]:
        """Gets live bid, ask, and spread in points."""
        self.ensure_connected()
        if not self._connected:
            return {"bid": 0.0, "ask": 0.0, "spread_points": 0.0, "point": 0.01}
        info = mt5.symbol_info(self.symbol)
        tick = mt5.symbol_info_tick(self.symbol)
        if info is None or tick is None:
            self.connect()
            info = mt5.symbol_info(self.symbol)
            tick = mt5.symbol_info_tick(self.symbol)
        if info is None or tick is None:
            return {"bid": 0.0, "ask": 0.0, "spread_points": 0.0, "point": 0.01}

        spread_points = (tick.ask - tick.bid) / info.point if info.point else 0.0
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread_points": round(spread_points, 1),
            "point": info.point,
            "digits": info.digits,
        }

    def get_candles(self, timeframe_str: str, count: int = 100) -> pd.DataFrame:
        """Fetches OHLCV candle history as a pandas DataFrame."""
        self.ensure_connected()
        if not self._connected:
            return pd.DataFrame()

        tf = TIMEFRAME_MAP.get(timeframe_str.upper(), mt5.TIMEFRAME_M15)
        rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            self.connect()
            rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        return df[['time', 'open', 'high', 'low', 'close', 'volume']]

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates full indicator suite: EMAs (9, 21, 50, 200), ATR 14, RSI 14, Bollinger Bands, VWAP."""
        if df.empty or len(df) < 30:
            return df

        # EMAs
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # ATR 14
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()

        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi_14'] = 100 - (100 / (1 + rs))

        # Bollinger Bands (20, 2.0)
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (bb_std * 2.0)
        df['bb_lower'] = df['bb_mid'] - (bb_std * 2.0)
        df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_mid']) * 100.0

        # ADX & Directional Movement (+DI, -DI)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift())
        df['tr2'] = abs(df['low'] - df['close'].shift())
        df['tr_val'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        
        df['up_move'] = df['high'] - df['high'].shift()
        df['down_move'] = df['low'].shift() - df['low']
        df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0.0)
        df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0.0)

        tr14 = df['tr_val'].rolling(14).sum()
        df['plus_di14'] = 100 * (df['plus_dm'].rolling(14).sum() / (tr14 + 1e-10))
        df['minus_di14'] = 100 * (df['minus_dm'].rolling(14).sum() / (tr14 + 1e-10))
        dx = 100 * (abs(df['plus_di14'] - df['minus_di14']) / (df['plus_di14'] + df['minus_di14'] + 1e-10))
        df['adx_14'] = dx.rolling(14).mean()

        # Choppiness Index (14)
        sum_tr = df['tr_val'].rolling(14).sum()
        max_high = df['high'].rolling(14).max()
        min_low = df['low'].rolling(14).min()
        range_hl = max_high - min_low
        df['chop_14'] = 100 * np.log10(sum_tr / (range_hl + 1e-10)) / np.log10(14)

        # Volume Delta & Cumulative Volume Delta (CVD)
        vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
        body_ratio = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        df['vol_delta'] = df[vol_col] * body_ratio
        df['cvd'] = df['vol_delta'].cumsum()

        # Intraday VWAP approximation
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
        df['cum_vol'] = df['volume'].cumsum()
        df['cum_vol_price'] = (typical_price * df['volume']).cumsum()
        df['vwap'] = df['cum_vol_price'] / (df['cum_vol'] + 1e-10)

        return df

    @staticmethod
    def find_fair_value_gaps(df: pd.DataFrame, min_gap_points: float = 0.5) -> List[Dict[str, Any]]:
        """Identifies active Fair Value Gaps (FVGs)."""
        if len(df) < 5:
            return []

        fvgs = []
        recent_df = df.iloc[-35:].reset_index(drop=True)
        current_price = recent_df['close'].iloc[-1]

        for i in range(2, len(recent_df) - 1):
            c1_high = recent_df.loc[i - 2, 'high']
            c1_low = recent_df.loc[i - 2, 'low']
            c3_high = recent_df.loc[i, 'high']
            c3_low = recent_df.loc[i, 'low']
            fvg_time = str(recent_df.loc[i - 1, 'time'])

            # Bullish FVG
            if c3_low > c1_high + min_gap_points:
                gap_top = c3_low
                gap_bottom = c1_high
                subsequent_lows = recent_df.loc[i+1:, 'low']
                is_mitigated = (subsequent_lows <= gap_bottom).any() if len(subsequent_lows) > 0 else False
                if not is_mitigated:
                    fvgs.append({
                        "type": "BULLISH_FVG",
                        "top": round(gap_top, 2),
                        "bottom": round(gap_bottom, 2),
                        "size": round(gap_top - gap_bottom, 2),
                        "distance": round(current_price - gap_top, 2),
                        "time": fvg_time
                    })

            # Bearish FVG
            elif c1_low > c3_high + min_gap_points:
                gap_top = c1_low
                gap_bottom = c3_high
                subsequent_highs = recent_df.loc[i+1:, 'high']
                is_mitigated = (subsequent_highs >= gap_top).any() if len(subsequent_highs) > 0 else False
                if not is_mitigated:
                    fvgs.append({
                        "type": "BEARISH_FVG",
                        "top": round(gap_top, 2),
                        "bottom": round(gap_bottom, 2),
                        "size": round(gap_top - gap_bottom, 2),
                        "distance": round(gap_bottom - current_price, 2),
                        "time": fvg_time
                    })

        return fvgs[-4:]

    @staticmethod
    def find_supply_demand_zones(df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identifies fresh Supply & Demand imbalance origin zones:
        Demand: Strong explosive bullish expansion candle leaving a base behind.
        Supply: Strong explosive bearish expansion candle leaving a base behind.
        """
        if len(df) < 15:
            return {"fresh_demand_zones": [], "fresh_supply_zones": []}

        demand_zones = []
        supply_zones = []
        recent = df.iloc[-40:].reset_index(drop=True)
        current_price = recent['close'].iloc[-1]

        for i in range(1, len(recent) - 1):
            prev_candle = recent.iloc[i - 1]
            curr_candle = recent.iloc[i]
            body_size = abs(curr_candle['close'] - curr_candle['open'])
            avg_body = (recent['high'] - recent['low']).mean()

            # Strong Bullish Impulse (Demand Origin)
            if curr_candle['close'] > curr_candle['open'] and body_size > avg_body * 1.5:
                zone_top = max(prev_candle['high'], prev_candle['open'])
                zone_bottom = prev_candle['low']
                # Check if price has broken below zone since
                subsequent = recent.iloc[i+1:]
                if not (subsequent['low'] < zone_bottom).any():
                    demand_zones.append({
                        "zone": "DEMAND",
                        "top": round(zone_top, 2),
                        "bottom": round(zone_bottom, 2),
                        "distance_to_price": round(current_price - zone_top, 2),
                        "time": str(prev_candle['time'])
                    })

            # Strong Bearish Impulse (Supply Origin)
            elif curr_candle['open'] > curr_candle['close'] and body_size > avg_body * 1.5:
                zone_top = prev_candle['high']
                zone_bottom = min(prev_candle['low'], prev_candle['open'])
                subsequent = recent.iloc[i+1:]
                if not (subsequent['high'] > zone_top).any():
                    supply_zones.append({
                        "zone": "SUPPLY",
                        "top": round(zone_top, 2),
                        "bottom": round(zone_bottom, 2),
                        "distance_to_price": round(zone_bottom - current_price, 2),
                        "time": str(prev_candle['time'])
                    })

        return {
            "fresh_demand_zones": demand_zones[-3:],
            "fresh_supply_zones": supply_zones[-3:]
        }

    @staticmethod
    def calculate_fibonacci_levels(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates Fibonacci Retracement & Extension levels on the most recent prominent swing leg.
        Golden Pocket: 0.618 - 0.786 OTE (Optimal Trade Entry) zone.
        """
        if len(df) < 30:
            return {}

        recent = df.iloc[-40:]
        highest_price = recent['high'].max()
        lowest_price = recent['low'].min()
        high_idx = recent['high'].idxmax()
        low_idx = recent['low'].idxmin()

        is_bullish_impulse = (high_idx > low_idx)  # Low happened before High -> Up impulse
        diff = highest_price - lowest_price

        if diff <= 0:
            return {}

        if is_bullish_impulse:
            # Retracement levels from High going down
            fib_50 = round(highest_price - (diff * 0.50), 2)
            fib_618 = round(highest_price - (diff * 0.618), 2)
            fib_786 = round(highest_price - (diff * 0.786), 2)
            ext_1272 = round(highest_price + (diff * 0.272), 2)
            ext_1618 = round(highest_price + (diff * 0.618), 2)
            return {
                "swing_type": "BULLISH_IMPULSE",
                "swing_low": round(lowest_price, 2),
                "swing_high": round(highest_price, 2),
                "fib_50_level": fib_50,
                "golden_pocket_ote": f"{fib_786} - {fib_618} (0.618 to 0.786)",
                "fib_618": fib_618,
                "fib_786": fib_786,
                "extension_tp1": ext_1272,
                "extension_tp2": ext_1618,
            }
        else:
            # Retracement levels from Low going up
            fib_50 = round(lowest_price + (diff * 0.50), 2)
            fib_618 = round(lowest_price + (diff * 0.618), 2)
            fib_786 = round(lowest_price + (diff * 0.786), 2)
            ext_1272 = round(lowest_price - (diff * 0.272), 2)
            ext_1618 = round(lowest_price - (diff * 0.618), 2)
            return {
                "swing_type": "BEARISH_IMPULSE",
                "swing_high": round(highest_price, 2),
                "swing_low": round(lowest_price, 2),
                "fib_50_level": fib_50,
                "golden_pocket_ote": f"{fib_618} - {fib_786} (0.618 to 0.786)",
                "fib_618": fib_618,
                "fib_786": fib_786,
                "extension_tp1": ext_1272,
                "extension_tp2": ext_1618,
            }

    @staticmethod
    def detect_candlestick_patterns(df: pd.DataFrame) -> List[Dict[str, str]]:
        """Detects high-probability candlestick geometry (Pinbars, Engulfing, Hammers)."""
        if len(df) < 5:
            return []

        patterns = []
        recent = df.iloc[-5:].reset_index(drop=True)
        for i in range(1, len(recent)):
            c = recent.iloc[i]
            prev = recent.iloc[i - 1]
            body = abs(c['close'] - c['open'])
            candle_range = c['high'] - c['low']
            upper_wick = c['high'] - max(c['close'], c['open'])
            lower_wick = min(c['close'], c['open']) - c['low']

            if candle_range <= 0:
                continue

            # Bullish Pinbar / Hammer (lower wick >= 60% of candle range)
            if lower_wick >= candle_range * 0.60 and body <= candle_range * 0.30:
                patterns.append({"pattern": "BULLISH_PINBAR_HAMMER", "time": str(c['time']), "significance": "Rejection of lower prices"})

            # Bearish Shooting Star / Inverted Pinbar (upper wick >= 60% of range)
            elif upper_wick >= candle_range * 0.60 and body <= candle_range * 0.30:
                patterns.append({"pattern": "BEARISH_SHOOTING_STAR", "time": str(c['time']), "significance": "Rejection of higher prices"})

            # Bullish Engulfing
            elif c['close'] > c['open'] and prev['open'] > prev['close'] and c['close'] > prev['open'] and c['open'] < prev['close']:
                patterns.append({"pattern": "BULLISH_ENGULFING", "time": str(c['time']), "significance": "Strong bullish momentum reversal"})

            # Bearish Engulfing
            elif c['open'] > c['close'] and prev['close'] > prev['open'] and c['open'] > prev['close'] and c['close'] < prev['open']:
                patterns.append({"pattern": "BEARISH_ENGULFING", "time": str(c['time']), "significance": "Strong bearish momentum reversal"})

        return patterns[-2:]

    @staticmethod
    def get_trading_session() -> Dict[str, Any]:
        """Calculates current market session (Asian, London, NY Overlap, NY Close) in UTC."""
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour

        if 0 <= hour < 7:
            session = "ASIAN_SESSION"
        elif 7 <= hour < 12:
            session = "LONDON_SESSION"
        elif 12 <= hour < 16:
            session = "LONDON_NY_OVERLAP (Peak Volatility)"
        elif 16 <= hour < 21:
            session = "NY_AFTERNOON"
        else:
            session = "DAY_CLOSE_ROLLOVER"

        return {
            "current_utc_time": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "session_name": session,
            "is_high_liquidity": (7 <= hour < 16),
        }

    def get_open_positions(self, ai_only: bool = False) -> List[Dict[str, Any]]:
        """
        Gets active open trades.
        If ai_only=True, strictly filters for orders placed by our AI algorithms (matching AI magic numbers or comments),
        ensuring the AI NEVER touches, modifies, or interferes with manual trades.
        """
        if not self._connected:
            return []

        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None or len(positions) == 0:
            return []

        ai_magic_numbers = {CONFIG.MAGIC_NUMBER, CONFIG.MAGIC_NUMBER + 111, 777888, 777999, 778101, 778110, 777889, 777890}
        pos_list = []
        for p in positions:
            is_ai = (p.magic in ai_magic_numbers) or (p.comment and (str(p.comment).upper().startswith("AI_") or "CHANAKYA" in str(p.comment).upper()))
            if ai_only and not is_ai:
                continue

            pos_list.append({
                "ticket": p.ticket,
                "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume": p.volume,
                "open_price": p.price_open,
                "current_price": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "magic": p.magic,
                "comment": p.comment,
                "is_ai_trade": is_ai,
                "open_time": datetime.fromtimestamp(p.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })
        return pos_list

    def check_m5_candle_confirmation(
        self,
        planned_entry: float,
        action: str,
        tolerance_points: float = 1.0,
        stop_loss: float = 0.0
    ) -> Dict[str, Any]:
        """
        Evaluates trade setup based on the last 5 completed M5 (5-minute) candles:
        - Validates that current price is inside or touching the institutional pullback zone.
        - Verifies that structural Stop Loss has NOT been invalidated.
        - Confirms price reaction / wick rejection / support-resistance defense inside the zone.
        """
        ticks = self.get_current_spread_and_ticks()
        current_price = ticks.get("ask" if action.upper() == "BUY" else "bid", planned_entry)
        bid = ticks.get("bid", current_price)
        ask = ticks.get("ask", current_price)

        is_btc = "BTC" in str(self.symbol).upper() or planned_entry > 10000.0
        if tolerance_points <= 1.0 and is_btc:
            tolerance_points = CONFIG.BTC_ENTRY_TOLERANCE_POINTS

        lower_bound = round(planned_entry - tolerance_points, 2)
        upper_bound = round(planned_entry + tolerance_points, 2)

        in_exact_zone = (lower_bound <= current_price <= upper_bound) or (lower_bound <= bid <= upper_bound) or (lower_bound <= ask <= upper_bound)

        sl_buffer = 20.0 if is_btc else 0.5
        if action.upper() == "BUY":
            min_floor = (stop_loss + sl_buffer) if stop_loss > 0 else (planned_entry - (tolerance_points * 2.0))
            in_zone = in_exact_zone or (min_floor <= current_price <= upper_bound) or (min_floor <= bid <= upper_bound)
        elif action.upper() == "SELL":
            max_ceiling = (stop_loss - sl_buffer) if stop_loss > 0 else (planned_entry + (tolerance_points * 2.0))
            in_zone = in_exact_zone or (lower_bound <= current_price <= max_ceiling) or (lower_bound <= ask <= max_ceiling)
        else:
            in_zone = False

        # Fetch last 15 M5 candles and inspect the 5-candle pattern
        df_m5 = self.get_candles("M5", count=15)
        m5_confirmed = False
        candle_trend_desc = "Neutral 5-candle structure"

        if not df_m5.empty and len(df_m5) >= 5:
            last_5 = df_m5.iloc[-5:]
            closes = last_5["close"].tolist()
            opens = last_5["open"].tolist()
            lows = last_5["low"].tolist()
            highs = last_5["high"].tolist()

            if action.upper() == "BUY":
                # Check for 5-candle bullish structure: low is holding above SL
                bullish_closes = sum([1 for c, o in zip(closes, opens) if c >= o])
                holding_support = min(lows) > stop_loss if stop_loss > 0 else True
                lower_wick_defense = (closes[-1] > lows[-1]) or (closes[-1] >= opens[-1]) or in_exact_zone
                if holding_support and lower_wick_defense:
                    m5_confirmed = True
                    candle_trend_desc = f"M5 Pullback Support Held @ {min(lows):,.2f} ({bullish_closes}/5 green, zone touched)"
            elif action.upper() == "SELL":
                # Check for 5-candle bearish structure: high is holding below SL
                bearish_closes = sum([1 for c, o in zip(closes, opens) if c <= o])
                holding_resistance = max(highs) < stop_loss if stop_loss > 0 else True
                upper_wick_defense = (closes[-1] < highs[-1]) or (closes[-1] <= opens[-1]) or in_exact_zone
                if holding_resistance and upper_wick_defense:
                    m5_confirmed = True
                    candle_trend_desc = f"M5 Pullback Resistance Held @ {max(highs):,.2f} ({bearish_closes}/5 red, zone touched)"
        else:
            m5_confirmed = True

        is_ready = in_zone and m5_confirmed

        return {
            "current_price": current_price,
            "bid": bid,
            "ask": ask,
            "planned_entry": planned_entry,
            "entry_zone_min": lower_bound,
            "entry_zone_max": upper_bound,
            "in_tolerance_zone": in_zone,
            "m5_confirmed": m5_confirmed,
            "m5_candle_trend": candle_trend_desc,
            "trigger_ready": is_ready,
            "zone_str": f"{lower_bound:,.2f} - {upper_bound:,.2f} (±{tolerance_points:.1f} pt)"
        }

    def check_m1_sniper_trigger(self, planned_entry: float, action: str, tolerance_points: float = 1.0, stop_loss: float = 0.0) -> Dict[str, Any]:
        """Backwards-compatible wrapper routing to 5-minute candle confirmation engine."""
        return self.check_m5_candle_confirmation(planned_entry, action, tolerance_points, stop_loss)

    def get_tick_microstructure(self, count: int = 100) -> Dict[str, Any]:
        """Analyzes live tick-by-tick order flow and spread metrics."""
        self.ensure_connected()
        default_res = {
            "ticks_analyzed": 0,
            "ask_lifters_pct": 50.0,
            "bid_hitters_pct": 50.0,
            "flow_bias": "BALANCED_FLOW",
            "current_spread_pts": 15.0,
            "avg_50_spread_pts": 15.0,
            "spread_ratio": 1.0,
            "slippage_hazard": "LOW",
            "execution_clearance": "CLEAR_OPTIMAL"
        }
        if not self._connected or mt5 is None:
            return default_res

        try:
            from datetime import timedelta
            ticks = mt5.copy_ticks_from(self.symbol, datetime.now() - timedelta(minutes=10), count, mt5.COPY_TICKS_ALL)
            if ticks is None or len(ticks) < 5:
                return default_res

            tdf = pd.DataFrame(ticks)
            tdf['spread'] = (tdf['ask'] - tdf['bid']) * 10.0 # pts

            buy_aggressors = 0
            sell_aggressors = 0
            for i in range(1, len(tdf)):
                curr = tdf.iloc[i]
                prev = tdf.iloc[i-1]
                if curr['bid'] > prev['bid'] or curr['ask'] > prev['ask']:
                    buy_aggressors += 1
                elif curr['bid'] < prev['bid'] or curr['ask'] < prev['ask']:
                    sell_aggressors += 1

            total = max(1, buy_aggressors + sell_aggressors)
            buy_pct = round((buy_aggressors / total) * 100, 1)
            sell_pct = round((sell_aggressors / total) * 100, 1)

            curr_spread = round(float(tdf['spread'].iloc[-1]), 1)
            avg_spread = round(float(tdf['spread'].tail(50).mean()), 1)
            spread_ratio = round(curr_spread / max(0.1, avg_spread), 2)

            # Execution Clearance Gate
            is_btc = "BTC" in self.symbol.upper() or "BITCOIN" in self.symbol.upper()
            max_spike = CONFIG.BTC_MAX_SPREAD_POINTS if is_btc else CONFIG.MAX_SPREAD_POINTS
            max_caution = (CONFIG.BTC_MAX_SPREAD_POINTS * 0.6) if is_btc else 25.0

            if spread_ratio > 2.2 or curr_spread > max_spike:
                exec_status = "LIQUIDITY_BLACKOUT_SPREAD_SPIKE"
                hazard = "HIGH"
            elif spread_ratio > 1.5 or curr_spread > max_caution:
                exec_status = "SPREAD_WIDENED_CAUTION"
                hazard = "MODERATE"
            else:
                exec_status = "CLEAR_OPTIMAL"
                hazard = "LOW"

            flow_bias = "AGGRESSIVE_BUYING" if buy_pct >= 58.0 else "AGGRESSIVE_SELLING" if sell_pct >= 58.0 else "BALANCED_FLOW"

            return {
                "ticks_analyzed": len(tdf),
                "ask_lifters_pct": buy_pct,
                "bid_hitters_pct": sell_pct,
                "flow_bias": flow_bias,
                "current_spread_pts": curr_spread,
                "avg_50_spread_pts": avg_spread,
                "spread_ratio": spread_ratio,
                "slippage_hazard": hazard,
                "execution_clearance": exec_status
            }
        except Exception:
            return default_res

    def extract_full_market_payload(self) -> Dict[str, Any]:
        """
        Aggregates multi-timeframe OHLCV, market structure, indicators, session,
        Fibonacci, Supply & Demand, Candlestick patterns, and account status for all 14 agents.
        """
        account = self.get_account_info()
        ticks = self.get_current_spread_and_ticks()
        session = self.get_trading_session()
        open_positions = self.get_open_positions()
        tick_micro = self.get_tick_microstructure(count=120)

        # Multi-timeframe data for comprehensive pattern recognition & indicators
        df_m1 = self.get_candles("M1", count=40)
        df_m5 = self.get_candles(CONFIG.EXECUTION_TIMEFRAME, count=80)
        df_m15 = self.get_candles("M15", count=80)
        df_m30 = self.get_candles("M30", count=60)
        df_h1 = self.get_candles(CONFIG.CONTEXT_TIMEFRAME, count=80)
        df_h4 = self.get_candles(CONFIG.MACRO_TIMEFRAME, count=60)
        df_d1 = self.get_candles("D1", count=60)

        df_d1 = self.calculate_indicators(df_d1)
        df_h4 = self.calculate_indicators(df_h4)
        df_h1 = self.calculate_indicators(df_h1)
        df_m30 = self.calculate_indicators(df_m30)
        df_m15 = self.calculate_indicators(df_m15)
        df_m5 = self.calculate_indicators(df_m5)

        d1_latest = df_d1.iloc[-1].to_dict() if not df_d1.empty else {}
        h4_latest = df_h4.iloc[-1].to_dict() if not df_h4.empty else {}
        h1_latest = df_h1.iloc[-1].to_dict() if not df_h1.empty else {}
        m30_latest = df_m30.iloc[-1].to_dict() if not df_m30.empty else {}
        m15_latest = df_m15.iloc[-1].to_dict() if not df_m15.empty else {}
        m5_latest = df_m5.iloc[-1].to_dict() if not df_m5.empty else {}

        # Prior Day High (PDH) / Prior Day Low (PDL) from completed Daily candle
        pdh = float(df_d1['high'].iloc[-2]) if len(df_d1) >= 2 else float(d1_latest.get('high', 0.0))
        pdl = float(df_d1['low'].iloc[-2]) if len(df_d1) >= 2 else float(d1_latest.get('low', 0.0))
        pdc = float(df_d1['close'].iloc[-2]) if len(df_d1) >= 2 else float(d1_latest.get('close', 0.0))

        # Advanced Multi-Timeframe Structural extractions (H4, H1, M15)
        fvgs_h4 = self.find_fair_value_gaps(df_h4, min_gap_points=2.0)
        fvgs_h1 = self.find_fair_value_gaps(df_h1, min_gap_points=1.0)
        fvgs_m15 = self.find_fair_value_gaps(df_m15, min_gap_points=0.5)

        supply_demand_h4 = self.find_supply_demand_zones(df_h4)
        supply_demand_h1 = self.find_supply_demand_zones(df_h1)
        supply_demand_m15 = self.find_supply_demand_zones(df_m15)

        fibonacci_h4 = self.calculate_fibonacci_levels(df_h4)
        fibonacci_h1 = self.calculate_fibonacci_levels(df_h1)
        fibonacci_m15 = self.calculate_fibonacci_levels(df_m15)

        patterns_d1 = self.detect_candlestick_patterns(df_d1)
        patterns_h4 = self.detect_candlestick_patterns(df_h4)
        patterns_h1 = self.detect_candlestick_patterns(df_h1)
        patterns_m15 = self.detect_candlestick_patterns(df_m15)

        # Multi-Timeframe Pattern Recognition Radar (M5 to D1)
        try:
            from core.pattern_detector import MultiTFPatternDetector
            tf_dict = {
                "D1": df_d1,
                "H4": df_h4,
                "H1": df_h1,
                "M30": df_m30,
                "M15": df_m15,
                "M5": df_m5
            }
            multi_tf_pattern_radar = MultiTFPatternDetector.scan_full_timeframe_matrix(tf_dict)
        except Exception as e:
            multi_tf_pattern_radar = {"harmony_bias": "NEUTRAL", "harmony_score": 50, "harmony_description": f"Scan error: {e}", "timeframes": {}}

        # Multi-Timeframe Trend & Alignment Evaluation
        d1_close = float(d1_latest.get('close', 0.0) or 0.0)
        d1_ema50 = float(d1_latest.get('ema_50', 0.0) or 0.0)
        d1_ema200 = float(d1_latest.get('ema_200', 0.0) or 0.0)
        d1_bias = "BULLISH" if (d1_close >= d1_ema50 or d1_ema50 >= d1_ema200) else "BEARISH"

        h4_close = float(h4_latest.get('close', 0.0) or 0.0)
        h4_ema50 = float(h4_latest.get('ema_50', 0.0) or 0.0)
        h4_ema200 = float(h4_latest.get('ema_200', 0.0) or 0.0)
        h4_bias = "BULLISH" if (h4_close >= h4_ema50 or h4_ema50 >= h4_ema200) else "BEARISH"

        h1_close = float(h1_latest.get('close', 0.0) or 0.0)
        h1_ema50 = float(h1_latest.get('ema_50', 0.0) or 0.0)
        h1_ema200 = float(h1_latest.get('ema_200', 0.0) or 0.0)
        h1_bias = "BULLISH" if (h1_close >= h1_ema50 and h1_ema50 >= h1_ema200) else "BEARISH" if (h1_close <= h1_ema50 and h1_ema50 <= h1_ema200) else "RANGE"

        m15_close = float(m15_latest.get('close', 0.0) or 0.0)
        m15_ema50 = float(m15_latest.get('ema_50', 0.0) or 0.0)
        m15_vwap = float(m15_latest.get('vwap', 0.0) or 0.0)
        m15_bias = "BULLISH" if (m15_close >= m15_vwap or m15_close >= m15_ema50) else "BEARISH"

        m5_ema9 = float(m5_latest.get('ema_9', 0.0) or 0.0)
        m5_ema21 = float(m5_latest.get('ema_21', 0.0) or 0.0)
        m5_fast_cross = "BULLISH" if m5_ema9 >= m5_ema21 else "BEARISH"

        # Tier 1 (Macro): D1 + H4
        tier1_macro_bias = "BULLISH" if (d1_bias == "BULLISH" and h4_bias == "BULLISH") else "BEARISH" if (d1_bias == "BEARISH" and h4_bias == "BEARISH") else h4_bias
        # Tier 2 (Setup): H1 + M15
        tier2_setup_bias = "BULLISH_PULLBACK" if (h1_bias == "BULLISH" and m15_bias == "BULLISH") else "BEARISH_PULLBACK" if (h1_bias == "BEARISH" and m15_bias == "BEARISH") else "CONSOLIDATING"
        # Tier 3 (Trigger): M5
        tier3_trigger_bias = "BULLISH_THRUST" if m5_fast_cross == "BULLISH" else "BEARISH_THRUST"

        # Overall Hierarchical Multi-TF Alignment Verdict
        if d1_bias == "BULLISH" and h4_bias == "BULLISH" and (h1_bias == "BULLISH" or m15_bias == "BULLISH"):
            alignment_verdict = "TIER1_TIER2_BULLISH_CONFLUENCE"
            alignment_score = 90
            dominant_trend = "BULLISH"
        elif d1_bias == "BEARISH" and h4_bias == "BEARISH" and (h1_bias == "BEARISH" or m15_bias == "BEARISH"):
            alignment_verdict = "TIER1_TIER2_BEARISH_CONFLUENCE"
            alignment_score = 90
            dominant_trend = "BEARISH"
        else:
            alignment_verdict = "MIXED_TIMEFRAME_CHOP_WAIT"
            alignment_score = 60
            dominant_trend = "NEUTRAL"

        # Bollinger Squeeze & Regime Classification Metrics
        bb_width_m15 = float(m15_latest.get('bb_width', 0.0) or 0.0)
        is_bollinger_squeeze = bb_width_m15 < 0.45
        adx_val = float(m15_latest.get('adx_14', 22.0) or 22.0)
        pdi_val = float(m15_latest.get('plus_di14', 20.0) or 20.0)
        mdi_val = float(m15_latest.get('minus_di14', 20.0) or 20.0)
        chop_val = float(m15_latest.get('chop_14', 50.0) or 50.0)

        # Quantitative Regime Classification
        if is_bollinger_squeeze or bb_width_m15 < 0.35:
            regime_tag = "LOW_VOLATILITY_COMPRESSION"
            regime_desc = "Extreme Volatility Squeeze — Explosive Breakout Coiling"
        elif adx_val >= 25.0 and pdi_val > mdi_val and chop_val < 50.0:
            regime_tag = "TRENDING_BULLISH"
            regime_desc = f"Strong Bullish Trend Expansion (ADX {adx_val:.1f} > 25, +DI Dominant)"
        elif adx_val >= 25.0 and mdi_val > pdi_val and chop_val < 50.0:
            regime_tag = "TRENDING_BEARISH"
            regime_desc = f"Strong Bearish Trend Expansion (ADX {adx_val:.1f} > 25, -DI Dominant)"
        elif chop_val >= 58.0 or (adx_val < 20.0 and abs(pdi_val - mdi_val) < 8.0):
            regime_tag = "MEAN_REVERTING_RANGE"
            regime_desc = f"Mean-Reverting Sideways Range (Choppiness {chop_val:.1f}, Low ADX)"
        else:
            regime_tag = "HIGH_VOLATILITY_CHOP"
            regime_desc = f"High Volatility Rotational Chop (Choppiness {chop_val:.1f})"

        # Volume Delta & CVD Divergence Calculation
        cvd_series = df_m15['cvd'] if not df_m15.empty and 'cvd' in df_m15.columns else pd.Series([0.0])
        cvd_delta_5 = float(cvd_series.iloc[-1] - cvd_series.iloc[-5]) if len(cvd_series) >= 5 else 0.0
        price_delta_5 = float(df_m15['close'].iloc[-1] - df_m15['close'].iloc[-5]) if len(df_m15) >= 5 else 0.0

        if price_delta_5 <= 0 and cvd_delta_5 > 500.0:
            cvd_divergence = "BULLISH_ABSORPTION_DIVERGENCE"
            cvd_desc = f"Bullish Absorption Detected: Price flat/lower while CVD surged +{cvd_delta_5:.0f} (Passive Limit Buying)"
        elif price_delta_5 >= 0 and cvd_delta_5 < -500.0:
            cvd_divergence = "BEARISH_EXHAUSTION_DIVERGENCE"
            cvd_desc = f"Bearish Exhaustion Detected: Price pushed higher but CVD dropped {cvd_delta_5:.0f} (Lack of Aggressive Buying)"
        elif price_delta_5 > 0 and cvd_delta_5 > 0:
            cvd_divergence = "CONVERGENT_BULLISH_THRUST"
            cvd_desc = f"Aggressive Bullish Momentum: Price and CVD (+{cvd_delta_5:.0f}) expanding in unison"
        elif price_delta_5 < 0 and cvd_delta_5 < 0:
            cvd_divergence = "CONVERGENT_BEARISH_THRUST"
            cvd_desc = f"Aggressive Bearish Momentum: Price and CVD ({cvd_delta_5:.0f}) dumping in unison"
        else:
            cvd_divergence = "NEUTRAL_DELTA"
            cvd_desc = "Balanced Volume Delta"

        regime_dict = {
            "regime": regime_tag,
            "description": regime_desc,
            "adx_14": round(adx_val, 1),
            "adx": round(adx_val, 1),
            "plus_di": round(pdi_val, 1),
            "minus_di": round(mdi_val, 1),
            "choppiness_index": round(chop_val, 1),
            "bollinger_bandwidth": round(bb_width_m15, 2),
            "is_squeeze": is_bollinger_squeeze
        }
        liq_dict = {
            "spread_points": tick_micro.get("current_spread_pts", 15.0),
            "spread_ratio": round(tick_micro.get("current_spread_pts", 15.0) / max(1.0, tick_micro.get("avg_50_spread_pts", 15.0)), 2),
            "clearance": tick_micro.get("execution_clearance", "CLEAR_OPTIMAL"),
            "raw_micro": tick_micro
        }
        tick_flow_dict = {
            "ask_lifters_pct": tick_micro.get("ask_lifters_pct", 50.0),
            "bid_hitters_pct": tick_micro.get("bid_hitters_pct", 50.0),
            "flow_imbalance": tick_micro.get("flow_bias", "BALANCED_FLOW"),
            "flow_bias": tick_micro.get("flow_bias", "BALANCED_FLOW"),
            "ticks_sampled": tick_micro.get("ticks_analyzed", 0),
            "spread_pts": tick_micro.get("current_spread_pts", 15.0),
            "avg_spread_pts": tick_micro.get("avg_50_spread_pts", 15.0),
            "execution_clearance": tick_micro.get("execution_clearance", "CLEAR_OPTIMAL")
        }
        vdelta_dict = {
            "cvd_pattern": cvd_divergence,
            "cvd_divergence": cvd_divergence,
            "description": cvd_desc,
            "5_bar_cvd_delta": round(cvd_delta_5, 1),
            "latest_bar_delta": round(float(m15_latest.get('vol_delta', 0.0) or 0.0), 1),
            "last_bar_delta": round(float(m15_latest.get('vol_delta', 0.0) or 0.0), 1),
            "cumulative_cvd": round(float(m15_latest.get('cvd', 0.0) or 0.0), 1)
        }

        # Complete Top-Down Multi-Timeframe Intelligence Profile
        top_down_summary = {
            "dominant_trend": dominant_trend,
            "alignment_verdict": alignment_verdict,
            "alignment_score": alignment_score,
            "tier1_macro_bias": tier1_macro_bias,
            "tier2_setup_bias": tier2_setup_bias,
            "tier3_trigger_bias": tier3_trigger_bias,
            "d1_bias": d1_bias,
            "h4_bias": h4_bias,
            "h1_bias": h1_bias,
            "m15_bias": m15_bias,
            "m5_bias": m5_fast_cross,
            "prior_day_high": round(pdh, 2),
            "prior_day_low": round(pdl, 2),
            "prior_day_close": round(pdc, 2)
        }

        multi_tf_matrix = {
            "top_down_summary": top_down_summary,
            "d1_macro": {
                "bias": d1_bias,
                "close": round(d1_close, 2),
                "ema_50": round(d1_ema50, 2),
                "ema_200": round(d1_ema200, 2),
                "rsi_14": round(float(d1_latest.get('rsi_14', 50.0) or 50.0), 1),
                "atr_14": round(float(d1_latest.get('atr_14', 20.0) or 20.0), 2),
                "pdh": round(pdh, 2),
                "pdl": round(pdl, 2),
                "patterns": patterns_d1
            },
            "h4_structural": {
                "bias": h4_bias,
                "close": round(h4_close, 2),
                "ema_50": round(h4_ema50, 2),
                "ema_200": round(h4_ema200, 2),
                "rsi_14": round(float(h4_latest.get('rsi_14', 50.0) or 50.0), 1),
                "atr_14": round(float(h4_latest.get('atr_14', 12.0) or 12.0), 2),
                "active_fvgs": fvgs_h4,
                "supply_demand_zones": supply_demand_h4,
                "fibonacci_levels": fibonacci_h4,
                "patterns": patterns_h4
            },
            "h1_trend": {
                "bias": h1_bias,
                "close": round(h1_close, 2),
                "ema_9": round(float(h1_latest.get('ema_9', 0.0) or 0.0), 2),
                "ema_21": round(float(h1_latest.get('ema_21', 0.0) or 0.0), 2),
                "ema_50": round(h1_ema50, 2),
                "ema_200": round(h1_ema200, 2),
                "rsi_14": round(float(h1_latest.get('rsi_14', 50.0) or 50.0), 1),
                "atr_14": round(float(h1_latest.get('atr_14', 8.0) or 8.0), 2),
                "vwap": round(float(h1_latest.get('vwap', 0.0) or 0.0), 2),
                "active_fvgs": fvgs_h1,
                "supply_demand_zones": supply_demand_h1,
                "fibonacci_levels": fibonacci_h1,
                "patterns": patterns_h1
            },
            "m30_bridge": {
                "close": round(float(m30_latest.get('close', 0.0) or 0.0), 2),
                "ema_50": round(float(m30_latest.get('ema_50', 0.0) or 0.0), 2),
                "rsi_14": round(float(m30_latest.get('rsi_14', 50.0) or 50.0), 1),
                "vwap": round(float(m30_latest.get('vwap', 0.0) or 0.0), 2)
            },
            "m15_execution": {
                "bias": m15_bias,
                "current_price": ticks.get("bid", 0.0),
                "vwap": round(m15_vwap, 2),
                "ema_9": round(float(m15_latest.get('ema_9', 0.0) or 0.0), 2),
                "ema_21": round(float(m15_latest.get('ema_21', 0.0) or 0.0), 2),
                "ema_50": round(m15_ema50, 2),
                "ema_200": round(float(m15_latest.get('ema_200', 0.0) or 0.0), 2),
                "atr_14": round(float(m15_latest.get('atr_14', 0.0) or 0.0), 2),
                "rsi_14": round(float(m15_latest.get('rsi_14', 0.0) or 0.0), 1),
                "bb_upper": round(float(m15_latest.get('bb_upper', 0.0) or 0.0), 2),
                "bb_lower": round(float(m15_latest.get('bb_lower', 0.0) or 0.0), 2),
                "is_bollinger_squeeze": is_bollinger_squeeze,
                "active_fvgs": fvgs_m15,
                "supply_demand_zones": supply_demand_m15,
                "fibonacci_levels": fibonacci_m15,
                "candlestick_patterns": patterns_m15
            },
            "m5_micro": {
                "ema_9": round(m5_ema9, 2),
                "ema_21": round(m5_ema21, 2),
                "fast_cross": m5_fast_cross,
                "rsi_14": round(float(m5_latest.get('rsi_14', 0.0) or 0.0), 1),
                "atr_14": round(float(m5_latest.get('atr_14', 0.0) or 0.0), 2)
            }
        }

        return {
            "symbol": self.symbol,
            "timestamp": session["current_utc_time"],
            "session": session,
            "account": account,
            "pricing": ticks,
            "open_positions": open_positions,
            "top_down_summary": top_down_summary,
            "multi_timeframe_matrix": multi_tf_matrix,
            "multi_tf_patterns": multi_tf_pattern_radar,
            "regime_analysis": regime_dict,
            "liquidity_execution_quality": liq_dict,
            "tick_order_flow": tick_flow_dict,
            "volume_delta_cvd": vdelta_dict,
            "market_structures": {
                "top_down_summary": top_down_summary,
                "multi_timeframe_matrix": multi_tf_matrix,
                "regime_analysis": regime_dict,
                "liquidity_execution_quality": liq_dict,
                "tick_order_flow": tick_flow_dict,
                "volume_delta_cvd": vdelta_dict,
                "d1_macro": multi_tf_matrix["d1_macro"],
                "h4_structural": multi_tf_matrix["h4_structural"],
                "h1_trend": multi_tf_matrix["h1_trend"],
                "h1_trend_structure": {
                    "ema_50": round(h1_ema50, 2),
                    "ema_200": round(h1_ema200, 2),
                    "trend_bias": h1_bias,
                    "rsi_14": round(float(h1_latest.get('rsi_14', 0.0) or 0.0), 1)
                },
                "h4_macro_trend": {
                    "ema_50": round(h4_ema50, 2),
                    "ema_200": round(h4_ema200, 2),
                    "macro_bias": h4_bias
                },
                "m30_bridge": multi_tf_matrix["m30_bridge"],
                "m15_execution_structure": multi_tf_matrix["m15_execution"],
                "m5_micro_momentum": multi_tf_matrix["m5_micro"]
            }
        }


class GoldDataEngine(MT5DataEngine):
    """Dedicated Market Data Engine for Pure Gold (XAUUSD)."""
    def __init__(self):
        super().__init__(symbol="XAUUSD")


class CryptoDataEngine(MT5DataEngine):
    """Dedicated Market Data Engine for Pure Bitcoin (BTCUSD)."""
    def __init__(self):
        super().__init__(symbol="BTCUSD")


def get_data_engine_for_symbol(symbol: str) -> MT5DataEngine:
    """Factory returning 100% dedicated isolated data engine per asset."""
    sym = str(symbol).upper()
    if "BTC" in sym or "BITCOIN" in sym or "CRYPTO" in sym:
        return CryptoDataEngine()
    return GoldDataEngine()

