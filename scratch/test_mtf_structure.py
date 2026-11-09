import MetaTrader5 as mt5

mt5.initialize()
sym = "XAUUSD.ecn" if mt5.symbol_info("XAUUSD.ecn") else "XAUUSD"

w1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_W1, 0, 75)
d1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 100)
h4 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H4, 0, 100)
h1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 100)
m30 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M30, 0, 200)
m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 250)
m5 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 280)
m1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)

price = mt5.symbol_info_tick(sym).bid

# W1
w1_closes = [float(c[4]) for c in w1]
w1_sma20 = sum(w1_closes[-20:]) / 20.0
w1_sma50 = sum(w1_closes[-50:]) / 50.0
w1_trend = "BULLISH" if w1_closes[-1] > w1_sma20 else "BEARISH"

# D1
d1_closes = [float(c[4]) for c in d1]
d1_highs = [float(c[2]) for c in d1]
d1_lows = [float(c[3]) for c in d1]
d1_sma20 = sum(d1_closes[-20:]) / 20.0
d1_sma50 = sum(d1_closes[-50:]) / 50.0
d1_trend = "BULLISH" if d1_closes[-1] > d1_sma20 else "BEARISH"
adr_20 = sum(d1_highs[i] - d1_lows[i] for i in range(-20, 0)) / 20.0

# H4
h4_highs = [float(c[2]) for c in h4]
h4_lows = [float(c[3]) for c in h4]
h4_closes = [float(c[4]) for c in h4]
h4_100_high = max(h4_highs)
h4_100_low = min(h4_lows)
h4_swing_high = max(h4_highs[-30:])
h4_swing_low = min(h4_lows[-30:])
h4_range_pct = (price - h4_100_low) / max(10.0, h4_100_high - h4_100_low)

# H1
h1_highs = [float(c[2]) for c in h1]
h1_lows = [float(c[3]) for c in h1]
session_high = max(h1_highs[-24:])
session_low = min(h1_lows[-24:])
range_pct = (price - session_low) / max(6.0, session_high - session_low)

# M30
m30_closes = [float(c[4]) for c in m30]
m30_highs = [float(c[2]) for c in m30]
m30_prior_high = max(m30_highs[-30:-5])
m30_mss_bullish = m30_closes[-1] > m30_prior_high

# M15
ssl_count = 0
deepest_ssl_low = 999999.0
for c in m15:
    rng = float(c[2]) - float(c[3])
    lw = min(float(c[1]), float(c[4])) - float(c[3])
    if lw >= 3.5 and rng > 0 and (lw / rng) >= 0.40:
        ssl_count += 1
        if float(c[3]) < deepest_ssl_low:
            deepest_ssl_low = float(c[3])

print(f"Spot Price: ${price:.2f}")
print(f"W1 (75 candles): Trend={w1_trend} | SMA20=${w1_sma20:.2f} | SMA50=${w1_sma50:.2f}")
print(f"D1 (100 candles): Trend={d1_trend} | SMA20=${d1_sma20:.2f} | ADR(20)={adr_20:.2f} pts")
print(f"H4 (100 candles): 100-bar Range=[${h4_100_low:.2f} - ${h4_100_high:.2f}] | Prominent Swing High Target=${h4_swing_high:.2f} | H4 Location={h4_range_pct*100:.1f}%")
print(f"H1 (100 candles): Active Session Range=[${session_low:.2f} - ${session_high:.2f}] | Daily Location={range_pct*100:.1f}%")
print(f"M30 (200 candles): Bullish Structure Break={m30_mss_bullish}")
print(f"M15 (250 candles): {ssl_count} Institutional Liquidity Sweeps detected | Deepest Sweep Low=${deepest_ssl_low:.2f}")

mt5.shutdown()
