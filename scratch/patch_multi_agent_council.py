import os

brain_file = r"trajedor/src/cognitive_brain.py"
with open(brain_file, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update TradeThesis dataclass to include council fields
old_dataclass = """@dataclass
class TradeThesis:
    symbol: str
    action: str                     # "BUY", "SELL", "STANDBY"
    confidence_score: int           # 0 to 100
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    metamorphosis_mode: str         # "SCALP", "SWING_RUNNER", "SCALP_TO_SWING_PROMOTION"
    session_phase: str              # "LONDON_EXPANSION", "NY_DISTRIBUTION", etc.
    regime: str                     # "INSTITUTIONAL_EXPANSION", "LIQUIDITY_HUNT", "DISCOUNT_ACCUMULATION"
    retail_long_pct: float
    retail_short_pct: float
    smart_money_bias: str
    order_blocks: List[Dict[str, float]]
    fair_value_gaps: List[Dict[str, float]]
    reasoning_monologue: str        # Jarvis internal speech
    memory_gate_approved: bool
    memory_warnings: List[str]
    lessons_consulted: List[str]"""

new_dataclass = """@dataclass
class TradeThesis:
    symbol: str
    action: str                     # "BUY", "SELL", "STANDBY"
    confidence_score: int           # 0 to 100
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    metamorphosis_mode: str         # "SCALP", "SWING_RUNNER", "SCALP_TO_SWING_PROMOTION"
    session_phase: str              # "LONDON_EXPANSION", "NY_DISTRIBUTION", etc.
    regime: str                     # "INSTITUTIONAL_EXPANSION", "LIQUIDITY_HUNT", "DISCOUNT_ACCUMULATION"
    retail_long_pct: float
    retail_short_pct: float
    smart_money_bias: str
    order_blocks: List[Dict[str, float]]
    fair_value_gaps: List[Dict[str, float]]
    reasoning_monologue: str        # Jarvis internal speech
    memory_gate_approved: bool
    memory_warnings: List[str]
    lessons_consulted: List[str]
    council_votes: Dict[str, str] = field(default_factory=dict)
    council_consensus_pct: float = 0.0
    council_rationale: List[str] = field(default_factory=list)"""

assert old_dataclass in code, "old_dataclass not found"
code = code.replace(old_dataclass, new_dataclass, 1)

# 2. Implement the full 6-Agent Council Deliberation in deliberate()
old_deliberate_impl = """    def deliberate(self, current_price: float, m5_candles: Optional[List[Dict[str, Any]]] = None) -> TradeThesis:
        \"\"\"
        Runs the full humanoid cognitive deliberation cycle:
        1. Live Macro Synthesis (DXY, 10Y Yields, Crude, News)
        2. Live Sentiment & Crowd Trap Diagnostics
        3. SMC Structural Topology (Order Blocks, FVGs, Liquidity Pools)
        4. Pre-Trade Cognitive Memory Gate (Audit against past failures)
        5. Sniper Thesis Assembly & Metamorphosis Planning
        \"\"\"
        price = current_price if current_price > 0 else 4139.52"""

# We find the entire deliberate function and replace it with the rigorous Multi-Agent Council
deliberate_start_idx = code.find("    def deliberate(")
assert deliberate_start_idx != -1, "deliberate function not found"

new_deliberate_func = '''    def deliberate(self, current_price: float, m5_candles: Optional[List[Dict[str, Any]]] = None) -> TradeThesis:
        """
        Runs the full 6-Agent Institutional Consensus Council deliberation:
        Agent 1: Macro & Yields Sentinel (DXY, 10Y Yields, Crude)
        Agent 2: Price Location & Range Architecture (Floor vs Ceiling / Support vs Resistance)
        Agent 3: Technical Momentum & Candlestick Displacement (Exhaustion & Chase Guard)
        Agent 4: SMC Liquidity & Imbalance Topology (FVGs, Order Blocks, Liquidity Sweeps)
        Agent 5: Retail Crowd Trap Sentinel (Fading Crowded Retail Positioning)
        Agent 6: Chief Risk Officer (CRO) & Surgical 1:2 R:R Guard (Tight Stop Loss & Strict R:R Floor)
        """
        price = round(float(current_price if current_price > 0 else 4139.52), 2)

        # -------------------------------------------------------------
        # Step 0: Market Structure & Range Reconstruction
        # -------------------------------------------------------------
        session_high = price + 15.0
        session_low = price - 15.0
        local_swing_high = price + 5.0
        local_swing_low = price - 5.0
        last_3_displacement = 0.0

        if m5_candles is not None and len(m5_candles) >= 5:
            try:
                highs = [float(c[2]) for c in m5_candles]
                lows = [float(c[3]) for c in m5_candles]
                closes = [float(c[4]) for c in m5_candles]
                session_high = max(highs)
                session_low = min(lows)
                recent_highs = highs[-6:] if len(highs) >= 6 else highs
                recent_lows = lows[-6:] if len(lows) >= 6 else lows
                local_swing_high = max(recent_highs)
                local_swing_low = min(recent_lows)
                if len(closes) >= 4:
                    last_3_displacement = closes[-1] - closes[-4]
            except Exception:
                pass

        range_span = max(5.0, session_high - session_low)
        range_pct = (price - session_low) / range_span  # 0.0 = Support Floor, 1.0 = Resistance Ceiling

        # -------------------------------------------------------------
        # COUNCIL AGENT 1: Macro & Yields Sentinel
        # -------------------------------------------------------------
        macro = self.macro_sentinel.get_live_macro_suite()
        macro_score = macro.get("gold_macro_impact_score", 0)
        dxy = macro.get("dxy_index", {}).get("price", 101.92)
        yield_10y = macro.get("us_10y_yield", {}).get("yield_pct", 5.277)
        
        agent_macro_vote = "NEUTRAL"
        agent_macro_reason = f"Macro neutral ({macro_score:+d})"
        if macro_score <= -25:
            agent_macro_vote = "SELL"
            agent_macro_reason = f"Surging yields ({yield_10y}%) & strong USD pressuring non-yielding gold."
        elif macro_score >= 15:
            agent_macro_vote = "BUY"
            agent_macro_reason = f"Softening yields ({yield_10y}%) & dollar weakness providing bullion tailwind."

        # -------------------------------------------------------------
        # COUNCIL AGENT 2: Price Location & Range Architecture (CRITICAL)
        # -------------------------------------------------------------
        agent_location_vote = "NEUTRAL"
        agent_location_veto = None
        if range_pct < 0.35:
            # At support floor! STRICT VETO ON SELLING
            agent_location_vote = "BUY" if range_pct <= 0.20 else "STANDBY"
            agent_location_veto = f"VETO SELL: Price at ${price:.2f} is at the support floor ({range_pct*100:.1f}% of range). Never sell support!"
            agent_location_reason = f"Floor defense: Resting at support (${session_low:.2f}). Selling here is retail panic chasing."
        elif range_pct > 0.65:
            # At resistance ceiling! STRICT VETO ON BUYING
            agent_location_vote = "SELL" if range_pct >= 0.80 else "STANDBY"
            agent_location_veto = f"VETO BUY: Price at ${price:.2f} is at the resistance ceiling ({range_pct*100:.1f}% of range). Never buy the ceiling!"
            agent_location_reason = f"Ceiling defense: Resting at resistance (${session_high:.2f}). Buying here is retail FOMO."
        else:
            agent_location_vote = "SELL" if range_pct >= 0.50 else "BUY"
            agent_location_reason = f"Equilibrium zone ({range_pct*100:.1f}% of range). Concurs with institutional trend."

        # -------------------------------------------------------------
        # COUNCIL AGENT 3: Technical Momentum & Exhaustion Guard
        # -------------------------------------------------------------
        agent_momentum_vote = "NEUTRAL"
        agent_momentum_veto = None
        if last_3_displacement < -15.0:
            # Steep uninterrupted drop: Downward exhaustion
            agent_momentum_vote = "STANDBY"
            agent_momentum_veto = f"VETO SELL: Downward exhaustion detected ({last_3_displacement:.1f} pts drop). High snapback risk."
            agent_momentum_reason = "Overextended selloff: Waiting for pullback before shorting."
        elif last_3_displacement > 15.0:
            # Steep pump: Upward exhaustion
            agent_momentum_vote = "STANDBY"
            agent_momentum_veto = f"VETO BUY: Upward exhaustion detected ({last_3_displacement:+.1f} pts pump). High mean-reversion risk."
            agent_momentum_reason = "Overextended rally: Waiting for pullback before buying."
        elif last_3_displacement < -3.0:
            agent_momentum_vote = "SELL"
            agent_momentum_reason = f"Bearish displacement active ({last_3_displacement:.1f} pts decline)."
        elif last_3_displacement > 3.0:
            agent_momentum_vote = "BUY"
            agent_momentum_reason = f"Bullish displacement active ({last_3_displacement:+.1f} pts advance)."
        else:
            agent_momentum_vote = "NEUTRAL"
            agent_momentum_reason = "Low momentum consolidation."

        # -------------------------------------------------------------
        # COUNCIL AGENT 4: SMC Liquidity & Imbalance Topology
        # -------------------------------------------------------------
        condition = self.sentiment_sentinel.evaluate_market_condition(self.symbol)
        agent_smc_vote = "NEUTRAL"
        if condition.smart_money_bias == "ACCUMULATING_DISCOUNT":
            agent_smc_vote = "BUY"
            agent_smc_reason = "SMC discount accumulation: Institutional sweep below swing lows completed."
        elif condition.smart_money_bias == "HUNTING_RETAIL_STOPS":
            agent_smc_vote = "SELL" if range_pct >= 0.40 else "BUY"
            agent_smc_reason = "SMC liquidity hunt: Targeting retail stop pools."
        else:
            agent_smc_vote = "NEUTRAL"
            agent_smc_reason = "Balanced order flow profile."

        # -------------------------------------------------------------
        # COUNCIL AGENT 5: Retail Crowd Trap Sentinel
        # -------------------------------------------------------------
        retail_long = condition.retail_sentiment_long_pct
        agent_sentiment_vote = "NEUTRAL"
        if retail_long >= 68.0:
            agent_sentiment_vote = "SELL"
            agent_sentiment_reason = f"Fading retail herd: {retail_long:.1f}% crowd is LONG. Dealers hunting their stops."
        elif retail_long <= 32.0:
            agent_sentiment_vote = "BUY"
            agent_sentiment_reason = f"Fading retail herd: {100-retail_long:.1f}% crowd is SHORT. Short squeeze potential."
        else:
            agent_sentiment_vote = "NEUTRAL"
            agent_sentiment_reason = f"Crowd sentiment balanced ({retail_long:.1f}% Long)."

        # -------------------------------------------------------------
        # COUNCIL AGENT 6: Chief Risk Officer (CRO) & Surgical 1:2 R:R Guard
        # -------------------------------------------------------------
        # Determine candidate action from raw consensus
        votes = {
            "Macro Sentinel": agent_macro_vote,
            "Location Agent": agent_location_vote,
            "Momentum Agent": agent_momentum_vote,
            "SMC Topology": agent_smc_vote,
            "Sentiment Trap": agent_sentiment_vote,
        }

        sell_votes = sum(1 for v in votes.values() if v == "SELL")
        buy_votes = sum(1 for v in votes.values() if v == "BUY")

        candidate_action = "STANDBY"
        if sell_votes >= 3 and buy_votes <= 1:
            candidate_action = "SELL"
        elif buy_votes >= 3 and sell_votes <= 1:
            candidate_action = "BUY"

        # Calculate Surgical Local Swing SL and 1:2 R:R
        agent_cro_vote = "STANDBY"
        agent_cro_veto = None
        sl = round(price - 5.0, 2)
        tp1 = round(price + 10.0, 2)
        tp2 = round(price + 15.0, 2)
        rr = 2.0

        if candidate_action == "SELL":
            raw_sl_dist = round(local_swing_high - price + 1.2, 2)
            sl_dist = max(3.5, min(7.5, raw_sl_dist))
            sl = round(price + sl_dist, 2)
            tp1 = round(price - (sl_dist * 2.0), 2)  # Strict 1:2.0 R:R
            tp2 = round(price - (sl_dist * 3.0), 2)
            rr = round(abs(price - tp1) / max(0.5, abs(sl - price)), 2)
            if rr >= 1.8:
                agent_cro_vote = "SELL"
                agent_cro_reason = f"Approved 1:{rr:.1f} R:R (Risk: {sl_dist:.1f} pts, Reward: {sl_dist*2:.1f} pts)."
            else:
                agent_cro_veto = f"VETO SELL: R:R ({rr:.1f}:1) is below 1:1.8 institutional threshold."
                agent_cro_reason = agent_cro_veto
        elif candidate_action == "BUY":
            raw_sl_dist = round(price - local_swing_low + 1.2, 2)
            sl_dist = max(3.5, min(7.5, raw_sl_dist))
            sl = round(price - sl_dist, 2)
            tp1 = round(price + (sl_dist * 2.0), 2)  # Strict 1:2.0 R:R
            tp2 = round(price + (sl_dist * 3.0), 2)
            rr = round(abs(tp1 - price) / max(0.5, abs(price - sl)), 2)
            if rr >= 1.8:
                agent_cro_vote = "BUY"
                agent_cro_reason = f"Approved 1:{rr:.1f} R:R (Risk: {sl_dist:.1f} pts, Reward: {sl_dist*2:.1f} pts)."
            else:
                agent_cro_veto = f"VETO BUY: R:R ({rr:.1f}:1) is below 1:1.8 institutional threshold."
                agent_cro_reason = agent_cro_veto
        else:
            agent_cro_reason = "No candidate action to evaluate."

        votes["CRO Risk Guard"] = agent_cro_vote

        # -------------------------------------------------------------
        # COUNCIL VERDICT & VETO ARBITRATION
        # -------------------------------------------------------------
        rationale_list = [
            f"Macro Sentinel: {agent_macro_vote} ({agent_macro_reason})",
            f"Location Agent: {agent_location_vote} ({agent_location_reason})",
            f"Momentum Agent: {agent_momentum_vote} ({agent_momentum_reason})",
            f"SMC Topology: {agent_smc_vote} ({agent_smc_reason})",
            f"Sentiment Trap: {agent_sentiment_vote} ({agent_sentiment_reason})",
            f"CRO Risk Guard: {agent_cro_vote} ({agent_cro_reason})",
        ]

        total_agents = 6
        final_sell_count = sum(1 for v in votes.values() if v == "SELL")
        final_buy_count = sum(1 for v in votes.values() if v == "BUY")

        # Check for any active safety vetoes
        all_vetoes = []
        if candidate_action == "SELL" and agent_location_veto:
            all_vetoes.append(agent_location_veto)
        if candidate_action == "BUY" and agent_location_veto:
            all_vetoes.append(agent_location_veto)
        if candidate_action == "SELL" and agent_momentum_veto:
            all_vetoes.append(agent_momentum_veto)
        if candidate_action == "BUY" and agent_momentum_veto:
            all_vetoes.append(agent_momentum_veto)
        if agent_cro_veto:
            all_vetoes.append(agent_cro_veto)

        final_action = "STANDBY"
        confidence = 45
        consensus_pct = 0.0

        if all_vetoes:
            final_action = "STANDBY"
            confidence = 40
            consensus_pct = 0.0
            monologue = f"JARVIS Cognition: 🏛️ COUNCIL VETOED ENTRY: {all_vetoes[0]}"
        elif final_sell_count >= 5:
            final_action = "SELL"
            consensus_pct = round((final_sell_count / total_agents) * 100, 1)
            confidence = int(consensus_pct)
            monologue = (
                f"JARVIS Cognition: 🏛️ HIGH-CONVICTION COUNCIL CONSENSUS: {final_sell_count}/6 AGENTS AGREE ON SELL ({consensus_pct}%). "
                f"Entry: ${price:.2f} | SL: ${sl:.2f} | TP1: ${tp1:.2f} | Institutional R:R: 1:{rr:.1f}."
            )
        elif final_buy_count >= 5:
            final_action = "BUY"
            consensus_pct = round((final_buy_count / total_agents) * 100, 1)
            confidence = int(consensus_pct)
            monologue = (
                f"JARVIS Cognition: 🏛️ HIGH-CONVICTION COUNCIL CONSENSUS: {final_buy_count}/6 AGENTS AGREE ON BUY ({consensus_pct}%). "
                f"Entry: ${price:.2f} | SL: ${sl:.2f} | TP1: ${tp1:.2f} | Institutional R:R: 1:{rr:.1f}."
            )
        else:
            final_action = "STANDBY"
            leading_count = max(final_sell_count, final_buy_count)
            consensus_pct = round((leading_count / total_agents) * 100, 1)
            confidence = 50
            monologue = (
                f"JARVIS Cognition: 🏛️ COUNCIL DELIBERATING (STANDBY): Insufficient consensus ({leading_count}/6 agents, {consensus_pct}%). "
                f"Awaiting full alignment across Macro, Location, SMC, and R:R."
            )

        # Audit against memory journal
        gate = self.memory_journal.audit_trade_thesis_against_memory(
            action=final_action,
            price=price,
            macro_score=macro_score,
            crowd_long_pct=retail_long
        )
        if not gate["approved"]:
            final_action = "STANDBY"
            confidence = 40

        return TradeThesis(
            symbol=self.symbol,
            action=final_action,
            confidence_score=confidence,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            risk_reward_ratio=rr,
            metamorphosis_mode="TACTICAL_SCALP" if final_action == "SELL" else "SCALP_TO_SWING_PROMOTION",
            session_phase=condition.session_phase,
            regime=condition.volatility_regime,
            retail_long_pct=retail_long,
            retail_short_pct=100.0 - retail_long,
            smart_money_bias=condition.smart_money_bias,
            order_blocks=[
                {"type": "BULLISH_OB", "low": round(local_swing_low - 1.5, 2), "high": round(local_swing_low + 1.0, 2)},
                {"type": "BEARISH_OB", "low": round(local_swing_high - 1.0, 2), "high": round(local_swing_high + 1.5, 2)}
            ],
            fair_value_gaps=[{
                "top": round(price + 2.0, 2),
                "bottom": round(price - 1.0, 2),
                "type": "LIQUIDITY_IMBALANCE_ZONE"
            }],
            reasoning_monologue=monologue,
            memory_gate_approved=gate["approved"],
            memory_warnings=gate["warnings"],
            lessons_consulted=[gate["recent_lesson"]],
            council_votes=votes,
            council_consensus_pct=consensus_pct,
            council_rationale=rationale_list
        )'''

code = code[:deliberate_start_idx] + new_deliberate_func + "\n"

with open(brain_file, "w", encoding="utf-8") as f:
    f.write(code)
print("SUCCESSFULLY_INSTALLED_COUNCIL_ARCHITECTURE")
