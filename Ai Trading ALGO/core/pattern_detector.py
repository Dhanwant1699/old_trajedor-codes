"""
Algorithmic Multi-Timeframe Pattern Recognition Engine for AI Trading Council.
Scans multi-timeframe OHLCV data (M5, M15, M30, H1, H4, D1) to detect:
1. Reversals: Double Tops (M-Shape), Double Bottoms (W-Shape), Head & Shoulders, Inverse H&S, Quasimodo (QM)
2. Continuations: Bull / Bear Flags, Ascending / Descending Triangles, Symmetrical Triangles, Wedges
3. Market Structure: Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL), BOS, CHoCH
4. Candlesticks: Rejection Pinbars, Bullish/Bearish Engulfing, Morning/Evening Stars, Tweezers
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple


class MultiTFPatternDetector:
    @staticmethod
    def find_pivots(df: pd.DataFrame, window: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Finds swing highs and swing lows across candlestick history."""
        if len(df) < window * 2 + 1:
            return [], []

        swing_highs = []
        swing_lows = []

        highs = df['high'].values
        lows = df['low'].values
        times = df['time'].values if 'time' in df.columns else [i for i in range(len(df))]

        for i in range(window, len(df) - window):
            current_high = highs[i]
            current_low = lows[i]

            # Swing High
            if all(current_high >= highs[i - j] for j in range(1, window + 1)) and \
               all(current_high > highs[i + j] for j in range(1, window + 1)):
                swing_highs.append({
                    "index": i,
                    "price": round(float(current_high), 2),
                    "time": str(times[i])
                })

            # Swing Low
            if all(current_low <= lows[i - j] for j in range(1, window + 1)) and \
               all(current_low < lows[i + j] for j in range(1, window + 1)):
                swing_lows.append({
                    "index": i,
                    "price": round(float(current_low), 2),
                    "time": str(times[i])
                })

        return swing_highs, swing_lows

    @classmethod
    def detect_market_structure(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Detects HH/HL (Bullish) or LH/LL (Bearish) trend structure and Break of Structure (BOS)."""
        if df.empty or len(df) < 20:
            return {"bias": "NEUTRAL", "structure": "Consolidation", "last_swing_high": 0.0, "last_swing_low": 0.0}

        swing_highs, swing_lows = cls.find_pivots(df, window=4)
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"bias": "NEUTRAL", "structure": "Consolidation", "last_swing_high": 0.0, "last_swing_low": 0.0}

        sh1, sh2 = swing_highs[-2], swing_highs[-1]
        sl1, sl2 = swing_lows[-2], swing_lows[-1]

        curr_close = float(df['close'].iloc[-1])

        # Check Higher Highs and Higher Lows
        if sh2['price'] > sh1['price'] and sl2['price'] > sl1['price']:
            structure = "Higher Highs & Higher Lows (HH/HL)"
            bias = "BULLISH"
            if curr_close > sh2['price']:
                structure += " • Bullish BOS Active"
        # Check Lower Lows and Lower Highs
        elif sh2['price'] < sh1['price'] and sl2['price'] < sl1['price']:
            structure = "Lower Highs & Lower Lows (LH/LL)"
            bias = "BEARISH"
            if curr_close < sl2['price']:
                structure += " • Bearish BOS Active"
        # Change of Character (CHoCH) - Bullish Reversal
        elif sl2['price'] > sl1['price'] and curr_close > sh2['price']:
            structure = "Bullish Change of Character (CHoCH)"
            bias = "BULLISH"
        # Change of Character (CHoCH) - Bearish Reversal
        elif sh2['price'] < sh1['price'] and curr_close < sl2['price']:
            structure = "Bearish Change of Character (CHoCH)"
            bias = "BEARISH"
        else:
            structure = "Range-Bound / Consolidating Structure"
            bias = "NEUTRAL"

        return {
            "bias": bias,
            "structure": structure,
            "last_swing_high": sh2['price'],
            "last_swing_low": sl2['price']
        }

    @classmethod
    def detect_chart_patterns(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identifies geometric chart patterns with:
        1. Touch Point Validation: Counts reactions to trendlines/necklines.
        2. Breakout Volume Confirmation: Validates breakouts using 20-bar relative volume.
        3. Structural Stop Loss & Measured Take Profit Points: Calculates precise risk/reward invalidation levels.
        """
        patterns = []
        if df.empty or len(df) < 30:
            return patterns

        swing_highs, swing_lows = cls.find_pivots(df, window=4)
        curr_price = float(df['close'].iloc[-1])
        curr_vol = float(df['volume'].iloc[-1]) if 'volume' in df.columns else 1000.0
        avg_vol = float(df['volume'].tail(20).mean()) if 'volume' in df.columns else 1000.0
        vol_ratio = round(curr_vol / max(1.0, avg_vol), 2)
        is_high_volume_breakout = vol_ratio >= 1.25

        atr = float((df['high'] - df['low']).rolling(14).mean().iloc[-1] or 5.0)

        # 1. Double Bottom (W-Pattern)
        if len(swing_lows) >= 2 and len(swing_highs) >= 1:
            sl1, sl2 = swing_lows[-2], swing_lows[-1]
            if sl2['index'] > sl1['index']:
                if abs(sl1['price'] - sl2['price']) <= (atr * 0.8):
                    mid_highs = [h for h in swing_highs if sl1['index'] < h['index'] < sl2['index']]
                    if mid_highs:
                        neckline = mid_highs[0]['price']
                        base_depth = neckline - sl2['price']
                        is_broken = curr_price >= neckline
                        sl_level = round(sl2['price'] - max(1.50, atr * 0.25), 2)
                        tp1 = round(neckline + (base_depth * 0.618), 2)
                        tp2 = round(neckline + base_depth, 2)
                        
                        # Count touches near support floor
                        support_touches = sum(1 for l in df['low'].iloc[sl1['index']:] if abs(l - sl1['price']) <= (atr * 0.35))
                        touch_strength = "HIGH (3+ touches)" if support_touches >= 3 else "STANDARD (2 touches)"

                        status = "High-Volume Breakout Confirmed" if (is_broken and is_high_volume_breakout) else (
                            "Breakout with Moderate Volume" if is_broken else "Forming / Approaching Neckline"
                        )
                        conf = 92 if (is_broken and is_high_volume_breakout) else (85 if is_broken else 76)

                        patterns.append({
                            "name": "Double Bottom (W-Pattern)",
                            "type": "REVERSAL",
                            "bias": "BULLISH",
                            "neckline": neckline,
                            "support_level": round((sl1['price'] + sl2['price']) / 2.0, 2),
                            "touch_count": support_touches,
                            "touch_strength": touch_strength,
                            "breakout_volume_ratio": vol_ratio,
                            "is_high_volume_breakout": is_high_volume_breakout,
                            "stop_loss": sl_level,
                            "take_profit_1": tp1,
                            "take_profit_2": tp2,
                            "target_price": tp2,
                            "status": status,
                            "confidence": conf,
                            "description": f"Double Bottom testing support ({touch_strength}). Target: {tp2:.2f} | SL: {sl_level:.2f}"
                        })

        # 2. Double Top (M-Pattern)
        if len(swing_highs) >= 2 and len(swing_lows) >= 1:
            sh1, sh2 = swing_highs[-2], swing_highs[-1]
            if sh2['index'] > sh1['index']:
                if abs(sh1['price'] - sh2['price']) <= (atr * 0.8):
                    mid_lows = [l for l in swing_lows if sh1['index'] < l['index'] < sh2['index']]
                    if mid_lows:
                        neckline = mid_lows[0]['price']
                        top_height = sh2['price'] - neckline
                        is_broken = curr_price <= neckline
                        sl_level = round(sh2['price'] + max(1.50, atr * 0.25), 2)
                        tp1 = round(neckline - (top_height * 0.618), 2)
                        tp2 = round(neckline - top_height, 2)

                        resistance_touches = sum(1 for h in df['high'].iloc[sh1['index']:] if abs(h - sh1['price']) <= (atr * 0.35))
                        touch_strength = "HIGH (3+ touches)" if resistance_touches >= 3 else "STANDARD (2 touches)"

                        status = "High-Volume Breakdown Confirmed" if (is_broken and is_high_volume_breakout) else (
                            "Breakdown with Moderate Volume" if is_broken else "Forming / Approaching Neckline"
                        )
                        conf = 92 if (is_broken and is_high_volume_breakout) else (85 if is_broken else 76)

                        patterns.append({
                            "name": "Double Top (M-Pattern)",
                            "type": "REVERSAL",
                            "bias": "BEARISH",
                            "neckline": neckline,
                            "resistance_level": round((sh1['price'] + sh2['price']) / 2.0, 2),
                            "touch_count": resistance_touches,
                            "touch_strength": touch_strength,
                            "breakout_volume_ratio": vol_ratio,
                            "is_high_volume_breakout": is_high_volume_breakout,
                            "stop_loss": sl_level,
                            "take_profit_1": tp1,
                            "take_profit_2": tp2,
                            "target_price": tp2,
                            "status": status,
                            "confidence": conf,
                            "description": f"Double Top testing resistance ({touch_strength}). Target: {tp2:.2f} | SL: {sl_level:.2f}"
                        })

        # 3. Head and Shoulders / Inverse Head and Shoulders
        if len(swing_highs) >= 3 and len(swing_lows) >= 2:
            left_s, head, right_s = swing_highs[-3], swing_highs[-2], swing_highs[-1]
            if head['price'] > left_s['price'] and head['price'] > right_s['price']:
                if abs(left_s['price'] - right_s['price']) <= (atr * 1.2):
                    neckline = min(swing_lows[-2]['price'], swing_lows[-1]['price'])
                    is_broken = curr_price < neckline
                    sl_level = round(right_s['price'] + max(1.50, atr * 0.25), 2)
                    tp1 = round(neckline - (head['price'] - neckline) * 0.618, 2)
                    tp2 = round(neckline - (head['price'] - neckline), 2)
                    conf = 94 if (is_broken and is_high_volume_breakout) else (88 if is_broken else 78)

                    patterns.append({
                        "name": "Head & Shoulders Top",
                        "type": "REVERSAL",
                        "bias": "BEARISH",
                        "neckline": neckline,
                        "head_price": head['price'],
                        "right_shoulder_sl": sl_level,
                        "stop_loss": sl_level,
                        "take_profit_1": tp1,
                        "take_profit_2": tp2,
                        "target_price": tp2,
                        "breakout_volume_ratio": vol_ratio,
                        "is_high_volume_breakout": is_high_volume_breakout,
                        "status": "High-Volume Neckline Breakdown" if (is_broken and is_high_volume_breakout) else ("Neckline Broken" if is_broken else "Right Shoulder Formed"),
                        "confidence": conf,
                        "description": f"H&S Top: Right Shoulder @ {right_s['price']:.2f}. Target: {tp2:.2f} | SL: {sl_level:.2f}"
                    })

        if len(swing_lows) >= 3 and len(swing_highs) >= 2:
            left_s, head, right_s = swing_lows[-3], swing_lows[-2], swing_lows[-1]
            if head['price'] < left_s['price'] and head['price'] < right_s['price']:
                if abs(left_s['price'] - right_s['price']) <= (atr * 1.2):
                    neckline = max(swing_highs[-2]['price'], swing_highs[-1]['price'])
                    is_broken = curr_price > neckline
                    sl_level = round(right_s['price'] - max(1.50, atr * 0.25), 2)
                    tp1 = round(neckline + (neckline - head['price']) * 0.618, 2)
                    tp2 = round(neckline + (neckline - head['price']), 2)
                    conf = 94 if (is_broken and is_high_volume_breakout) else (88 if is_broken else 78)

                    patterns.append({
                        "name": "Inverse Head & Shoulders",
                        "type": "REVERSAL",
                        "bias": "BULLISH",
                        "neckline": neckline,
                        "head_price": head['price'],
                        "right_shoulder_sl": sl_level,
                        "stop_loss": sl_level,
                        "take_profit_1": tp1,
                        "take_profit_2": tp2,
                        "target_price": tp2,
                        "breakout_volume_ratio": vol_ratio,
                        "is_high_volume_breakout": is_high_volume_breakout,
                        "status": "High-Volume Neckline Breakout" if (is_broken and is_high_volume_breakout) else ("Neckline Broken" if is_broken else "Right Shoulder Formed"),
                        "confidence": conf,
                        "description": f"Inverse H&S: Right Shoulder @ {right_s['price']:.2f}. Target: {tp2:.2f} | SL: {sl_level:.2f}"
                    })

        # 4. Continuation Formations: Bull Flag & Bear Flag
        if len(df) >= 25:
            ema_21 = float(df['close'].ewm(span=21).mean().iloc[-1])
            ema_50 = float(df['close'].ewm(span=50).mean().iloc[-1])
            recent_candles = df.tail(10)
            range_span = float(recent_candles['high'].max() - recent_candles['low'].min())

            # Bull Flag: Strong prior expansion up, followed by tight shallow consolidation above EMA 50
            if ema_21 > ema_50 and curr_price > ema_50 and range_span <= (atr * 3.5):
                prior_move = float(df['close'].iloc[-11] - df['close'].iloc[-25])
                if prior_move > (atr * 2.5):
                    channel_low = float(recent_candles['low'].min())
                    sl_level = round(channel_low - max(1.50, atr * 0.25), 2)
                    tp1 = round(curr_price + prior_move * 0.5, 2)
                    tp2 = round(curr_price + prior_move * 0.85, 2)

                    patterns.append({
                        "name": "Bull Flag (Continuation Channel)",
                        "type": "CONTINUATION",
                        "bias": "BULLISH",
                        "pole_size": round(prior_move, 2),
                        "stop_loss": sl_level,
                        "take_profit_1": tp1,
                        "take_profit_2": tp2,
                        "target_price": tp2,
                        "breakout_volume_ratio": vol_ratio,
                        "status": "High-Volume Pole Breakout" if is_high_volume_breakout else "Channel Consolidation / Breakout Ready",
                        "confidence": 91 if is_high_volume_breakout else 85,
                        "description": f"Bull Flag: Flag pole +{prior_move:.2f} pts. Target: {tp2:.2f} | SL: {sl_level:.2f}"
                    })

            # Bear Flag: Strong prior dump down, followed by tight shallow consolidation below EMA 50
            elif ema_21 < ema_50 and curr_price < ema_50 and range_span <= (atr * 3.5):
                prior_move = float(df['close'].iloc[-25] - df['close'].iloc[-11])
                if prior_move > (atr * 2.5):
                    channel_high = float(recent_candles['high'].max())
                    sl_level = round(channel_high + max(1.50, atr * 0.25), 2)
                    tp1 = round(curr_price - prior_move * 0.5, 2)
                    tp2 = round(curr_price - prior_move * 0.85, 2)

                    patterns.append({
                        "name": "Bear Flag (Continuation Channel)",
                        "type": "CONTINUATION",
                        "bias": "BEARISH",
                        "pole_size": round(prior_move, 2),
                        "stop_loss": sl_level,
                        "take_profit_1": tp1,
                        "take_profit_2": tp2,
                        "target_price": tp2,
                        "breakout_volume_ratio": vol_ratio,
                        "status": "High-Volume Pole Breakdown" if is_high_volume_breakout else "Channel Consolidation / Breakdown Ready",
                        "confidence": 91 if is_high_volume_breakout else 85,
                        "description": f"Bear Flag: Flag pole -{prior_move:.2f} pts. Target: {tp2:.2f} | SL: {sl_level:.2f}"
                    })

        # 5. Triangles (Ascending, Descending, Symmetrical)
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            sh1, sh2 = swing_highs[-2], swing_highs[-1]
            sl1, sl2 = swing_lows[-2], swing_lows[-1]

            # Ascending Triangle: Flat Highs, Rising Lows
            if abs(sh1['price'] - sh2['price']) <= (atr * 0.5) and sl2['price'] > (sl1['price'] + atr * 0.3):
                height = sh2['price'] - sl1['price']
                sl_level = round(sl2['price'] - max(1.50, atr * 0.25), 2)
                tp1 = round(sh2['price'] + height * 0.618, 2)
                tp2 = round(sh2['price'] + height, 2)
                is_broken = curr_price > sh2['price']

                patterns.append({
                    "name": "Ascending Triangle (Bullish)",
                    "type": "CONTINUATION",
                    "bias": "BULLISH",
                    "resistance_level": round(sh2['price'], 2),
                    "support_level": round(sl2['price'], 2),
                    "stop_loss": sl_level,
                    "take_profit_1": tp1,
                    "take_profit_2": tp2,
                    "target_price": tp2,
                    "breakout_volume_ratio": vol_ratio,
                    "status": "High-Volume Resistance Breakout" if (is_broken and is_high_volume_breakout) else "Coiling at Resistance",
                    "confidence": 90 if (is_broken and is_high_volume_breakout) else 83,
                    "description": f"Ascending Triangle: Rising lows pressuring {sh2['price']:.2f}. Target: {tp2:.2f} | SL: {sl_level:.2f}"
                })

            # Descending Triangle: Flat Lows, Lower Highs
            elif abs(sl1['price'] - sl2['price']) <= (atr * 0.5) and sh2['price'] < (sh1['price'] - atr * 0.3):
                height = sh1['price'] - sl2['price']
                sl_level = round(sh2['price'] + max(1.50, atr * 0.25), 2)
                tp1 = round(sl2['price'] - height * 0.618, 2)
                tp2 = round(sl2['price'] - height, 2)
                is_broken = curr_price < sl2['price']

                patterns.append({
                    "name": "Descending Triangle (Bearish)",
                    "type": "CONTINUATION",
                    "bias": "BEARISH",
                    "resistance_level": round(sh2['price'], 2),
                    "support_level": round(sl2['price'], 2),
                    "stop_loss": sl_level,
                    "take_profit_1": tp1,
                    "take_profit_2": tp2,
                    "target_price": tp2,
                    "breakout_volume_ratio": vol_ratio,
                    "status": "High-Volume Support Breakdown" if (is_broken and is_high_volume_breakout) else "Coiling at Support",
                    "confidence": 90 if (is_broken and is_high_volume_breakout) else 83,
                    "description": f"Descending Triangle: Lower highs pressuring {sl2['price']:.2f}. Target: {tp2:.2f} | SL: {sl_level:.2f}"
                })

            # Symmetrical Triangle / Coil: Lower Highs + Higher Lows
            elif sh2['price'] < sh1['price'] and sl2['price'] > sl1['price']:
                sl_buy = round(sl2['price'] - max(1.50, atr * 0.25), 2)
                sl_sell = round(sh2['price'] + max(1.50, atr * 0.25), 2)
                patterns.append({
                    "name": "Symmetrical Triangle (Volatility Coil)",
                    "type": "CONVERGENCE",
                    "bias": "NEUTRAL",
                    "apex_upper": round(sh2['price'], 2),
                    "apex_lower": round(sl2['price'], 2),
                    "breakout_volume_ratio": vol_ratio,
                    "status": "Volatility Squeeze Near Apex",
                    "confidence": 76,
                    "description": f"Symmetrical Triangle: Range coiling between {sl2['price']:.2f} and {sh2['price']:.2f}."
                })

        return patterns

    @classmethod
    def detect_candlestick_triggers(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detects all 38 Institutional Candlestick Patterns (Groww Pro Encyclopedia):
        Bullish Patterns:
          1. Bullish Engulfing
          2. Hammer
          3. Morning Star
          4. Piercing Line
          5. Bullish Harami
          6. Three White Soldiers
          7. Inverted Hammer
          8. Dragonfly Doji
          9. Bullish Abandoned Baby
          10. Three Inside Up
          11. Three Outside Up
          12. Bullish Kicker
          13. Tweezer Bottom
          14. Rising Three Methods
          15. Concealing Baby Swallow
          16. Mat Hold (Bullish)
          17. Bullish Separating Lines
          18. Bullish Belt Hold
          19. Three-Line Strike (Bullish)
          20. Ladder Bottom
          21. Meeting Lines (Bullish)
        Bearish Patterns:
          22. Bearish Engulfing
          23. Bearish Belt Hold
          24. Three Black Crows
          25. Bearish Three-Line Strike
          26. Bearish Hanging Man
          27. Upside Gap Two Crows
          28. Bearish Evening Star
          29. Bearish Shooting Star
          30. Bearish Harami
          31. Bearish Doji Star
          32. Bearish Abandoned Baby
          33. Bearish Tweezer Top
          34. Bearish Kicker
          35. Bearish Three Inside Down
          36. Bearish Three Outside Down
          37. Bearish Mat Hold / Falling Three Methods
          38. Dark Cloud Cover
        """
        triggers = []
        if len(df) < 5:
            return triggers

        # Candles from latest (c0) to 4 bars back (c4)
        c0 = df.iloc[-1]
        c1 = df.iloc[-2]
        c2 = df.iloc[-3] if len(df) >= 3 else None
        c3 = df.iloc[-4] if len(df) >= 4 else None
        c4 = df.iloc[-5] if len(df) >= 5 else None

        o0, h0, l0, c0_val = float(c0['open']), float(c0['high']), float(c0['low']), float(c0['close'])
        o1, h1, l1, c1_val = float(c1['open']), float(c1['high']), float(c1['low']), float(c1['close'])

        range0 = max(0.01, h0 - l0)
        body0 = abs(c0_val - o0)
        upper_wick0 = h0 - max(o0, c0_val)
        lower_wick0 = min(o0, c0_val) - l0

        range1 = max(0.01, h1 - l1)
        body1 = abs(c1_val - o1)
        upper_wick1 = h1 - max(o1, c1_val)
        lower_wick1 = min(o1, c1_val) - l1

        # Trend context over previous 10 candles
        tail = df.iloc[-12:-1] if len(df) >= 12 else df.iloc[:-1]
        prior_slope = float(tail['close'].iloc[-1] - tail['close'].iloc[0]) if len(tail) >= 2 else 0.0
        is_prior_downtrend = prior_slope < 0 or c1_val < o1
        is_prior_uptrend = prior_slope > 0 or c1_val > o1

        # =========================================================================
        # 1. SINGLE CANDLESTICK PATTERNS (Bullish & Bearish)
        # =========================================================================

        # 18. Bullish Belt Hold (Opens at low of the day, drives strongly to high, no lower shadow)
        if c0_val > o0 and (lower_wick0 / range0) <= 0.05 and (body0 / range0) >= 0.70 and is_prior_downtrend:
            triggers.append({
                "name": "Bullish Belt Hold",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 88,
                "description": "Opened at the extreme low and surged with zero lower shadow; aggressive buyers in control."
            })

        # 23. Bearish Belt Hold (Opens at high of the day, drives strongly to low, no upper shadow)
        if c0_val < o0 and (upper_wick0 / range0) <= 0.05 and (body0 / range0) >= 0.70 and is_prior_uptrend:
            triggers.append({
                "name": "Bearish Belt Hold",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 88,
                "description": "Opened at the extreme high and dumped with zero upper shadow; aggressive sellers in control."
            })

        # 2. Hammer (Small body at high, lower shadow >= 2x body, at bottom of downtrend)
        if lower_wick0 >= (2.0 * body0) and upper_wick0 <= (0.20 * range0) and is_prior_downtrend:
            triggers.append({
                "name": "Hammer Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "wick_rejected": round(l0, 2),
                "confidence": 90,
                "description": f"Long lower shadow rejected lower prices at {l0:.2f}; buyers stepping in strongly."
            })

        # 7. Inverted Hammer (Small body at low, long upper shadow >= 2x body, at bottom of downtrend)
        if upper_wick0 >= (2.0 * body0) and lower_wick0 <= (0.20 * range0) and is_prior_downtrend:
            triggers.append({
                "name": "Inverted Hammer Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 86,
                "description": "Buyers tested higher prices aggressively; reversal brewing from lower support."
            })

        # 26. Bearish Hanging Man (Small body at high, long lower shadow >= 2x body, at top of uptrend)
        if lower_wick0 >= (2.0 * body0) and upper_wick0 <= (0.20 * range0) and is_prior_uptrend:
            triggers.append({
                "name": "Bearish Hanging Man Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 86,
                "description": "Long lower shadow at the top of an advance signaling heavy distribution and buyer exhaustion."
            })

        # 29. Bearish Shooting Star (Small body at low, long upper shadow >= 2x body, at top of uptrend)
        if upper_wick0 >= (2.0 * body0) and lower_wick0 <= (0.20 * range0) and is_prior_uptrend:
            triggers.append({
                "name": "Bearish Shooting Star Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "wick_rejected": round(h0, 2),
                "confidence": 91,
                "description": f"Long upper shadow rejected higher prices at {h0:.2f}; sellers seized dominance."
            })

        # 8. Dragonfly Doji (Open ~= Close near high, long lower shadow >= 70% range)
        if (body0 / range0) <= 0.12 and (upper_wick0 / range0) <= 0.08 and (lower_wick0 / range0) >= 0.70:
            triggers.append({
                "name": "Dragonfly Doji Bullish Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 91,
                "description": f"Aggressive buyer defense; price tested down to {l0:.2f} but closed back at the high."
            })

        # Bearish Gravestone Doji (Open ~= Close near low, long upper shadow >= 70% range)
        if (body0 / range0) <= 0.12 and (lower_wick0 / range0) <= 0.08 and (upper_wick0 / range0) >= 0.70:
            triggers.append({
                "name": "Gravestone Doji Bearish Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 91,
                "description": f"Aggressive seller rejection; price spiked to {h0:.2f} but collapsed back to the low."
            })

        # Bullish Marubozu (Strong expansion, body >= 80% range)
        if c0_val > o0 and (body0 / range0) >= 0.80 and (upper_wick0 / range0) <= 0.10 and (lower_wick0 / range0) <= 0.10:
            triggers.append({
                "name": "Bullish Marubozu",
                "bias": "BULLISH",
                "type": "MOMENTUM_EXPANSION",
                "confidence": 92,
                "description": "Full bullish body with minimal wicks confirming dominant institutional buying drive."
            })

        # Bearish Marubozu (Strong dump, body >= 80% range)
        if c0_val < o0 and (body0 / range0) >= 0.80 and (upper_wick0 / range0) <= 0.10 and (lower_wick0 / range0) <= 0.10:
            triggers.append({
                "name": "Bearish Marubozu",
                "bias": "BEARISH",
                "type": "MOMENTUM_EXPANSION",
                "confidence": 92,
                "description": "Full bearish body with minimal wicks confirming dominant institutional selling dump."
            })

        # =========================================================================
        # 2. TWO-CANDLESTICK PATTERNS (Bullish & Bearish)
        # =========================================================================

        # 1. Bullish Engulfing (Small red followed by larger green engulfing body)
        if c1_val < o1 and c0_val > o0 and c0_val >= o1 and o0 <= (c1_val + body1 * 0.15):
            triggers.append({
                "name": "Bullish Engulfing Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 92,
                "description": f"Bullish body completely engulfed prior red candle ({o1:.2f} to {c1_val:.2f}); strong accumulation."
            })

        # 22. Bearish Engulfing (Small green followed by larger red engulfing body)
        if c1_val > o1 and c0_val < o0 and c0_val <= o1 and o0 >= (c1_val - body1 * 0.15):
            triggers.append({
                "name": "Bearish Engulfing Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 92,
                "description": f"Bearish body completely engulfed prior green candle ({o1:.2f} to {c1_val:.2f}); strong distribution."
            })

        # 4. Piercing Line Pattern (Red candle, then opens lower, closes > 50% into prior body)
        if c1_val < o1 and c0_val > o0 and o0 <= c1_val and c0_val >= (o1 + c1_val) / 2 and c0_val < o1:
            triggers.append({
                "name": "Piercing Line Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 89,
                "description": f"Bullish candle pierced {((c0_val - c1_val) / max(0.01, body1) * 100):.0f}% into prior bearish body."
            })

        # 38. Dark Cloud Cover Pattern (Green candle, opens higher, closes > 50% into prior body)
        if c1_val > o1 and c0_val < o0 and o0 >= c1_val and c0_val <= (o1 + c1_val) / 2 and c0_val > o1:
            triggers.append({
                "name": "Dark Cloud Cover Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 89,
                "description": f"Bearish candle covered {((c1_val - c0_val) / max(0.01, body1) * 100):.0f}% of prior bullish body."
            })

        # 5. Bullish Harami (Small green inside previous large red body)
        if c1_val < o1 and c0_val > o0 and o0 > c1_val and c0_val < o1 and body0 <= (0.60 * body1):
            triggers.append({
                "name": "Bullish Harami Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 84,
                "description": "Small bullish inside body shows selling momentum has completely halted."
            })

        # 30. Bearish Harami (Small red inside previous large green body)
        if c1_val > o1 and c0_val < o0 and o0 < c1_val and c0_val > o1 and body0 <= (0.60 * body1):
            triggers.append({
                "name": "Bearish Harami Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 84,
                "description": "Small bearish inside body shows buying momentum has completely halted."
            })

        # 12. Bullish Kicker Pattern (Long red followed by long green that opens higher than prior open and drives up)
        if c1_val < o1 and c0_val > o0 and o0 >= o1 and body0 >= (0.60 * range0):
            triggers.append({
                "name": "Bullish Kicker Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 95,
                "description": "Dramatic gap-up opposite momentum; violent institutional shift from bearish to bullish."
            })

        # 34. Bearish Kicker Pattern (Long green followed by long red that opens lower than prior open and dumps)
        if c1_val > o1 and c0_val < o0 and o0 <= o1 and body0 >= (0.60 * range0):
            triggers.append({
                "name": "Bearish Kicker Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 95,
                "description": "Dramatic gap-down opposite momentum; violent institutional shift from bullish to bearish."
            })

        # 13. Tweezer Bottom Pattern (Two consecutive candles with matching lows at support)
        if abs(l0 - l1) <= max(0.30, range0 * 0.05) and (lower_wick0 / range0) >= 0.25 and (lower_wick1 / range1) >= 0.25:
            triggers.append({
                "name": "Tweezer Bottom Pattern",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "support_level": round(min(l0, l1), 2),
                "confidence": 90,
                "description": f"Consecutive candles defended the identical support floor at {min(l0, l1):.2f}."
            })

        # 33. Bearish Tweezer Top Pattern (Two consecutive candles with matching highs at resistance)
        if abs(h0 - h1) <= max(0.30, range0 * 0.05) and (upper_wick0 / range0) >= 0.25 and (upper_wick1 / range1) >= 0.25:
            triggers.append({
                "name": "Bearish Tweezer Top Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "resistance_level": round(max(h0, h1), 2),
                "confidence": 90,
                "description": f"Consecutive candles rejected at the identical resistance ceiling at {max(h0, h1):.2f}."
            })

        # 17. Bullish Separating Lines (Downtrend/Pullback candle followed by bullish candle opening at same level)
        if c1_val < o1 and c0_val > o0 and abs(o0 - o1) <= max(0.35, range0 * 0.08) and c0_val > h1:
            triggers.append({
                "name": "Bullish Separating Lines Pattern",
                "bias": "BULLISH",
                "type": "CONTINUATION",
                "confidence": 86,
                "description": "Opened at the same level as previous candle and expanded upward; trend resumption."
            })

        # 21. Meeting Lines Pattern (Bullish: Bearish candle, then green opens lower but closes at exact same close)
        if c1_val < o1 and c0_val > o0 and o0 < c1_val and abs(c0_val - c1_val) <= max(0.30, range0 * 0.05):
            triggers.append({
                "name": "Meeting Lines Pattern (Bullish)",
                "bias": "BULLISH",
                "type": "REVERSAL",
                "confidence": 87,
                "description": f"Green candle rallied from lower open to meet previous close at {c1_val:.2f}; selling absorbed."
            })

        # 31. Bearish Doji Star (Long green candle followed by a Doji gapping higher)
        if c1_val > o1 and body1 >= (0.50 * range1) and (body0 / range0) <= 0.12 and l0 >= (c1_val - 0.20):
            triggers.append({
                "name": "Bearish Doji Star Pattern",
                "bias": "BEARISH",
                "type": "REVERSAL",
                "confidence": 87,
                "description": "Doji at the top of a rally signifies exhaustion of buyer conviction."
            })

        # =========================================================================
        # 3. THREE-CANDLESTICK PATTERNS (Bullish & Bearish)
        # =========================================================================
        if c2 is not None:
            o2, h2, l2, c2_val = float(c2['open']), float(c2['high']), float(c2['low']), float(c2['close'])
            range2 = max(0.01, h2 - l2)
            body2 = abs(c2_val - o2)

            # 3. Morning Star Pattern (Long red -> Star/Doji -> Long green closing > 50% into 1st candle)
            if c2_val < o2 and body2 >= (0.45 * range2) and body1 <= (0.45 * body2) and c0_val > o0 and c0_val >= (o2 + c2_val) / 2:
                triggers.append({
                    "name": "Morning Star Pattern",
                    "bias": "BULLISH",
                    "type": "REVERSAL",
                    "confidence": 95,
                    "description": "Institutional 3-candle reversal: Heavy dump, star deceleration, and explosive bullish breakout."
                })

            # 28. Bearish Evening Star Pattern (Long green -> Star/Doji -> Long red closing > 50% into 1st candle)
            if c2_val > o2 and body2 >= (0.45 * range2) and body1 <= (0.45 * body2) and c0_val < o0 and c0_val <= (o2 + c2_val) / 2:
                triggers.append({
                    "name": "Bearish Evening Star Pattern",
                    "bias": "BEARISH",
                    "type": "REVERSAL",
                    "confidence": 95,
                    "description": "Institutional 3-candle reversal: Heavy rally, star deceleration, and explosive bearish breakdown."
                })

            # 6. Three White Soldiers Pattern (Three consecutive long green candles making higher highs & higher closes)
            if c2_val > o2 and c1_val > o1 and c0_val > o0 and c0_val > c1_val > c2_val and body0 >= (0.50 * range0) and body1 >= (0.50 * range1) and body2 >= (0.50 * range2):
                triggers.append({
                    "name": "Three White Soldiers Pattern",
                    "bias": "BULLISH",
                    "type": "MOMENTUM_EXPANSION",
                    "confidence": 94,
                    "description": "Three consecutive advancing green candles confirming massive institutional trend flow."
                })

            # 24. Three Black Crows Pattern (Three consecutive long red candles making lower lows & lower closes)
            if c2_val < o2 and c1_val < o1 and c0_val < o0 and c0_val < c1_val < c2_val and body0 >= (0.50 * range0) and body1 >= (0.50 * range1) and body2 >= (0.50 * range2):
                triggers.append({
                    "name": "Three Black Crows Pattern",
                    "bias": "BEARISH",
                    "type": "MOMENTUM_EXPANSION",
                    "confidence": 94,
                    "description": "Three consecutive declining red candles confirming massive institutional distribution."
                })

            # 9. Bullish Abandoned Baby (Red candle -> Doji gapping below -> Green gapping above)
            if c2_val < o2 and (body1 / range1) <= 0.12 and h1 < l2 and l0 > h1 and c0_val > o0:
                triggers.append({
                    "name": "Bullish Abandoned Baby Pattern",
                    "bias": "BULLISH",
                    "type": "REVERSAL",
                    "confidence": 96,
                    "description": "Island Doji reversal; trapped short sellers forced to cover in a violent squeeze."
                })

            # 32. Bearish Abandoned Baby (Green candle -> Doji gapping above -> Red gapping below)
            if c2_val > o2 and (body1 / range1) <= 0.12 and l1 > h2 and h0 < l1 and c0_val < o0:
                triggers.append({
                    "name": "Bearish Abandoned Baby Pattern",
                    "bias": "BEARISH",
                    "type": "REVERSAL",
                    "confidence": 96,
                    "description": "Island Doji reversal; trapped buyers liquidated in an aggressive waterfall."
                })

            # 10. Three Inside Up Pattern (Harami confirmed by 3rd candle closing above 1st candle open)
            if c2_val < o2 and c1_val > o1 and o1 > c2_val and c1_val < o2 and c0_val > o0 and c0_val > o2:
                triggers.append({
                    "name": "Three Inside Up Pattern",
                    "bias": "BULLISH",
                    "type": "REVERSAL",
                    "confidence": 92,
                    "description": "Harami confirmed by strong breakout candle closing above mother bar high."
                })

            # 35. Bearish Three Inside Down Pattern (Harami confirmed by 3rd candle closing below 1st candle open)
            if c2_val > o2 and c1_val < o1 and o1 < c2_val and c1_val > o2 and c0_val < o0 and c0_val < o2:
                triggers.append({
                    "name": "Bearish Three Inside Down Pattern",
                    "bias": "BEARISH",
                    "type": "REVERSAL",
                    "confidence": 92,
                    "description": "Bearish Harami confirmed by breakdown candle closing below mother bar low."
                })

            # 11. Three Outside Up Pattern (Engulfing confirmed by 3rd green candle closing higher)
            if c2_val < o2 and c1_val > o1 and c1_val >= o2 and o1 <= c2_val and c0_val > o0 and c0_val > c1_val:
                triggers.append({
                    "name": "Three Outside Up Pattern",
                    "bias": "BULLISH",
                    "type": "REVERSAL",
                    "confidence": 93,
                    "description": "Bullish Engulfing confirmed by follow-through expansion candle."
                })

            # 36. Bearish Three Outside Down Pattern (Engulfing confirmed by 3rd red candle closing lower)
            if c2_val > o2 and c1_val < o1 and c1_val <= o2 and o1 >= c2_val and c0_val < o0 and c0_val < c1_val:
                triggers.append({
                    "name": "Bearish Three Outside Down Pattern",
                    "bias": "BEARISH",
                    "type": "REVERSAL",
                    "confidence": 93,
                    "description": "Bearish Engulfing confirmed by follow-through breakdown candle."
                })

            # 27. Upside Gap Two Crows Pattern (Green candle -> Small red gapping up -> Red closing below 2nd candle)
            if c2_val > o2 and c1_val < o1 and l1 > c2_val and c0_val < o0 and o0 > o1 and c0_val < c1_val and c0_val > o2:
                triggers.append({
                    "name": "Upside Gap Two Crows Pattern",
                    "bias": "BEARISH",
                    "type": "REVERSAL",
                    "confidence": 88,
                    "description": "Two consecutive red candles failing to hold an upside gap; bearish reversal in progress."
                })

        # =========================================================================
        # 4. FOUR & FIVE CANDLESTICK PATTERNS (Bullish & Bearish)
        # =========================================================================
        if c3 is not None:
            o3, h3, l3, c3_val = float(c3['open']), float(c3['high']), float(c3['low']), float(c3['close'])

            # 19. Three-Line Strike (Bullish: 3 rising green candles, then 1 large red that engulfs them)
            # Classic Japanese paradox pattern: Despite the 4th red candle, uptrend vigorously resumes!
            if c3_val > o3 and c2_val > o2 and c1_val > o1 and c1_val > c2_val > c3_val and c0_val < o0 and o0 >= c1_val and c0_val <= o3:
                triggers.append({
                    "name": "Three-Line Strike Pattern (Bullish)",
                    "bias": "BULLISH",
                    "type": "CONTINUATION",
                    "confidence": 91,
                    "description": "Three rising candles followed by strike bar wipeout; classic liquidity trap before uptrend resumes."
                })

            # 25. Bearish Three-Line Strike (3 falling red candles, then 1 large green that engulfs them)
            if c3_val < o3 and c2_val < o2 and c1_val < o1 and c1_val < c2_val < c3_val and c0_val > o0 and o0 <= c1_val and c0_val >= o3:
                triggers.append({
                    "name": "Bearish Three-Line Strike Pattern",
                    "bias": "BEARISH",
                    "type": "CONTINUATION",
                    "confidence": 91,
                    "description": "Three falling candles followed by strike bar rally; short-squeeze liquidity trap before downtrend resumes."
                })

            # 15. Concealing Baby Swallow (4 candles: 2 marubozu reds, gap down red, then high open red closing inside)
            if c3_val < o3 and c2_val < o2 and c1_val < o1 and c0_val < o0 and c0_val >= l1 and o0 > h1:
                triggers.append({
                    "name": "Concealing Baby Swallow Pattern",
                    "bias": "BULLISH",
                    "type": "REVERSAL",
                    "confidence": 90,
                    "description": "Extreme seller exhaustion; sellers fail to expand lower despite gap down."
                })

        if c4 is not None:
            o4, h4, l4, c4_val = float(c4['open']), float(c4['high']), float(c4['low']), float(c4['close'])

            # 14. Rising Three Methods / 16. Mat Hold (Large green, 3 small consolidating reds, then large green breakout)
            if c4_val > o4 and (c4_val - o4) >= (0.50 * (h4 - l4)):
                if c3_val < o3 and c2_val < o2 and c1_val < o1:
                    if max(h3, h2, h1) <= h4 and min(l3, l2, l1) >= l4:
                        if c0_val > o0 and c0_val > h4:
                            triggers.append({
                                "name": "Rising Three Methods / Mat Hold Pattern",
                                "bias": "BULLISH",
                                "type": "CONTINUATION",
                                "confidence": 95,
                                "description": "Three shallow pullback candles completely contained within initial thrust bar, followed by explosive new high breakout."
                            })

            # 37. Bearish Mat Hold / Falling Three Methods (Large red, 3 small consolidating greens, then large red breakdown)
            if c4_val < o4 and (o4 - c4_val) >= (0.50 * (h4 - l4)):
                if c3_val > o3 and c2_val > o2 and c1_val > o1:
                    if max(h3, h2, h1) <= h4 and min(l3, l2, l1) >= l4:
                        if c0_val < o0 and c0_val < l4:
                            triggers.append({
                                "name": "Falling Three Methods / Bearish Mat Hold Pattern",
                                "bias": "BEARISH",
                                "type": "CONTINUATION",
                                "confidence": 95,
                                "description": "Three shallow pullback candles completely contained within initial dump bar, followed by explosive new low breakdown."
                            })

            # 20. Ladder Bottom Pattern (Three consecutive long red candles, small 4th candle, then 5th strong green breaking out)
            if c4_val < o4 and c3_val < o3 and c2_val < o2 and c4_val > c3_val > c2_val:
                if abs(c1_val - o1) <= (0.40 * abs(c2_val - o2)):
                    if c0_val > o0 and c0_val > h1 and c0_val > o2:
                        triggers.append({
                            "name": "Ladder Bottom Pattern",
                            "bias": "BULLISH",
                            "type": "REVERSAL",
                            "confidence": 93,
                            "description": "Five-candle institutional reversal: Three heavy red bars, volatility pause, and explosive green confirmation."
                        })

        return triggers

    @classmethod
    def scan_full_timeframe_matrix(cls, timeframes_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Scans all timeframes (M5, M15, M30, H1, H4, D1) simultaneously,
        producing a complete hierarchical Multi-Timeframe Pattern Confluence Radar
        grounded in the FXNX Fractal Harmony Strategy, KentinoFX 3-Tier Hierarchy,
        and Tradeciety Top-Down Analysis:
        - Daily (D1): The Macro Compass (Auction Value: Discount vs Premium).
        - 4-Hour (H4): The Structural Bridge & Filter (Market Structure Shift MSS).
        - 1-Hour (H1) & 30-Min (M30): Intermediate Formations (Necklines, Flags & Channels).
        - 15-Min (M15): The Execution Trigger Window (ChoCH, FVG, High-Volume Boxes).
        - 5-Min (M5): Micro Sniper Precision Entry (Candlestick Confirmation & Tight S/L).
        """
        radar = {}
        bullish_votes = 0
        bearish_votes = 0
        total_tf_scanned = len(timeframes_dict)

        tf_order = ["D1", "H4", "H1", "M30", "M15", "M5"]

        role_map = {
            "D1": {"role_name": "THE MACRO COMPASS", "badge": "COMPASS", "desc": "Auction Value & Macro Trend"},
            "H4": {"role_name": "THE STRUCTURAL BRIDGE", "badge": "FILTER / BRIDGE", "desc": "MSS & Noise Filter"},
            "H1": {"role_name": "INTERMEDIATE STRUCTURE", "badge": "STRUCTURE", "desc": "Trend Channel & Necklines"},
            "M30": {"role_name": "INTERMEDIATE FORMATION", "badge": "INTERMEDIATE", "desc": "Consolidation Coils & Flags"},
            "M15": {"role_name": "EXECUTION TRIGGER", "badge": "TRIGGER", "desc": "ChoCH & FVG Windows"},
            "M5": {"role_name": "SNIPER PRECISION ENTRY", "badge": "SNIPER", "desc": "Micro Trigger & Tight S/L"}
        }

        d1_zone = "NEUTRAL"
        d1_mid = 0.0
        h4_mss = "IN_RANGE"
        p_m15_name = ""
        p_m5_name = ""
        live_price = 0.0

        for tf in tf_order:
            if tf not in timeframes_dict:
                continue
            df = timeframes_dict[tf]
            if df.empty:
                continue

            struct = cls.detect_market_structure(df)
            patterns = cls.detect_chart_patterns(df)
            triggers = cls.detect_candlestick_triggers(df)

            primary_pattern = patterns[0]["name"] if patterns else "Standard Trend Wave"
            pattern_bias = patterns[0]["bias"] if patterns else struct["bias"]
            pattern_status = patterns[0]["status"] if patterns else struct["structure"]

            if tf == "M15":
                p_m15_name = primary_pattern
                live_price = float(df['close'].iloc[-1])
            elif tf == "M5":
                p_m5_name = primary_pattern
                if live_price == 0.0:
                    live_price = float(df['close'].iloc[-1])

            # Specific Top-Down Institutional Metadata
            extra_meta = {}
            if tf == "D1" and len(df) >= 5:
                d1_high = float(df['high'].iloc[-20:].max())
                d1_low = float(df['low'].iloc[-20:].min())
                d1_mid = (d1_high + d1_low) / 2.0
                curr_c = float(df['close'].iloc[-1])
                d1_zone = "DISCOUNT" if curr_c < d1_mid else "PREMIUM"
                extra_meta = {
                    "auction_zone": d1_zone,
                    "equilibrium_price": round(d1_mid, 2),
                    "range_high": round(d1_high, 2),
                    "range_low": round(d1_low, 2),
                    "context_label": f"{d1_zone} Zone (Eq: ${d1_mid:,.2f})"
                }
            elif tf == "H4" and len(df) >= 10:
                h4_high = float(df['high'].iloc[-10:-1].max())
                h4_low = float(df['low'].iloc[-10:-1].min())
                curr_c = float(df['close'].iloc[-1])
                if curr_c > h4_high:
                    h4_mss = "BULLISH_MSS (Higher High)"
                elif curr_c < h4_low:
                    h4_mss = "BEARISH_MSS (Lower Low)"
                else:
                    h4_mss = "IN_RANGE (Consolidation)"
                extra_meta = {
                    "mss_status": h4_mss,
                    "swing_high": round(h4_high, 2),
                    "swing_low": round(h4_low, 2),
                    "context_label": h4_mss
                }

            if pattern_bias == "BULLISH":
                bullish_votes += 1
            elif pattern_bias == "BEARISH":
                bearish_votes += 1

            r_info = role_map.get(tf, {"role_name": tf, "badge": tf, "desc": "Analysis"})

            bias_num = 1.0 if pattern_bias == "BULLISH" else (-1.0 if pattern_bias == "BEARISH" else 0.0)
            radar[tf] = {
                "timeframe": tf,
                "role_name": r_info["role_name"],
                "role_badge": r_info["badge"],
                "role_desc": r_info["desc"],
                "structure": struct["structure"],
                "bias": pattern_bias,
                "bias_numeric": bias_num,
                "primary_pattern": primary_pattern,
                "status": pattern_status,
                "patterns_found": patterns,
                "candlestick_triggers": triggers,
                "last_swing_high": struct.get("last_swing_high", 0.0),
                "last_swing_low": struct.get("last_swing_low", 0.0),
                "institutional_meta": extra_meta
            }

        # Calculate Multi-Timeframe Harmony Score with Top-Down H4/D1-First Weighting
        # D1: 2.5, H4: 2.5, H1: 1.5, M30: 1.0, M15: 1.0, M5: 0.5 (Total = 9.0)
        tf_weights = {"D1": 2.5, "H4": 2.5, "H1": 1.5, "M30": 1.0, "M15": 1.0, "M5": 0.5}
        weighted_bull = sum(tf_weights.get(t, 1.0) for t, d in radar.items() if d.get("bias") == "BULLISH")
        weighted_bear = sum(tf_weights.get(t, 1.0) for t, d in radar.items() if d.get("bias") == "BEARISH")
        total_weight = sum(tf_weights.get(t, 1.0) for t in radar.keys()) or 1.0

        d1_b = radar.get("D1", {}).get("bias", "NEUTRAL")
        h4_b = radar.get("H4", {}).get("bias", "NEUTRAL")

        # Golden Rule: If D1 & H4 are Bearish, Harmony can NEVER be declared Bullish!
        if d1_b == "BEARISH" and h4_b == "BEARISH":
            harmony_bias = "BEARISH"
            harmony_score = round((weighted_bear / total_weight) * 100)
            harmony_desc = f"H4/D1 Confirmed Bearish Macro Harmony ({harmony_score}%)"
        elif d1_b == "BULLISH" and h4_b == "BULLISH":
            harmony_bias = "BULLISH"
            harmony_score = round((weighted_bull / total_weight) * 100)
            harmony_desc = f"H4/D1 Confirmed Bullish Macro Harmony ({harmony_score}%)"
        elif weighted_bull > weighted_bear and (d1_b != "BEARISH" and h4_b != "BEARISH"):
            harmony_bias = "BULLISH"
            harmony_score = round((weighted_bull / total_weight) * 100)
            harmony_desc = f"{bullish_votes}/{total_tf_scanned} Bullish Multi-TF Harmony ({harmony_score}%)"
        elif weighted_bear > weighted_bull and (d1_b != "BULLISH" and h4_b != "BULLISH"):
            harmony_bias = "BEARISH"
            harmony_score = round((weighted_bear / total_weight) * 100)
            harmony_desc = f"{bearish_votes}/{total_tf_scanned} Bearish Multi-TF Harmony ({harmony_score}%)"
        else:
            harmony_bias = "NEUTRAL"
            harmony_score = 50
            harmony_desc = "Neutral / Mixed Multi-TF Harmony (50%)"

        # Tradeciety Top-Down Strategy Classification
        if "Double Top" in p_m15_name or "Head & Shoulders" in p_m15_name:
            tradeciety_mode = "Tradeciety Strategy 2: HTF Resistance Hold -> M15 Reversal Geometry"
        elif "Double Bottom" in p_m15_name or "Inverse Head" in p_m15_name:
            tradeciety_mode = "Tradeciety Strategy 2: HTF Support Hold -> M15 Reversal Geometry"
        elif "Bull Flag" in p_m5_name or "Triangle" in p_m15_name:
            tradeciety_mode = "Tradeciety Strategy 1: HTF Trend Expansion -> Micro Flag Continuation"
        elif "Bear Flag" in p_m5_name:
            tradeciety_mode = "Tradeciety Strategy 1: HTF Bearish Expansion -> Micro Bear Flag Continuation"
        elif d1_mid > 0 and abs(live_price - d1_mid) > 50.0:
            tradeciety_mode = "Tradeciety Strategy 3: Macro Value Extension / Liquidity Trap"
        else:
            tradeciety_mode = "Tradeciety Strategy 4: Moving Average Trend Anchor -> Intraday Pullback"

        # Fractal Harmony Golden Rule
        h4_bias = radar.get("H4", {}).get("bias", "NEUTRAL")
        if (d1_zone == "DISCOUNT" or radar.get("D1", {}).get("bias") == "BULLISH") and h4_bias == "BULLISH":
            fractal_rule = "BULLISH_FRACTAL_HARMONY (D1 Discount/Bullish + H4 Bullish MSS)"
        elif (d1_zone == "PREMIUM" or radar.get("D1", {}).get("bias") == "BEARISH") and h4_bias == "BEARISH":
            fractal_rule = "BEARISH_FRACTAL_HARMONY (D1 Premium/Bearish + H4 Bearish MSS)"
        else:
            fractal_rule = "FRACTAL_CONFLICT_STAND_ASIDE (D1 Compass & H4 Bridge in Disagreement)"

        return {
            "harmony_bias": harmony_bias,
            "harmony_score": harmony_score,
            "harmony_pct": float(harmony_score),
            "harmony_description": harmony_desc,
            "bullish_count": bullish_votes,
            "bearish_count": bearish_votes,
            "total_timeframes": total_tf_scanned,
            "tradeciety_strategy_mode": tradeciety_mode,
            "fractal_harmony_verdict": fractal_rule,
            "timeframes": radar
        }
