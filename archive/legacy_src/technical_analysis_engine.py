"""
Trajedor Technical Analysis Engine (Pure Python Standard Library)
Zero external dependencies required.
Implements:
1. Indicators: EMA (20, 50, 200), RSI (14), ATR (14)
2. Smart Money Concepts: Fair Value Gaps (FVG)
3. Microstructure: Liquidity Sweeps (BSL/SSL Hunts) & Displacement
"""

import math


class TechnicalEngine:
    def __init__(self, candles):
        """
        :param candles: List of dicts with keys: ['open', 'high', 'low', 'close', 'time']
        """
        self.candles = candles

    # -------------------------------------------------------------
    # 1. Indicator Calculations
    # -------------------------------------------------------------
    def compute_ema(self, period=20):
        """Calculates Exponential Moving Average."""
        if len(self.candles) < period:
            return []

        multiplier = 2.0 / (period + 1.0)
        # Seed with SMA of first 'period' candles
        sma = sum(c["close"] for c in self.candles[:period]) / period
        ema_values = [None] * (period - 1) + [sma]

        for i in range(period, len(self.candles)):
            curr_close = self.candles[i]["close"]
            prev_ema = ema_values[-1]
            new_ema = (curr_close - prev_ema) * multiplier + prev_ema
            ema_values.append(new_ema)

        return ema_values

    def compute_atr(self, period=14):
        """Calculates Average True Range."""
        if len(self.candles) < period + 1:
            return []

        tr_values = []
        for i in range(1, len(self.candles)):
            curr = self.candles[i]
            prev_close = self.candles[i - 1]["close"]
            tr = max(
                curr["high"] - curr["low"],
                abs(curr["high"] - prev_close),
                abs(curr["low"] - prev_close),
            )
            tr_values.append(tr)

        # Initial SMA of TR
        first_atr = sum(tr_values[:period]) / period
        atr_values = [None] * period + [first_atr]

        for tr in tr_values[period:]:
            new_atr = (atr_values[-1] * (period - 1) + tr) / period
            atr_values.append(new_atr)

        return atr_values

    def compute_rsi(self, period=14):
        """Calculates Relative Strength Index (Wilder's RSI)."""
        if len(self.candles) < period + 1:
            return []

        gains = []
        losses = []
        for i in range(1, len(self.candles)):
            delta = self.candles[i]["close"] - self.candles[i - 1]["close"]
            gains.append(max(delta, 0.0))
            losses.append(abs(min(delta, 0.0)))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_values = [None] * period
        rs = avg_gain / (avg_loss + 1e-9)
        rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            rs = avg_gain / (avg_loss + 1e-9)
            rsi = 100.0 - (100.0 / (1.0 + rs))
            rsi_values.append(rsi)

        return rsi_values

    # -------------------------------------------------------------
    # 2. Institutional Fair Value Gaps (FVG)
    # -------------------------------------------------------------
    def detect_fair_value_gaps(self):
        """
        Detects 3-candle institutional imbalances:
        - Bullish FVG: Candle 1 High < Candle 3 Low
        - Bearish FVG: Candle 1 Low > Candle 3 High
        """
        fvgs = []
        for i in range(2, len(self.candles)):
            c1 = self.candles[i - 2]
            c2 = self.candles[i - 1]
            c3 = self.candles[i]

            # Bullish FVG
            if c3["low"] > c1["high"]:
                fvgs.append({
                    "candle_index": i - 1,
                    "type": "Bullish_FVG",
                    "top": round(c3["low"], 2),
                    "bottom": round(c1["high"], 2),
                    "midpoint": round((c3["low"] + c1["high"]) / 2.0, 2),
                    "time": c2.get("time", f"Bar-{i-1}"),
                })
            # Bearish FVG
            elif c3["high"] < c1["low"]:
                fvgs.append({
                    "candle_index": i - 1,
                    "type": "Bearish_FVG",
                    "top": round(c1["low"], 2),
                    "bottom": round(c3["high"], 2),
                    "midpoint": round((c1["low"] + c3["high"]) / 2.0, 2),
                    "time": c2.get("time", f"Bar-{i-1}"),
                })

        return fvgs

    # -------------------------------------------------------------
    # 3. Liquidity Sweeps (Stop Hunts)
    # -------------------------------------------------------------
    def detect_liquidity_sweep(self, lookback=20):
        """
        Detects when the latest candle pierced a key swing high/low with a wick
        but closed back inside the range (Liquidity grab / False breakout).
        """
        if len(self.candles) < lookback + 1:
            return None

        recent_range = self.candles[-lookback - 1 : -1]
        swing_high = max(c["high"] for c in recent_range)
        swing_low = min(c["low"] for c in recent_range)

        curr = self.candles[-1]

        # Buy-Side Liquidity (BSL) Sweep (Bearish rejection)
        if curr["high"] > swing_high and curr["close"] < swing_high:
            wick_size = curr["high"] - max(curr["open"], curr["close"])
            body_size = abs(curr["close"] - curr["open"])
            if wick_size > body_size:
                return {
                    "type": "BSL_SWEEP",
                    "bias": "Bearish",
                    "swept_level": round(swing_high, 2),
                    "rejection_wick": round(wick_size, 2),
                }

        # Sell-Side Liquidity (SSL) Sweep (Bullish rejection)
        if curr["low"] < swing_low and curr["close"] > swing_low:
            wick_size = min(curr["open"], curr["close"]) - curr["low"]
            body_size = abs(curr["close"] - curr["open"])
            if wick_size > body_size:
                return {
                    "type": "SSL_SWEEP",
                    "bias": "Bullish",
                    "swept_level": round(swing_low, 2),
                    "rejection_wick": round(wick_size, 2),
                }

        return None

    # -------------------------------------------------------------
    # 4. Candlestick Pattern Recognition
    # -------------------------------------------------------------
    def detect_candlestick_patterns(self):
        """
        Scans recent price action for high-probability candlestick formations:
        - Hammer / Shooting Star
        - Bullish / Bearish Engulfing
        - Morning / Evening Star
        - Three-Line Strike (#1 ranked pattern)
        """
        patterns = []
        n = len(self.candles)
        if n < 2:
            return patterns

        curr = self.candles[-1]
        prev = self.candles[-2]

        curr_body = abs(curr["close"] - curr["open"])
        curr_range = curr["high"] - curr["low"]
        is_curr_green = curr["close"] >= curr["open"]

        prev_body = abs(prev["close"] - prev["open"])
        is_prev_green = prev["close"] >= prev["open"]

        # A. Pin Bar (Hammer / Shooting Star)
        if curr_range > 0:
            upper_wick = curr["high"] - max(curr["open"], curr["close"])
            lower_wick = min(curr["open"], curr["close"]) - curr["low"]

            # Hammer (Bullish Rejection)
            if lower_wick >= 2.0 * curr_body and upper_wick <= 0.2 * curr_range:
                patterns.append({
                    "pattern": "Hammer",
                    "bias": "Bullish",
                    "candle_time": curr.get("time"),
                    "strength": "High"
                })

            # Shooting Star (Bearish Rejection)
            if upper_wick >= 2.0 * curr_body and lower_wick <= 0.2 * curr_range:
                patterns.append({
                    "pattern": "Shooting_Star",
                    "bias": "Bearish",
                    "candle_time": curr.get("time"),
                    "strength": "High"
                })

            # Inverted Hammer (Bullish Rejection at lows)
            if upper_wick >= 2.0 * curr_body and lower_wick <= 0.2 * curr_range and not is_prev_green:
                patterns.append({
                    "pattern": "Inverted_Hammer",
                    "bias": "Bullish",
                    "candle_time": curr.get("time"),
                    "strength": "Medium"
                })

        # B. Two-Candle Patterns (Engulfing, Piercing Line, Dark Cloud Cover)
        # Bullish Engulfing
        if not is_prev_green and is_curr_green:
            if curr["open"] <= prev["close"] and curr["close"] >= prev["open"] and curr_body > prev_body:
                patterns.append({
                    "pattern": "Bullish_Engulfing",
                    "bias": "Bullish",
                    "candle_time": curr.get("time"),
                    "strength": "High"
                })

        # Bearish Engulfing
        if is_prev_green and not is_curr_green:
            if curr["open"] >= prev["close"] and curr["close"] <= prev["open"] and curr_body > prev_body:
                patterns.append({
                    "pattern": "Bearish_Engulfing",
                    "bias": "Bearish",
                    "candle_time": curr.get("time"),
                    "strength": "High"
                })

        # Piercing Line (Bullish)
        if not is_prev_green and is_curr_green:
            midpoint = (prev["open"] + prev["close"]) / 2.0
            if curr["open"] < prev["low"] and curr["close"] > midpoint and curr["close"] < prev["open"]:
                patterns.append({
                    "pattern": "Piercing_Line",
                    "bias": "Bullish",
                    "candle_time": curr.get("time"),
                    "strength": "High"
                })

        # Dark Cloud Cover (Bearish)
        if is_prev_green and not is_curr_green:
            midpoint = (prev["open"] + prev["close"]) / 2.0
            if curr["open"] > prev["high"] and curr["close"] < midpoint and curr["close"] > prev["open"]:
                patterns.append({
                    "pattern": "Dark_Cloud_Cover",
                    "bias": "Bearish",
                    "candle_time": curr.get("time"),
                    "strength": "High"
                })

        # C. Three-Candle Patterns (Morning / Evening Star)
        if n >= 3:
            c1 = self.candles[-3]
            c2 = self.candles[-2]
            c3 = self.candles[-1]

            c1_body = abs(c1["close"] - c1["open"])
            c2_body = abs(c2["close"] - c2["open"])
            c3_body = abs(c3["close"] - c3["open"])

            # Morning Star: Red -> Small Doji/Star -> Green closing above 50% of c1
            if c1["close"] < c1["open"] and c2_body < (c1_body * 0.4) and c3["close"] > c3["open"]:
                if c3["close"] > (c1["open"] + c1["close"]) / 2.0:
                    patterns.append({
                        "pattern": "Morning_Star",
                        "bias": "Bullish",
                        "candle_time": c3.get("time"),
                        "strength": "Very_High"
                    })

            # Evening Star: Green -> Small Doji/Star -> Red closing below 50% of c1
            if c1["close"] > c1["open"] and c2_body < (c1_body * 0.4) and c3["close"] < c3["open"]:
                if c3["close"] < (c1["open"] + c1["close"]) / 2.0:
                    patterns.append({
                        "pattern": "Evening_Star",
                        "bias": "Bearish",
                        "candle_time": c3.get("time"),
                        "strength": "Very_High"
                    })

            # Three White Soldiers: 3 consecutive expanding green candles
            if (c1["close"] > c1["open"] and c2["close"] > c2["open"] and c3["close"] > c3["open"] and
                c3["close"] > c2["close"] > c1["close"]):
                patterns.append({
                    "pattern": "Three_White_Soldiers",
                    "bias": "Bullish",
                    "candle_time": c3.get("time"),
                    "strength": "High"
                })

            # Three Black Crows: 3 consecutive expanding red candles (~78% accuracy)
            if (c1["close"] < c1["open"] and c2["close"] < c2["open"] and c3["close"] < c3["open"] and
                c3["close"] < c2["close"] < c1["close"]):
                patterns.append({
                    "pattern": "Three_Black_Crows",
                    "bias": "Bearish",
                    "candle_time": c3.get("time"),
                    "win_rate_stat": "78% (Bulkowski #3)",
                    "strength": "Very_High"
                })

        # D. Four-Candle Patterns: Three-Line Strike (#1 Statistically Ranked: ~84% accuracy)
        if n >= 4:
            b1 = self.candles[-4]
            b2 = self.candles[-3]
            b3 = self.candles[-2]
            b4 = self.candles[-1]

            # Bullish Three-Line Strike: 3 consecutive descending red candles + 1 giant green candle engulfing all 3
            if (b1["close"] < b1["open"] and b2["close"] < b2["open"] and b3["close"] < b3["open"] and
                b2["close"] < b1["close"] and b3["close"] < b2["close"]):
                if b4["close"] > b4["open"] and b4["open"] <= b3["close"] and b4["close"] >= b1["open"]:
                    patterns.append({
                        "pattern": "Bullish_Three_Line_Strike",
                        "bias": "Bullish",
                        "candle_time": b4.get("time"),
                        "win_rate_stat": "84% (Bulkowski #1)",
                        "strength": "Maximum"
                    })

            # Bearish Three-Line Strike: 3 consecutive ascending green candles + 1 giant red candle engulfing all 3
            if (b1["close"] > b1["open"] and b2["close"] > b2["open"] and b3["close"] > b3["open"] and
                b2["close"] > b1["close"] and b3["close"] > b2["close"]):
                if b4["close"] < b4["open"] and b4["open"] >= b3["close"] and b4["close"] <= b1["open"]:
                    patterns.append({
                        "pattern": "Bearish_Three_Line_Strike",
                        "bias": "Bearish",
                        "candle_time": b4.get("time"),
                        "win_rate_stat": "65% (Bulkowski #2)",
                        "strength": "Maximum"
                    })

        return patterns



if __name__ == "__main__":
    print("Testing Trajedor Pure-Python Technical Engine...")

    # Build 30 synthetic gold candles
    sample_candles = []
    base_price = 2650.0

    for i in range(30):
        op = base_price + (i * 0.2)
        cl = op + (0.5 if i % 2 == 0 else -0.3)
        hi = max(op, cl) + 0.8
        lo = min(op, cl) - 0.7
        sample_candles.append({
            "open": op, "high": hi, "low": lo, "close": cl, "time": f"10:{i:02d}"
        })

    # Inject an engineered Bullish Fair Value Gap at bar 20
    sample_candles[18]["high"] = 2653.0
    sample_candles[19]["open"] = 2653.2
    sample_candles[19]["close"] = 2660.0  # Big green displacement
    sample_candles[19]["high"] = 2660.5
    sample_candles[19]["low"] = 2653.0
    sample_candles[20]["low"] = 2656.0    # Gap left between 2653.0 and 2656.0
    sample_candles[20]["high"] = 2662.0

    engine = TechnicalEngine(sample_candles)
    ema20 = engine.compute_ema(period=20)
    atr14 = engine.compute_atr(period=14)
    rsi14 = engine.compute_rsi(period=14)

    print(f"Latest Bar Close: ${sample_candles[-1]['close']:.2f}")
    print(f"Calculated 20 EMA: ${ema20[-1]:.2f}")
    print(f"Calculated 14 ATR: ${atr14[-1]:.2f}")
    print(f"Calculated 14 RSI: {rsi14[-1]:.1f}")

    fvgs = engine.detect_fair_value_gaps()
    print(f"\nFair Value Gaps Detected: {len(fvgs)}")
    for fvg in fvgs:
        print(f"-> [{fvg['type']}] Midpoint: ${fvg['midpoint']} (Range: ${fvg['bottom']} to ${fvg['top']})")

    # Inject an engineered Bullish Three-Line Strike at the end
    sample_candles.append({"open": 2656.0, "high": 2656.2, "low": 2653.0, "close": 2653.5, "time": "10:31"})
    sample_candles.append({"open": 2653.5, "high": 2653.8, "low": 2651.0, "close": 2651.2, "time": "10:32"})
    sample_candles.append({"open": 2651.2, "high": 2651.5, "low": 2649.0, "close": 2649.5, "time": "10:33"})
    # Candle 4: Giant engulfing candle closing above candle 1 open (2656.0)
    sample_candles.append({"open": 2649.0, "high": 2658.0, "low": 2648.8, "close": 2657.5, "time": "10:34"})

    patterns = engine.detect_candlestick_patterns()
    print(f"\nCandlestick Patterns Detected on Latest Bar: {len(patterns)}")
    for p in patterns:
        stat = p.get('win_rate_stat', 'N/A')
        print(f"-> [{p['pattern']}] Bias: {p['bias']} | Win Rate: {stat} | Strength: {p['strength']}")
