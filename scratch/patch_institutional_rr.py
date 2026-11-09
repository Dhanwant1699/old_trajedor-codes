import os

# 1. Patch cognitive_brain.py
brain_path = r"trajedor/src/cognitive_brain.py"
with open(brain_path, "r", encoding="utf-8") as f:
    brain_code = f.read()

target_deliberate = """        # 3. SMC Structural Zones
        bullish_ob_low = round(price - 6.5, 2)
        bullish_ob_high = round(price - 2.8, 2)
        bearish_ob_low = round(price + 14.5, 2)
        bearish_ob_high = round(price + 22.0, 2)

        fvg_imbalance = {
            "top": round(price - 1.2, 2),
            "bottom": round(price - 4.5, 2),
            "type": "BULLISH_DISPLACEMENT_FVG"
        }

        # 4. Form Initial Hypothesis
        tentative_action = "STANDBY"
        confidence = 50

        if macro_score >= 10:
            tentative_action = "BUY"
            confidence = 86
        elif macro_score <= -30:
            tentative_action = "SELL"
            confidence = 83
        else:
            # Neutral macro - follow SMC Liquidity Sweeps
            if condition.smart_money_bias in ["ACCUMULATING_DISCOUNT", "HUNTING_RETAIL_STOPS"]:
                tentative_action = "BUY"
                confidence = 79
            else:
                tentative_action = "BUY"
                confidence = 74

        # 5. Cognitive Memory Gate Audit
        gate = self.memory_journal.audit_trade_thesis_against_memory(
            action=tentative_action,
            price=price,
            macro_score=macro_score,
            crowd_long_pct=condition.retail_sentiment_long_pct
        )

        final_action = tentative_action
        if not gate["approved"]:
            final_action = "STANDBY"
            confidence = 45

        # 6. Target & SL Engineering
        if final_action == "BUY":
            entry = round(price, 2)
            sl = round(bullish_ob_low - 2.5, 2)
            tp1 = round(price + 11.5, 2)
            tp2 = round(price + 26.0, 2)
            regime = "DISCOUNT_ACCUMULATION"
            mode = "SCALP_TO_SWING_PROMOTION"
            monologue = (
                f"JARVIS Cognition: Price resting at ${price:.2f}. "
                f"Session: {condition.session_phase} with {condition.volatility_regime}. "
                f"Macro Score: {macro_score:+d} (DXY: {dxy}, US10Y: {yield_10y}%). "
                f"Retail Sentiment: {condition.retail_sentiment_long_pct}% Long. "
                f"Smart Money Posture: {condition.smart_money_bias}. "
                f"SMC Invalidation SL protected below H1 Order Block at ${sl}. "
                f"Initial TP1 at ${tp1}. If momentum breaks structure cleanly, promote to swing runner targeting ${tp2}."
            )
        elif final_action == "SELL":
            entry = round(price, 2)
            sl = round(bearish_ob_high + 2.5, 2)
            tp1 = round(price - 12.0, 2)
            tp2 = round(price - 24.0, 2)
            regime = "PREMIUM_DISTRIBUTION"
            mode = "TACTICAL_SCALP"
            monologue = (
                f"JARVIS Cognition: Elevated Treasury Yields ({yield_10y}%) exerting institutional selling pressure. "
                f"Bearish Order Block resistance at ${bearish_ob_low} - ${bearish_ob_high}. "
                f"Targeting sell-side liquidity at ${tp1} with strict early-cut defense."
            )
        else:
            entry = round(price, 2)
            sl = round(price - 6.0, 2)
            tp1 = round(price + 8.0, 2)
            tp2 = round(price + 16.0, 2)
            regime = "TACTICAL_STANDBY"
            mode = "STANDBY"
            warnings_str = " | ".join(gate["warnings"]) if gate["warnings"] else "Waiting for clean structural confirmation."
            monologue = (
                f"JARVIS Cognition: Cognitive Memory Gate held order in STANDBY. "
                f"Reason: {warnings_str} "
                f"Preserving capital until institutional liquidity sweep completes."
            )

        rr = round(abs(tp1 - entry) / max(0.5, abs(entry - sl)), 2)"""

repl_deliberate = """        # 3. Market Structure & Price Location (Premium vs Discount Analysis)
        session_high = price + 15.0
        session_low = price - 15.0
        local_swing_high = price + 5.0
        local_swing_low = price - 5.0

        if m5_candles and len(m5_candles) >= 5:
            try:
                highs = [float(c[2]) for c in m5_candles]
                lows = [float(c[3]) for c in m5_candles]
                session_high = max(highs)
                session_low = min(lows)
                recent_highs = highs[-6:] if len(highs) >= 6 else highs
                recent_lows = lows[-6:] if len(lows) >= 6 else lows
                local_swing_high = max(recent_highs)
                local_swing_low = min(recent_lows)
            except Exception:
                pass

        range_span = max(5.0, session_high - session_low)
        range_pct = (price - session_low) / range_span  # 0.0 = Floor/Support, 1.0 = Ceiling/Resistance

        bullish_ob_low = round(local_swing_low - 1.5, 2)
        bullish_ob_high = round(local_swing_low + 1.0, 2)
        bearish_ob_low = round(local_swing_high - 1.0, 2)
        bearish_ob_high = round(local_swing_high + 1.5, 2)

        fvg_imbalance = {
            "top": round(price + 2.0, 2) if range_pct < 0.5 else round(price - 1.0, 2),
            "bottom": round(price - 1.0, 2) if range_pct < 0.5 else round(price - 3.5, 2),
            "type": "LIQUIDITY_IMBALANCE_ZONE"
        }

        # 4. Form Initial Hypothesis with Strict Price Location Gate
        # RULE: NEVER SELL AT THE FLOOR / SUPPORT (range_pct < 0.35)
        # RULE: NEVER BUY AT THE CEILING / RESISTANCE (range_pct > 0.65)
        tentative_action = "STANDBY"
        confidence = 50

        if macro_score <= -30:
            if range_pct < 0.35:
                # Price is at the floor! Selling here is chasing into support
                tentative_action = "STANDBY"
                confidence = 45
            else:
                tentative_action = "SELL"
                confidence = 85
        elif macro_score >= 10:
            if range_pct > 0.65:
                # Price is at the ceiling! Buying here is chasing into resistance
                tentative_action = "STANDBY"
                confidence = 45
            else:
                tentative_action = "BUY"
                confidence = 86
        else:
            if condition.smart_money_bias in ["ACCUMULATING_DISCOUNT", "HUNTING_RETAIL_STOPS"] and range_pct <= 0.40:
                tentative_action = "BUY"
                confidence = 80
            elif range_pct >= 0.60:
                tentative_action = "SELL"
                confidence = 78
            else:
                tentative_action = "STANDBY"
                confidence = 50

        # 5. Cognitive Memory Gate Audit
        gate = self.memory_journal.audit_trade_thesis_against_memory(
            action=tentative_action,
            price=price,
            macro_score=macro_score,
            crowd_long_pct=condition.retail_sentiment_long_pct
        )

        final_action = tentative_action
        if not gate["approved"]:
            final_action = "STANDBY"
            confidence = 45

        # 6. Target & SL Engineering with Guaranteed 1:2.0 Institutional R:R
        if final_action == "BUY":
            entry = round(price, 2)
            raw_sl_dist = round(entry - local_swing_low + 1.2, 2)
            sl_dist = max(3.5, min(7.5, raw_sl_dist))
            sl = round(entry - sl_dist, 2)
            tp1 = round(entry + (sl_dist * 2.0), 2)  # Strict 1:2.0 R:R
            tp2 = round(entry + (sl_dist * 3.0), 2)  # 1:3.0 Runner
            regime = "DISCOUNT_ACCUMULATION"
            mode = "SCALP_TO_SWING_PROMOTION"
            monologue = (
                f"JARVIS Cognition: Price resting in Discount zone at ${price:.2f} ({range_pct*100:.1f}% of range). "
                f"Session: {condition.session_phase}. "
                f"SMC Structural Invalidation SL at ${sl:.2f} ({sl_dist:.1f} pts risk). "
                f"TP1 at ${tp1:.2f} ({sl_dist*2:.1f} pts target | R:R 1:2.0)."
            )
        elif final_action == "SELL":
            entry = round(price, 2)
            raw_sl_dist = round(local_swing_high - entry + 1.2, 2)
            sl_dist = max(3.5, min(7.5, raw_sl_dist))
            sl = round(entry + sl_dist, 2)
            tp1 = round(entry - (sl_dist * 2.0), 2)  # Strict 1:2.0 R:R
            tp2 = round(entry - (sl_dist * 3.0), 2)  # 1:3.0 Runner
            regime = "PREMIUM_DISTRIBUTION"
            mode = "TACTICAL_SCALP"
            monologue = (
                f"JARVIS Cognition: Price in Premium zone at ${price:.2f} ({range_pct*100:.1f}% of range). "
                f"Session: {condition.session_phase}. "
                f"SMC Resistance Invalidation SL at ${sl:.2f} ({sl_dist:.1f} pts risk). "
                f"TP1 at ${tp1:.2f} ({sl_dist*2:.1f} pts target | R:R 1:2.0)."
            )
        else:
            entry = round(price, 2)
            sl = round(price - 5.0, 2)
            tp1 = round(price + 10.0, 2)
            tp2 = round(price + 15.0, 2)
            regime = "TACTICAL_STANDBY"
            mode = "STANDBY"
            reason = "Price located at extreme floor/support, waiting for pullback" if range_pct < 0.35 and macro_score <= -30 else "Awaiting clean structural confirmation."
            monologue = f"JARVIS Cognition: Held order in STANDBY. {reason}"

        rr = round(abs(tp1 - entry) / max(0.5, abs(entry - sl)), 2)

        # 7. Mandatory Institutional R:R Floor Gate (Minimum 1 : 1.5)
        if final_action in ("BUY", "SELL") and rr < 1.5:
            final_action = "STANDBY"
            confidence = 40
            monologue = f"JARVIS Cognition: Trade VETOED by R:R Gate. Calculated R:R ({rr}:1) is below mandatory 1:1.5 floor."
"""

assert target_deliberate in brain_code, "target_deliberate not found in cognitive_brain.py"
brain_code = brain_code.replace(target_deliberate, repl_deliberate, 1)

with open(brain_path, "w", encoding="utf-8") as f:
    f.write(brain_code)
print("SUCCESSFULLY_PATCHED_COGNITIVE_BRAIN")

# 2. Patch jarvis_executive.py to fetch and pass live M5 candles to deliberate()
exec_path = r"trajedor/src/jarvis_executive.py"
with open(exec_path, "r", encoding="utf-8") as f:
    exec_code = f.read()

target_exec = """        # 2. Cognitive Deliberation
        thesis = self.brain.deliberate(current_price=price)"""

repl_exec = """        # 2. Extract Recent M5 Candle Structure for Surgical Range & R:R Analysis
        m5_rates = None
        try:
            import MetaTrader5 as mt5
            m5_rates = mt5.copy_rates_from_pos(self.settings.PRIMARY_SYMBOL, mt5.TIMEFRAME_M5, 0, 30)
            if m5_rates is None or len(m5_rates) == 0:
                m5_rates = mt5.copy_rates_from_pos("XAUUSD.ecn", mt5.TIMEFRAME_M5, 0, 30)
        except Exception:
            pass

        # Cognitive Deliberation with Full Candle Structure & 1:2 R:R Guard
        thesis = self.brain.deliberate(current_price=price, m5_candles=m5_rates)"""

assert target_exec in exec_code, "target_exec not found in jarvis_executive.py"
exec_code = exec_code.replace(target_exec, repl_exec, 1)

with open(exec_path, "w", encoding="utf-8") as f:
    f.write(exec_code)
print("SUCCESSFULLY_PATCHED_JARVIS_EXECUTIVE")
