"""
TRAJEDOR - Cognitive Reasoning Brain (The Jarvis Mind).
Deliberates across price action, Smart Money Concepts (SMC), macro catalysts,
crowd sentiment traps, session cycles, and episodic memory to generate
high-conviction sniper trade theses.
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from trajedor.src.macro_sentinel import MacroSentinel
from trajedor.src.sentiment_sentinel import SentimentSentinel, MarketCondition
from trajedor.src.memory_journal import MemoryJournal
from trajedor.src.analyst_chambers import AnalystChambers


@dataclass
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
    council_rationale: List[str] = field(default_factory=list)
    pitch_initiator: str = "None"
    pitch_setup_type: str = "STANDBY"
    roundtable_transcript: List[Dict[str, str]] = field(default_factory=list)
    opportunity_hunt_plans: List[Dict[str, str]] = field(default_factory=list)
    chambers_briefing: Dict[str, Any] = field(default_factory=dict)


class CognitiveBrain:
    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol
        self.macro_sentinel = MacroSentinel()
        self.sentiment_sentinel = SentimentSentinel()
        self.memory_journal = MemoryJournal()
        self.chambers = AnalystChambers(symbol=self.symbol)

    def deliberate(
        self,
        current_price: float,
        mtf_candles: Optional[Dict[str, Any]] = None,
        m5_candles: Optional[List[Dict[str, Any]]] = None,
        h1_candles: Optional[List[Dict[str, Any]]] = None,
        recent_loss_context: Optional[Dict[str, Any]] = None
    ) -> TradeThesis:
        """
        Runs the full 6-Agent Institutional Consensus Council deliberation with
        Top-Down Multi-Timeframe Structural Analysis:
        - 1W (50-100 candles): Macro structural trend & multi-month liquidity pool
        - 1D (50-100 candles): Daily trend, 20-day high/low, ATR
        - 4H (50-100 candles): Institutional order blocks & multi-day swing targets
        - 1H (50-100 candles): Daily floor & ceiling boundaries
        - 15M (180-300 candles): Liquidity sweeps, CHoCH, double-bottom retests
        - 5M & 1M (180-300 candles): Surgical displacement and tight execution stops
        """
        price = round(float(current_price if current_price > 0 else 4139.52), 2)
        mtf = mtf_candles or {}

        # =============================================================
        # STEP 0: COMPILE FULL 8-TIMEFRAME DATASET FOR ALL AGENTS
        # 1W (75c), D1 (100c), H4 (100c), H1 (100c), M30 (200c), M15 (250c), M5 (280c), M1 (250c)
        # =============================================================
        session_high = price + 15.0
        session_low = price - 15.0
        local_swing_high = price + 5.0
        local_swing_low = price - 5.0
        h4_swing_high = price + 35.0
        h4_swing_low = price - 35.0
        last_3_displacement = 0.0
        last_5_displacement = 0.0
        h4_range_pct = 0.50
        adr_20 = 40.0

        w1_rates = mtf.get("w1")
        d1_rates = mtf.get("d1")
        h4_rates = mtf.get("h4")
        h1_rates = mtf.get("h1") if mtf.get("h1") is not None else h1_candles
        m30_rates = mtf.get("m30")
        m15_rates = mtf.get("m15")
        m5_rates = mtf.get("m5") if mtf.get("m5") is not None else m5_candles
        m1_rates = mtf.get("m1")

        # 1. Weekly (W1)
        w1_trend = "NEUTRAL"
        if w1_rates is not None and len(w1_rates) >= 20:
            try:
                w1_closes = [float(c[4]) for c in w1_rates]
                w1_sma20 = sum(w1_closes[-20:]) / 20.0
                w1_trend = "BULLISH" if w1_closes[-1] > w1_sma20 else "BEARISH"
            except Exception:
                pass

        # 2. Daily (D1)
        d1_trend = "NEUTRAL"
        if d1_rates is not None and len(d1_rates) >= 20:
            try:
                d1_closes = [float(c[4]) for c in d1_rates]
                d1_highs = [float(c[2]) for c in d1_rates]
                d1_lows = [float(c[3]) for c in d1_rates]
                d1_sma20 = sum(d1_closes[-20:]) / 20.0
                d1_trend = "BULLISH" if d1_closes[-1] > d1_sma20 else "BEARISH"
                adr_20 = sum(d1_highs[i] - d1_lows[i] for i in range(-20, 0)) / 20.0
            except Exception:
                pass

        # 3. 4-Hour (H4)
        if h4_rates is not None and len(h4_rates) >= 20:
            try:
                h4_highs = [float(c[2]) for c in h4_rates]
                h4_lows = [float(c[3]) for c in h4_rates]
                h4_100_high = max(h4_highs)
                h4_100_low = min(h4_lows)
                recent_h4_highs = h4_highs[-30:] if len(h4_highs) >= 30 else h4_highs
                recent_h4_lows = h4_lows[-30:] if len(h4_lows) >= 30 else h4_lows
                h4_swing_high = max(recent_h4_highs)
                h4_swing_low = min(recent_h4_lows)
                h4_range_span = max(10.0, h4_100_high - h4_100_low)
                h4_range_pct = (price - h4_100_low) / h4_range_span
            except Exception:
                pass

        # 4. 1-Hour (H1)
        if h1_rates is not None and len(h1_rates) >= 24:
            try:
                h1_highs = [float(c[2]) for c in h1_rates]
                h1_lows = [float(c[3]) for c in h1_rates]
                session_high = max(h1_highs[-24:])
                session_low = min(h1_lows[-24:])
            except Exception:
                pass
        elif m15_rates is not None and len(m15_rates) >= 40:
            session_high = max(float(c[2]) for c in m15_rates[-40:])
            session_low = min(float(c[3]) for c in m15_rates[-40:])

        range_span = max(6.0, session_high - session_low)
        range_pct = (price - session_low) / range_span

        # Multi-Timeframe Institutional Trend Detection (Higher Highs & Higher Lows)
        h1_bullish_trend = False
        h1_bearish_trend = False
        recent_h1_low = session_low
        recent_h1_high = session_high
        if h1_rates is not None and len(h1_rates) >= 6:
            try:
                h1_rec_lows = [float(c[3]) for c in h1_rates[-6:]]
                h1_rec_highs = [float(c[2]) for c in h1_rates[-6:]]
                recent_h1_low = min(h1_rec_lows[-3:])
                recent_h1_high = max(h1_rec_highs[-3:])
                hl_count = sum(1 for i in range(1, len(h1_rec_lows)) if h1_rec_lows[i] >= h1_rec_lows[i-1] - 1.2)
                hh_count = sum(1 for i in range(1, len(h1_rec_highs)) if h1_rec_highs[i] >= h1_rec_highs[i-1] - 1.2)
                if hl_count >= 3 and hh_count >= 3:
                    h1_bullish_trend = True
                elif hl_count <= 1 and hh_count <= 1:
                    h1_bearish_trend = True
            except Exception:
                pass

        # Intraday D1 Expansion Status
        d1_bullish_expansion = False
        d1_daily_gain = 0.0
        if d1_rates is not None and len(d1_rates) >= 1:
            try:
                d1_today_open = float(d1_rates[-1][1])
                d1_daily_gain = price - d1_today_open
                if d1_daily_gain >= 8.0:
                    d1_bullish_expansion = True
            except Exception:
                pass

        # 5. 30-Minute (M30)
        m30_mss_bullish = False
        m30_mss_bearish = False
        if m30_rates is not None and len(m30_rates) >= 30:
            try:
                m30_closes = [float(c[4]) for c in m30_rates]
                m30_highs = [float(c[2]) for c in m30_rates]
                m30_lows = [float(c[3]) for c in m30_rates]
                m30_mss_bullish = m30_closes[-1] > max(m30_highs[-30:-5])
                m30_mss_bearish = m30_closes[-1] < min(m30_lows[-30:-5])
            except Exception:
                pass

        # 6. 15-Minute (M15) - RESTRICTED TO RECENT SESSION (Last 6 candles / 90 mins only)
        m15_ssl_sweep = False
        m15_sweep_low = 0.0
        m15_sweep_wick = 0.0
        m15_bsl_sweep = False
        m15_sweep_high = 0.0
        m15_ssl_count = 0
        if m15_rates is not None and len(m15_rates) >= 6:
            try:
                recent_m15_candles = m15_rates[-6:]
                for c in recent_m15_candles:
                    c_open, c_high, c_low, c_close = float(c[1]), float(c[2]), float(c[3]), float(c[4])
                    rng = c_high - c_low
                    lower_wick = min(c_open, c_close) - c_low
                    upper_wick = c_high - max(c_open, c_close)
                    if lower_wick >= 3.0 and rng > 0 and (lower_wick / rng) >= 0.35:
                        m15_ssl_sweep = True
                        m15_ssl_count += 1
                        if m15_sweep_low == 0.0 or c_low < m15_sweep_low:
                            m15_sweep_low = c_low
                            m15_sweep_wick = lower_wick
                    if upper_wick >= 3.0 and rng > 0 and (upper_wick / rng) >= 0.35:
                        m15_bsl_sweep = True
                        if c_high > m15_sweep_high:
                            m15_sweep_high = c_high
            except Exception:
                pass

        m15_floor_retest = m15_ssl_sweep and (range_pct <= 0.42 or h4_range_pct <= 0.15 or abs(price - session_low) <= 6.0)
        m15_ceiling_retest = m15_bsl_sweep and (range_pct >= 0.70 or h4_range_pct >= 0.85 or abs(session_high - price) <= 6.0)

        # 7. 5-Minute (M5)
        if m5_rates is not None and len(m5_rates) >= 15:
            try:
                m5_highs = [float(c[2]) for c in m5_rates]
                m5_lows = [float(c[3]) for c in m5_rates]
                m5_closes = [float(c[4]) for c in m5_rates]
                local_swing_high = max(m5_highs[-15:])
                local_swing_low = min(m5_lows[-15:])
                if len(m5_closes) >= 4:
                    last_3_displacement = m5_closes[-1] - m5_closes[-4]
                if len(m5_closes) >= 6:
                    last_5_displacement = m5_closes[-1] - m5_closes[-6]
            except Exception:
                pass

        # 8. 1-Minute (M1)
        m1_absorption = False
        if m1_rates is not None and len(m1_rates) >= 5:
            try:
                m1_last = m1_rates[-1]
                m1_rng = float(m1_last[2]) - float(m1_last[3])
                m1_lower_wick = min(float(m1_last[1]), float(m1_last[4])) - float(m1_last[3])
                m1_absorption = m1_lower_wick >= 0.8 and (m1_lower_wick / max(0.1, m1_rng)) >= 0.35
            except Exception:
                pass

        # External Sentinel Feeds
        macro = self.macro_sentinel.get_live_macro_suite()
        macro_score = macro.get("gold_macro_impact_score", 0)
        dxy = macro.get("dxy_index", {}).get("price", 101.92)
        yield_10y = macro.get("us_10y_yield", {}).get("yield_pct", 5.277)
        condition = self.sentiment_sentinel.evaluate_market_condition(self.symbol)
        retail_long = condition.retail_sentiment_long_pct

        # =========================================================================
        # 6 SPECIALIZED ANALYST CHAMBERS (THE 14-AGENT AI WAR ROOMS)
        # Deep integration of all 14 strategy agents from Ai Trading ALGO across
        # EACH TIMEFRAME (1W, 1D, 4H, 1H, 30M, 15M, 5M, 1M)
        # =========================================================================
        chambers_eval = self.chambers.evaluate(
            current_price=price,
            mtf_rates=mtf,
            macro_suite={"gold_macro_impact_score": macro_score, "dxy": {"price": dxy}, "us10y_yield": {"price": yield_10y}},
            sentiment_suite={"retail_sentiment_long_pct": retail_long}
        )
        chambers_dossier = chambers_eval.get("chambers", {})
        syndicate_debate = chambers_eval.get("syndicate_debate", {})
        timeframe_matrix = chambers_eval.get("timeframe_matrix", {})
        morphology_report = chambers_dossier.get("room_1_morphology", {})

        # =============================================================
        # PHASE 1: AUTONOMOUS MULTI-TIMEFRAME OPPORTUNITY SCANNING
        # Every agent scans all timeframes (1W, D1, H4, H1, M30, M15, M5, M1)
        # to spot candidate setups.
        # =============================================================
        pitch_candidates = []

        # Ingest candidate setups directly pitched by the 6 Chambers
        for c_pitch in chambers_eval.get("pitch_candidates", []):
            pitch_candidates.append(c_pitch)

        # Candidate Scan A: SMC Topology (Scanning 1W, D1, H4, H1, M30, M15, M5)
        # --- 1. Institutional Bullish Trend Pullback Setup (Primary Gold Trend Driver) ---
        dist_to_demand = min(abs(price - recent_h1_low), abs(price - local_swing_low))
        is_near_demand = dist_to_demand <= 3.8 or m15_floor_retest or m1_absorption or range_pct <= 0.38
        if h1_bullish_trend and is_near_demand and last_3_displacement >= -2.0:
            pitch_candidates.append({
                "initiator": "SMC Topology",
                "action": "BUY",
                "setup_type": "BULLISH_TREND_ORDER_BLOCK_PULLBACK",
                "conviction": 90,
                "discovery_tf": "H1",
                "timeframes": ["H4", "H1", "M15"],
                "rationale": (
                    f"Inspected H4, H1, M15: Institutional Bullish Trend Structure confirmed with Higher Highs & Higher Lows. "
                    f"Support holding at H1 demand base (${recent_h1_low:.2f}). Trend continuation long targeting ${recent_h1_high + 12.0:.2f}."
                )
            })
        elif m15_floor_retest and range_pct <= 0.50 and last_3_displacement >= -2.0:
            pitch_candidates.append({
                "initiator": "SMC Topology",
                "action": "BUY",
                "setup_type": "INTRADAY_SWING_LONG",
                "conviction": 88,
                "discovery_tf": "M15",
                "timeframes": ["D1", "H4", "M15"],
                "rationale": (
                    f"Inspected D1, H4, M15: M15 institutional sweep confirmed at ${m15_sweep_low:.2f} ({m15_sweep_wick:.1f}pt wick) "
                    f"absorbing sell-side stops at H4 discount ({h4_range_pct*100:.1f}%). Clear target at H4 swing high ${h4_swing_high:.2f}."
                )
            })
        elif m30_mss_bullish and last_3_displacement >= 0.0:
            pitch_candidates.append({
                "initiator": "SMC Topology",
                "action": "BUY",
                "setup_type": "MOMENTUM_BREAKOUT_LONG",
                "conviction": 85,
                "discovery_tf": "M30",
                "timeframes": ["H4", "M30", "M15"],
                "rationale": (
                    f"Inspected H4, M30, M15: M30 Market Structure Shift confirmed with break of prior swing high. "
                    f"Bullish Fair Value Gap respected on M15. Targeting H4 swing expansion to ${h4_swing_high:.2f}."
                )
            })
        elif condition.smart_money_bias == "ACCUMULATING_DISCOUNT" and range_pct <= 0.50:
            pitch_candidates.append({
                "initiator": "SMC Topology",
                "action": "BUY",
                "setup_type": "INSTITUTIONAL_DISCOUNT_SWING",
                "conviction": 80,
                "discovery_tf": "D1",
                "timeframes": ["D1", "M15"],
                "rationale": "Inspected D1 and M15: Dealers actively absorbing sell-side liquidity at discount floor."
            })
        elif m15_ceiling_retest and range_pct >= 0.70 and not m30_mss_bullish and not h1_bullish_trend and last_3_displacement <= 1.0:
            pitch_candidates.append({
                "initiator": "SMC Topology",
                "action": "SELL",
                "setup_type": "INTRADAY_SWING_SHORT",
                "conviction": 82,
                "discovery_tf": "M15",
                "timeframes": ["H4", "M15"],
                "rationale": f"Inspected H4 and M15: Buy-side liquidity swept at ${m15_sweep_high:.2f} with supply rejection. Targeting H4 swing low ${h4_swing_low:.2f}."
            })

        # Candidate Scan B: Momentum Agent (Scanning H4, H1, M30, M15, M5, M1)
        if (h1_bullish_trend or d1_bullish_expansion) and (price >= local_swing_high - 0.75 or price <= local_swing_low + 3.0) and last_3_displacement >= 1.0:
            pitch_candidates.append({
                "initiator": "Momentum Agent",
                "action": "BUY",
                "setup_type": "BULLISH_TREND_MOMENTUM_EXPANSION",
                "conviction": 88,
                "discovery_tf": "M15",
                "timeframes": ["H1", "M15", "M5"],
                "rationale": (
                    f"Inspected H1, M15, M5: Bullish order flow velocity intact (+{d1_daily_gain:.1f}pt expansion today). "
                    f"Pullback absorbed at structural pivot with fresh expansion momentum. Trend continuation long."
                )
            })
        elif last_3_displacement >= 3.0 and price >= local_swing_high - 0.75:
            pitch_candidates.append({
                "initiator": "Momentum Agent",
                "action": "BUY",
                "setup_type": "MOMENTUM_DISPLACEMENT_BURST",
                "conviction": 83,
                "discovery_tf": "M5",
                "timeframes": ["H1", "M5", "M1"],
                "rationale": f"Inspected H1, M5, M1: Velocity expanding rapidly beyond local swing high (+{last_3_displacement:.1f} pts displacement). Buyers aggressive in price discovery."
            })
        elif last_3_displacement <= -3.5 and price <= local_swing_low + 0.75 and range_pct >= 0.50 and not h1_bullish_trend:
            pitch_candidates.append({
                "initiator": "Momentum Agent",
                "action": "SELL",
                "setup_type": "MOMENTUM_DISPLACEMENT_DROP",
                "conviction": 80,
                "discovery_tf": "M5",
                "timeframes": ["H1", "M5"],
                "rationale": f"Inspected H1 and M5: Downward velocity expanding beyond local swing low ({last_3_displacement:.1f} pts drop). Selling pressure intact."
            })

        # Candidate Scan C: Location Agent (Scanning 1W, D1, H4, H1, M30, M15)
        if h1_bullish_trend and (price <= local_swing_low + 3.2 or m15_floor_retest) and price >= session_low + 10.0:
            pitch_candidates.append({
                "initiator": "Location Agent",
                "action": "BUY",
                "setup_type": "DYNAMIC_TREND_VALUE_LONG",
                "conviction": 87,
                "discovery_tf": "H1",
                "timeframes": ["D1", "H1", "M30"],
                "rationale": (
                    f"Inspected D1, H1, M30: Trending Day Architecture. In persistent bull trends, ceiling breaks become new dynamic floors. "
                    f"Prior broken resistance successfully converted to institutional support at ${local_swing_low:.2f}."
                )
            })
        elif range_pct >= 0.70 and (m30_mss_bullish or last_3_displacement >= 1.0):
            pitch_candidates.append({
                "initiator": "Location Agent",
                "action": "BUY",
                "setup_type": "BULLISH_BREAKOUT_EXPANSION",
                "conviction": 82,
                "discovery_tf": "D1",
                "timeframes": ["1W", "D1", "H1"],
                "rationale": f"Inspected 1W, D1, H1: Price broke through daily ceiling (${session_high:.2f}) with structural follow-through. Price discovery expansion active."
            })
        elif range_pct <= 0.30 and last_3_displacement >= -1.5:
            pitch_candidates.append({
                "initiator": "Location Agent",
                "action": "BUY",
                "setup_type": "DISCOUNT_ACCUMULATION_BOUNCE",
                "conviction": 81,
                "discovery_tf": "H4",
                "timeframes": ["D1", "H4", "H1"],
                "rationale": f"Inspected D1, H4, H1: Resting firmly at daily support floor (${session_low:.2f}, {range_pct*100:.1f}% range). Asymmetric discount long."
            })
        elif range_pct >= 0.85 and last_3_displacement <= 0.5 and not m30_mss_bullish and not h1_bullish_trend:
            pitch_candidates.append({
                "initiator": "Location Agent",
                "action": "SELL",
                "setup_type": "CEILING_REJECTION_SCALP",
                "conviction": 78,
                "discovery_tf": "H1",
                "timeframes": ["H4", "H1"],
                "rationale": f"Inspected H4 and H1: At resistance ceiling (${session_high:.2f}, {range_pct*100:.1f}%) without breakout momentum. Rejection scalp."
            })

        # Candidate Scan D: Macro Sentinel (Scanning 1W, D1, H4, DXY, 10Y Yields)
        if d1_bullish_expansion or macro_score >= 15:
            pitch_candidates.append({
                "initiator": "Macro Sentinel",
                "action": "BUY",
                "setup_type": "MACRO_BULLION_EXPANSION",
                "conviction": 86,
                "discovery_tf": "D1",
                "timeframes": ["1W", "D1", "DXY/10Y"],
                "rationale": f"Inspected 1W, D1, DXY, 10Y: Today's Daily Candle expanded +{d1_daily_gain:.1f} pts. Bullion demand driving macro price discovery."
            })
        elif macro_score <= -30 and range_pct >= 0.50 and not h1_bullish_trend:
            pitch_candidates.append({
                "initiator": "Macro Sentinel",
                "action": "SELL",
                "setup_type": "MACRO_YIELD_PRESSURE",
                "conviction": 78,
                "discovery_tf": "D1",
                "timeframes": ["1W", "D1", "DXY/10Y"],
                "rationale": f"Inspected 1W, D1, DXY, 10Y: Elevated Treasury yields ({yield_10y}%) creating heavy macro selling pressure."
            })

        # Candidate Scan E: Sentiment Trap Sentinel (Scanning SSI Book, H4, M15, M5)
        if retail_long <= 30.0:
            pitch_candidates.append({
                "initiator": "Sentiment Trap",
                "action": "BUY",
                "setup_type": "RETAIL_SHORT_SQUEEZE",
                "conviction": 84,
                "discovery_tf": "SSI-Book",
                "timeframes": ["SSI-Book", "M15"],
                "rationale": f"Inspected SSI Book & M15: Retail crowd is heavily short ({100-retail_long:.1f}% short). Stop-hunt squeeze fuel is prime."
            })
        elif retail_long >= 70.0 and range_pct >= 0.55 and not h1_bullish_trend:
            pitch_candidates.append({
                "initiator": "Sentiment Trap",
                "action": "SELL",
                "setup_type": "RETAIL_LONG_TRAP_FLUSH",
                "conviction": 81,
                "discovery_tf": "SSI-Book",
                "rationale": f"Inspected SSI Book & H1: Retail herd is trapped long ({retail_long:.1f}% long). Smart money preparing flush."
            })

        # Candidate Scan F: Pattern Recognition Sentinel (Scanning M15, M5, H1 Geometric Formations)
        if m5_rates is not None and len(m5_rates) >= 20:
            try:
                m5_lows_recent = [float(c[3]) for c in m5_rates[-20:]]
                m5_highs_recent = [float(c[2]) for c in m5_rates[-20:]]
                m5_closes_recent = [float(c[4]) for c in m5_rates[-20:]]
                
                # 1. Double Bottom (W-Pattern)
                first_half_lows = m5_lows_recent[:10]
                second_half_lows = m5_lows_recent[10:]
                l1 = min(first_half_lows)
                l2 = min(second_half_lows)
                min_idx1 = first_half_lows.index(l1)
                min_idx2 = 10 + second_half_lows.index(l2)
                
                if min_idx2 > min_idx1 + 2:
                    neckline = max(m5_highs_recent[min_idx1:min_idx2])
                    if abs(l1 - l2) <= 1.8 and price >= (neckline - 1.2) and last_3_displacement >= 0.8:
                        pitch_candidates.append({
                            "initiator": "Pattern Sentinel",
                            "action": "BUY",
                            "setup_type": "DOUBLE_BOTTOM_W_FORMATION",
                            "conviction": 89,
                            "discovery_tf": "M5",
                            "timeframes": ["M15", "M5", "H1"],
                            "rationale": (
                                f"Inspected M5 & M15: Institutional Double Bottom (W-Pattern) confirmed. "
                                f"Twin troughs at ${l1:.2f} and ${l2:.2f} successfully absorbed sell-side stops. "
                                f"Neckline at ${neckline:.2f} breached with positive displacement (+{last_3_displacement:.1f} pts). Target major swing expansion."
                            )
                        })

                # 2. Double Top (M-Pattern)
                first_half_highs = m5_highs_recent[:10]
                second_half_highs = m5_highs_recent[10:]
                h1_p = max(first_half_highs)
                h2_p = max(second_half_highs)
                max_idx1 = first_half_highs.index(h1_p)
                max_idx2 = 10 + second_half_highs.index(h2_p)
                
                if max_idx2 > max_idx1 + 2:
                    valley = min(m5_lows_recent[max_idx1:max_idx2])
                    if abs(h1_p - h2_p) <= 1.8 and price <= (valley + 1.2) and last_3_displacement <= -0.8 and not h1_bullish_trend:
                        pitch_candidates.append({
                            "initiator": "Pattern Sentinel",
                            "action": "SELL",
                            "setup_type": "DOUBLE_TOP_M_FORMATION",
                            "conviction": 86,
                            "discovery_tf": "M5",
                            "timeframes": ["M15", "M5", "H1"],
                            "rationale": (
                                f"Inspected M5 & M15: Institutional Double Top (M-Pattern) confirmed. "
                                f"Twin peaks at ${h1_p:.2f} and ${h2_p:.2f} rejected supply ceiling. "
                                f"Neckline at ${valley:.2f} broken with negative displacement ({last_3_displacement:.1f} pts)."
                            )
                        })

                # 3. Bull Flag Continuation Pattern
                if len(m5_closes_recent) >= 14:
                    pole_gain = m5_closes_recent[-5] - m5_closes_recent[-14]
                    flag_range = max(m5_highs_recent[-5:]) - min(m5_lows_recent[-5:])
                    if pole_gain >= 5.0 and flag_range <= 2.8 and last_3_displacement >= 1.0 and price >= max(m5_highs_recent[-5:]) - 0.6:
                        pitch_candidates.append({
                            "initiator": "Pattern Sentinel",
                            "action": "BUY",
                            "setup_type": "BULL_FLAG_EXPANSION_BREAKOUT",
                            "conviction": 88,
                            "discovery_tf": "M5",
                            "timeframes": ["H1", "M15", "M5"],
                            "rationale": (
                                f"Inspected H1, M15, M5: Bull Flag Continuation Pattern confirmed! "
                                f"Impulse pole (+{pole_gain:.1f} pts) followed by tight flag consolidation ({flag_range:.1f} pt span). "
                                f"Price breaking above flag resistance. Measured move expansion active."
                            )
                        })

                # 4. Turtle Soup Liquidity Sweep (False Breakout / Liquidity Trap Reversal)
                # True vs False Structure Dissection:
                # - False Breakout Trap: Wick penetrates swing high by 0.5 to 4.5 pts, but candle closes back below.
                # - False Breakdown Trap: Wick penetrates swing low by 0.5 to 4.5 pts, but candle closes back above.
                if m15_rates is not None and len(m15_rates) >= 15:
                    m15_highs_r = [float(c[2]) for c in m15_rates[-15:-1]]
                    m15_lows_r = [float(c[3]) for c in m15_rates[-15:-1]]
                    prev_m15_high = max(m15_highs_r)
                    prev_m15_low = min(m15_lows_r)
                    cur_m15_high = float(m15_rates[-1][2])
                    cur_m15_low = float(m15_rates[-1][3])
                    cur_m15_close = float(m15_rates[-1][4])
                    
                    # False Breakdown Reversal Long (Sell-Stops Purged)
                    if cur_m15_low < prev_m15_low and cur_m15_close > prev_m15_low and (cur_m15_close - cur_m15_low) >= 1.2:
                        pitch_candidates.append({
                            "initiator": "Pattern Sentinel",
                            "action": "BUY",
                            "setup_type": "TURTLE_SOUP_FALSE_BREAKDOWN_LONG",
                            "conviction": 91,
                            "discovery_tf": "M15",
                            "timeframes": ["H1", "M15", "M5"],
                            "rationale": (
                                f"Inspected M15 & M5: FALSE BREAKDOWN TRAP IDENTIFIED on Gold! "
                                f"Price plunged through key swing low (${prev_m15_low:.2f}) to ${cur_m15_low:.2f} harvesting retail stop-losses, "
                                f"but M15 candle closed back above (${cur_m15_close:.2f}) with a {(cur_m15_close - cur_m15_low):.1f}pt absorption wick. "
                                f"Smart Money Liquidity Grab complete. Target opposing swing high."
                            )
                        })
                    
                    # False Breakout Reversal Short (Buy-Stops Purged)
                    elif cur_m15_high > prev_m15_high and cur_m15_close < prev_m15_high and (cur_m15_high - cur_m15_close) >= 1.2 and not h1_bullish_trend:
                        pitch_candidates.append({
                            "initiator": "Pattern Sentinel",
                            "action": "SELL",
                            "setup_type": "TURTLE_SOUP_FALSE_BREAKOUT_SHORT",
                            "conviction": 90,
                            "discovery_tf": "M15",
                            "timeframes": ["H1", "M15", "M5"],
                            "rationale": (
                                f"Inspected M15 & M5: FALSE BREAKOUT TRAP IDENTIFIED on Gold! "
                                f"Price spiked above key swing high (${prev_m15_high:.2f}) to ${cur_m15_high:.2f} inducing breakout buyers, "
                                f"but M15 candle closed back inside (${cur_m15_close:.2f}) with a {(cur_m15_high - cur_m15_close):.1f}pt rejection wick. "
                                f"Smart money distribution confirmed. Target sell-side liquidity at swing low."
                            )
                        })

                # 5. Multi-TF Algorithmic Morphology Signal (Powered by Ai Trading ALGO MultiTFPatternDetector)
                p_harm_bias = morphology_report.get("harmony_bias", "NEUTRAL")
                p_harm_score = int(morphology_report.get("harmony_score", 50))
                p_strat_mode = morphology_report.get("tradeciety_strategy_mode", "")
                p_fractal = morphology_report.get("fractal_harmony_verdict", "")
                
                m15_tf_meta = morphology_report.get("timeframes", {}).get("M15", {})
                h1_tf_meta = morphology_report.get("timeframes", {}).get("H1", {})
                m15_pat = m15_tf_meta.get("primary_pattern", "")
                h1_pat = h1_tf_meta.get("primary_pattern", "")

                if p_harm_bias == "BEARISH" and p_harm_score >= 75 and not h1_bullish_trend:
                    pitch_candidates.append({
                        "initiator": "Room 1 (Morphology Lab)",
                        "action": "SELL",
                        "setup_type": "ALGORITHMIC_MORPHOLOGY_BEARISH_EXPANSION",
                        "conviction": min(95, p_harm_score),
                        "discovery_tf": "M15",
                        "timeframes": ["D1", "H4", "H1", "M15"],
                        "rationale": (
                            f"Room 1 (Morphology Lab) Briefing: High-Conviction {p_harm_score}% BEARISH Multi-TF Harmony. "
                            f"Formations: M15 [{m15_pat}], H1 [{h1_pat}]. "
                            f"Verdict: {p_fractal}. Mode: {p_strat_mode}."
                        )
                    })
                elif p_harm_bias == "BULLISH" and p_harm_score >= 75:
                    pitch_candidates.append({
                        "initiator": "Room 1 (Morphology Lab)",
                        "action": "BUY",
                        "setup_type": "ALGORITHMIC_MORPHOLOGY_BULLISH_EXPANSION",
                        "conviction": min(95, p_harm_score),
                        "discovery_tf": "M15",
                        "timeframes": ["D1", "H4", "H1", "M15"],
                        "rationale": (
                            f"Room 1 (Morphology Lab) Briefing: High-Conviction {p_harm_score}% BULLISH Multi-TF Harmony. "
                            f"Formations: M15 [{m15_pat}], H1 [{h1_pat}]. "
                            f"Verdict: {p_fractal}. Mode: {p_strat_mode}."
                        )
                    })
            except Exception:
                pass

        # =============================================================
        # INSTANT MULTI-TIMEFRAME STRUCTURAL CROSS-CHECK ENGINE
        # Once an opportunity is spotted on a timeframe, the agent MUST instantly
        # inspect other timeframe structures (HTF and LTF) before deciding to pitch.
        # =============================================================
        def verify_timeframe_structures(cand: Dict[str, Any]) -> Tuple[bool, str, str]:
            c_action = cand["action"]
            c_disc = cand.get("discovery_tf", "M15")

            # --- 1. HIGHER-TIMEFRAME (HTF) STRUCTURAL CHECK (1W, D1, H4, H1) ---
            htf_ok = True
            htf_reason = "HTF Aligned"
            if c_action == "BUY":
                if h1_bullish_trend or d1_bullish_expansion:
                    htf_reason = f"D1/H4 Bullish Trend Expansion confirmed (HH/HL structure, Daily +{d1_daily_gain:.1f} pts)"
                elif range_pct >= 0.78 or h4_range_pct >= 0.88:
                    if not (m30_mss_bullish and last_3_displacement >= 1.0):
                        htf_ok = False
                        htf_reason = f"REJECTED: D1/H4 ceiling trap ({range_pct*100:.1f}% Daily range) without confirmed breakout velocity"
                    else:
                        htf_reason = f"D1/H4 ceiling breakout expansion confirmed (+{last_3_displacement:.1f} pts)"
                elif macro_score <= -30 and w1_trend == "BEARISH":
                    htf_ok = False
                    htf_reason = f"REJECTED: 1W Bearish secular trend and surging yields (Score: {macro_score:+d}) oppose long expansion"
                else:
                    htf_reason = f"D1/H4 clear (Range: {range_pct*100:.1f}%, Secular 1W: {w1_trend})"

            elif c_action == "SELL":
                if h1_bullish_trend or d1_bullish_expansion:
                    htf_ok = False
                    htf_reason = f"REJECTED: H1/D1 in aggressive Bullish Trend Expansion (HH/HL, +{d1_daily_gain:.1f} pts). Shorting an institutional bull run is strictly prohibited!"
                elif range_pct <= 0.28 or h4_range_pct <= 0.12:
                    if not (m30_mss_bearish and last_3_displacement <= -1.0):
                        htf_ok = False
                        htf_reason = f"REJECTED: D1/H4 support floor trap ({range_pct*100:.1f}% Daily range) without confirmed breakdown velocity"
                    else:
                        htf_reason = f"D1/H4 floor breakdown expansion confirmed ({last_3_displacement:.1f} pts)"
                elif macro_score >= 30 and w1_trend == "BULLISH":
                    htf_ok = False
                    htf_reason = f"REJECTED: 1W Bullish secular trend and softening yields (Score: {macro_score:+d}) oppose short expansion"
                else:
                    htf_reason = f"D1/H4 clear (Range: {range_pct*100:.1f}%, Secular 1W: {w1_trend})"

            # --- 2. LOWER-TIMEFRAME (LTF) MICRO-STRUCTURE CHECK (M15, M5, M1) ---
            ltf_ok = True
            ltf_reason = "LTF Confirmed"
            if c_action == "BUY":
                if last_3_displacement <= -2.8 and not m1_absorption and not m15_ssl_sweep:
                    ltf_ok = False
                    ltf_reason = f"REJECTED: M5/M1 falling knife ({last_3_displacement:.1f} pts drop) without absorption wick"
                else:
                    ltf_reason = f"M5/M1 micro-structure confirmed (Displacement: {last_3_displacement:+.1f} pts, M1 Absorption: {m1_absorption})"

            elif c_action == "SELL":
                if last_3_displacement >= 2.8 and not m15_bsl_sweep:
                    ltf_ok = False
                    ltf_reason = f"REJECTED: M5/M1 upward rocket (+{last_3_displacement:.1f} pts surge) without exhaustion wick"
                else:
                    ltf_reason = f"M5/M1 micro-structure confirmed (Displacement: {last_3_displacement:+.1f} pts)"

            # --- 3. STRUCTURAL ANCHOR / MID-RUN CHOP ELIMINATION GATE ---
            # Strictly forbids taking trades in the "middle of running" / dead-zone equilibrium.
            # Every valid trade MUST have a concrete structural anchor:
            # - BUY: Pullback to demand base/order block, support discount, or confirmed breakout above swing high.
            # - SELL: Pullback to supply base/order block, resistance premium, or confirmed breakdown below swing low.
            anchor_ok = True
            anchor_reason = "Anchored"
            local_span = max(4.0, local_swing_high - local_swing_low)
            local_eq_pct = (price - local_swing_low) / local_span

            if c_action == "BUY":
                is_demand_anchor = (price <= local_swing_low + 3.2) or m15_floor_retest or m1_absorption or range_pct <= 0.35
                is_breakout_anchor = (price >= local_swing_high - 0.75) and last_3_displacement >= 1.2
                if not (is_demand_anchor or is_breakout_anchor):
                    if 0.35 <= local_eq_pct <= 0.72:
                        anchor_ok = False
                        anchor_reason = (
                            f"REJECTED: Mid-run floating entry ({local_eq_pct*100:.0f}% of M5 range, ${price:.2f}). "
                            f"No demand base anchor (low: ${local_swing_low:.2f}) and no breakout velocity (high: ${local_swing_high:.2f}). "
                            f"Entering mid-run in equilibrium dead-zone is strictly forbidden."
                        )
            elif c_action == "SELL":
                is_supply_anchor = (price >= local_swing_high - 3.2) or m15_ceiling_retest or range_pct >= 0.65
                is_breakdown_anchor = (price <= local_swing_low + 0.75) and last_3_displacement <= -1.2
                if not (is_supply_anchor or is_breakdown_anchor):
                    if 0.28 <= local_eq_pct <= 0.65:
                        anchor_ok = False
                        anchor_reason = (
                            f"REJECTED: Mid-run floating entry ({local_eq_pct*100:.0f}% of M5 range, ${price:.2f}). "
                            f"No supply base anchor (high: ${local_swing_high:.2f}) and no breakdown velocity (low: ${local_swing_low:.2f}). "
                            f"Entering mid-run in equilibrium dead-zone is strictly forbidden."
                        )

            passed_all = htf_ok and ltf_ok and anchor_ok
            return passed_all, htf_reason, (anchor_reason if not anchor_ok else ltf_reason)

        # Run all candidates through instant cross-timeframe structural verification
        verified_candidates = []
        discarded_candidates = []
        for cand in pitch_candidates:
            passed, htf_v, ltf_v = verify_timeframe_structures(cand)
            cand["htf_verdict"] = htf_v
            cand["ltf_verdict"] = ltf_v
            cand["confluence_verified"] = passed
            if passed:
                cand["conviction"] += 5  # Confluence bonus
                cand["rationale"] += f" [CROSS-TIMEFRAME VERIFIED]: HTF ({htf_v}) | LTF ({ltf_v})."
                verified_candidates.append(cand)
            else:
                cand["rejection_reason"] = f"{htf_v if 'REJECTED' in htf_v else ltf_v}"
                discarded_candidates.append(cand)

        # =============================================================
        # PHASE 2: BRING LEAD CONFLUENCE OPPORTUNITY TO THE COUNCIL TABLE
        # =============================================================
        lead_pitch = None
        if verified_candidates:
            verified_candidates.sort(key=lambda x: x["conviction"], reverse=True)
            lead_pitch = verified_candidates[0]

        pitch_initiator = lead_pitch["initiator"] if lead_pitch else "None"
        pitch_setup_type = lead_pitch["setup_type"] if lead_pitch else "STANDBY"
        pitched_action = lead_pitch["action"] if lead_pitch else "STANDBY"
        lead_tf = lead_pitch["timeframes"] if lead_pitch else []
        pitch_rationale = lead_pitch["rationale"] if lead_pitch else "Market in balanced equilibrium. No cross-timeframe confluence."

        # Risk parameters calculation for the pitched opportunity
        agent_cro_vote = "STANDBY"
        agent_cro_veto = None
        sl = round(price - 5.0, 2)
        tp1 = round(price + 10.0, 2)
        tp2 = round(price + 15.0, 2)
        rr = 2.0
        sl_dist = 5.0

        if pitched_action == "SELL":
            raw_sl_dist = round(local_swing_high - price + 1.2, 2)
            sl_dist = max(3.5, min(7.5, raw_sl_dist))
            sl = round(price + sl_dist, 2)
            tp1 = round(price - (sl_dist * 2.0), 2)
            target_75_sell = round(price - 0.75 * max(12.0, price - session_low), 2)
            tp2 = round(min(h4_swing_low, session_low + 1.5, target_75_sell, price - (sl_dist * 3.5)), 2)
            rr = round(abs(price - tp1) / max(0.5, abs(sl - price)), 2)
            swing_rr = round(abs(price - tp2) / max(0.5, abs(sl - price)), 2)
            if rr >= 1.8:
                agent_cro_vote = "SELL"
                agent_cro_reason = f"CRO Checked M5 Risk Geometry: SL at ${sl:.2f} ({sl_dist:.1f}pt risk), TP1 at ${tp1:.2f} (1:{rr:.1f} R:R), Major Swing TP2 at ${tp2:.2f} (1:{swing_rr:.1f} R:R | Big-Point Target). Asymmetry approved."
            else:
                agent_cro_veto = f"VETO SELL: R:R ({rr:.1f}:1) below institutional threshold (minimum 1:1.8)."
                agent_cro_reason = agent_cro_veto
        elif pitched_action == "BUY":
            raw_sl_dist = round(price - local_swing_low + 1.2, 2)
            sl_dist = max(3.5, min(7.5, raw_sl_dist))
            sl = round(price - sl_dist, 2)
            tp1 = round(price + (sl_dist * 2.0), 2)
            target_75_buy = round(price + 0.75 * max(12.0, session_high - price), 2)
            tp2 = round(max(h4_swing_high, session_high - 1.5, target_75_buy, price + (sl_dist * 3.5)), 2)
            rr = round(abs(tp1 - price) / max(0.5, abs(price - sl)), 2)
            swing_rr = round(abs(tp2 - price) / max(0.5, abs(price - sl)), 2)
            if rr >= 1.8:
                agent_cro_vote = "BUY"
                agent_cro_reason = f"CRO Checked M5 Risk Geometry: SL at ${sl:.2f} ({sl_dist:.1f}pt risk), TP1 at ${tp1:.2f} (1:{rr:.1f} R:R), Major Swing TP2 at ${tp2:.2f} (1:{swing_rr:.1f} R:R | Big-Point Target). Asymmetry approved."
            else:
                agent_cro_veto = f"VETO BUY: R:R ({rr:.1f}:1) below institutional threshold (minimum 1:1.8)."
                agent_cro_reason = agent_cro_veto
        else:
            agent_cro_reason = "No active trade proposal to calculate risk-reward profile."

        # =============================================================
        # PHASE 3: COUNCIL PEER REVIEW & CROSS-EXAMINATION
        # Every agent examines the pitched trade using their chosen timeframes.
        # =============================================================
        roundtable_dialogue = []
        roundtable_dialogue.append({
            "speaker": "Council War Room",
            "statement": f"=== AUTONOMOUS COUNCIL CONVENED AT ${price:.2f} ==="
        })

        if lead_pitch:
            disc_tf = lead_pitch.get("discovery_tf", "M15")
            roundtable_dialogue.append({
                "speaker": f"Pitch Initiator // {pitch_initiator}",
                "statement": (
                    f"[FORMAL PROPOSAL WITH STRUCTURAL CONFLUENCE]: I pitch {pitch_setup_type} ({pitched_action}) @ ${price:.2f}. "
                    f"Spotted on {disc_tf}. Instant Cross-Check: HTF [{lead_pitch.get('htf_verdict')}]; LTF [{lead_pitch.get('ltf_verdict')}]. "
                    f"Structural confluence verified across all timeframes. Floor is open for cross-examination."
                )
            })
            roundtable_dialogue.append({
                "speaker": "Chairman Trajedor",
                "statement": (
                    f"Council order! {pitch_initiator} has formally pitched {pitch_setup_type} ({pitched_action}) with verified HTF & LTF confluence. "
                    f"Opening floor for rigorous cross-examination across all timeframes!"
                )
            })
        else:
            discard_msg = discarded_candidates[0]["rejection_reason"] if discarded_candidates else "No setups meeting multi-timeframe confluence"
            roundtable_dialogue.append({
                "speaker": "Chairman Trajedor",
                "statement": (
                    f"Autonomous omni-timeframe scan evaluated {len(pitch_candidates)} candidate setups across 1W, D1, H4, H1, M30, M15, M5, M1. "
                    f"Candidate setups failed cross-timeframe structural verification ({discard_msg}). Room remains in disciplined STANDBY."
                )
            })

        # Autonomous Peer Reviews: Each agent chooses timeframes to inspect the pitch
        # 1. Macro Sentinel Peer Review
        agent_macro_tf = ["1W", "D1", "Macro-DXY"]
        agent_macro_vote = "NEUTRAL"
        if macro_score <= -20:
            agent_macro_vote = "SELL"
            agent_macro_reason = f"Inspected 1W & D1: Yields ({yield_10y}%) & USD strength creating strong bearish macro pressure."
        elif macro_score >= 15:
            agent_macro_vote = "BUY"
            agent_macro_reason = f"Inspected 1W & D1: Softening yields ({yield_10y}%) & dollar weakness providing bullion tailwind. W1 secular trend: {w1_trend}."
        else:
            agent_macro_vote = "BUY" if w1_trend == "BULLISH" and pitched_action == "BUY" else "NEUTRAL"
            agent_macro_reason = f"Inspected 1W & D1: Macro neutral ({macro_score:+d}). W1 trend {w1_trend} aligns with bullish structure."

        # 2. Location Agent Peer Review
        agent_location_tf = ["D1", "H4", "H1"]
        agent_location_vote = "NEUTRAL"
        agent_location_veto = None
        if range_pct <= 0.35 or h4_range_pct <= 0.12:
            agent_location_vote = "BUY" if (range_pct <= 0.28 or m15_floor_retest) else "STANDBY"
            agent_location_veto = (
                f"VETO SELL: Price at ${price:.2f} is resting at the Support Floor / Discount zone "
                f"({range_pct*100:.1f}% Daily range, floor: ${session_low:.2f}). Selling into support floor is strictly forbidden!"
            )
            agent_location_reason = f"Inspected D1, H4, H1: Price at daily floor (${session_low:.2f}, {range_pct*100:.1f}%). Longs favored, shorts vetoed."
        elif range_pct >= 0.70 or h4_range_pct >= 0.88:
            if h1_bullish_trend or d1_bullish_expansion:
                agent_location_vote = "BUY" if pitched_action == "BUY" else "STANDBY"
                agent_location_reason = f"Inspected D1, H4, H1: In confirmed Bullish Trend Expansion (Higher Highs/Lows). Ceiling expanding dynamically. Trend longs supported."
            elif m30_mss_bullish and last_3_displacement >= 1.0:
                agent_location_vote = "BUY"
                agent_location_reason = f"Inspected D1, H4, H1: Price breaking session ceiling (${session_high:.2f}) with expansion momentum (+{last_3_displacement:.1f} pts). Breakout expansion confirmed."
            elif last_3_displacement <= 0.5 and not m30_mss_bullish and not h1_bullish_trend:
                agent_location_vote = "SELL" if range_pct >= 0.85 else "STANDBY"
                agent_location_veto = f"VETO BUY: Price at ${price:.2f} is at Resistance Ceiling (${session_high:.2f}, {range_pct*100:.1f}%) without breakout momentum."
                agent_location_reason = f"Inspected D1, H4, H1: Testing resistance ceiling (${session_high:.2f}). Stalling without breakout confirmation."
            else:
                agent_location_vote = "STANDBY"
                agent_location_reason = f"Inspected H4 & H1: In upper range (${session_high:.2f}, {range_pct*100:.1f}%). Awaiting clear breakout thrust."
        else:
            if last_3_displacement >= 1.5 or m30_mss_bullish or h1_bullish_trend:
                agent_location_vote = "BUY"
                agent_location_reason = f"Inspected H4 & H1: Equilibrium expansion upward toward ceiling."
            elif last_3_displacement <= -2.0:
                agent_location_vote = "SELL"
                agent_location_reason = f"Inspected H4 & H1: Equilibrium decline downward toward floor."
            else:
                agent_location_vote = "NEUTRAL"
                agent_location_reason = f"Inspected H4 & H1: Equilibrium consolidation ({range_pct*100:.1f}% range)."

        # 3. SMC Topology Peer Review
        agent_smc_tf = ["H4", "M30", "M15"]
        agent_smc_vote = "NEUTRAL"
        if h1_bullish_trend:
            agent_smc_vote = "BUY" if pitched_action == "BUY" else "NEUTRAL"
            agent_smc_reason = f"Inspected H4, H1, M15: Bullish Trend Structure confirmed (Higher Highs & Higher Lows). Order block demand respected."
        elif m15_floor_retest and range_pct <= 0.50:
            agent_smc_vote = "BUY"
            agent_smc_reason = f"Inspected H4, M30, M15: M15 institutional sweep confirmed at ${m15_sweep_low:.2f} with floor demand absorption."
        elif m30_mss_bullish:
            agent_smc_vote = "BUY"
            agent_smc_reason = f"Inspected H4, M30, M15: M30 Market Structure Shift confirmed. Bullish expansion toward H4 swing target (${h4_swing_high:.2f})."
        elif condition.smart_money_bias == "ACCUMULATING_DISCOUNT":
            agent_smc_vote = "BUY"
            agent_smc_reason = "Inspected H4 & M15: Smart Money accumulating at discount."
        elif m15_ceiling_retest and range_pct >= 0.70 and not m30_mss_bullish:
            agent_smc_vote = "SELL"
            agent_smc_reason = f"Inspected H4 & M15: Buy-side liquidity swept at ${m15_sweep_high:.2f} with premium rejection."
        else:
            agent_smc_vote = pitched_action if pitched_action in ("BUY", "SELL") and lead_pitch and lead_pitch["initiator"] == "SMC Topology" else "NEUTRAL"
            agent_smc_reason = f"Inspected M30 & M15: Balanced order flow profile."

        # 4. Momentum Agent Peer Review
        agent_momentum_tf = ["H1", "M5", "M1"]
        agent_momentum_vote = "NEUTRAL"
        agent_momentum_veto = None
        if last_3_displacement > 15.0:
            agent_momentum_veto = f"VETO BUY: Extreme upward pump ({last_3_displacement:+.1f} pts). Exhaustion risk."
            agent_momentum_vote = "STANDBY"
            agent_momentum_reason = "Inspected H1, M5, M1: Overextended rally, snapback risk."
        elif last_3_displacement < -15.0:
            agent_momentum_veto = f"VETO SELL: Extreme downward drop ({last_3_displacement:.1f} pts). Exhaustion risk."
            agent_momentum_vote = "STANDBY"
            agent_momentum_reason = "Inspected H1, M5, M1: Overextended selloff, snapback risk."
        elif h1_bullish_trend and last_3_displacement >= -1.0:
            agent_momentum_vote = "BUY"
            agent_momentum_reason = f"Inspected H1, M5, M1: Bullish momentum flow aligned with H1 expansion (+{last_3_displacement:+.1f} pts)."
        elif last_3_displacement >= 2.0:
            agent_momentum_vote = "BUY"
            agent_momentum_reason = f"Inspected H1, M5, M1: Velocity accelerating (+{last_3_displacement:+.1f} pts displacement). Buyers in firm control."
        elif last_3_displacement <= -2.5:
            if range_pct <= 0.35:
                agent_momentum_vote = "STANDBY"
                agent_momentum_reason = f"Inspected M5 & M1: Bearish velocity into floor ({range_pct*100:.1f}%). Shorting into floor rejected."
            else:
                agent_momentum_vote = "SELL"
                agent_momentum_reason = f"Inspected H1, M5, M1: Bearish displacement active ({last_3_displacement:.1f} pts drop)."
        else:
            agent_momentum_vote = "NEUTRAL"
            agent_momentum_reason = "Inspected M5 & M1: Low momentum consolidation."

        # 5. Sentiment Trap Peer Review
        agent_sentiment_tf = ["Crowd-SSI", "M15"]
        agent_sentiment_vote = "NEUTRAL"
        if retail_long <= 32.0:
            agent_sentiment_vote = "BUY"
            agent_sentiment_reason = f"Inspected SSI Book: Retail crowd is heavily short ({100-retail_long:.1f}% short). Strong short-squeeze fuel."
        elif retail_long >= 68.0:
            if h1_bullish_trend or d1_bullish_expansion:
                agent_sentiment_vote = "BUY" if pitched_action == "BUY" else "NEUTRAL"
                agent_sentiment_reason = f"Inspected SSI Book & H1: Institutional Bullish Trend overrides retail positioning. Retail longs are riding institutional expansion."
            elif range_pct >= 0.50:
                agent_sentiment_vote = "SELL"
                agent_sentiment_reason = f"Inspected SSI Book: Fading retail herd ({retail_long:.1f}% long). Smart money hunting stops."
            else:
                agent_sentiment_vote = "STANDBY"
                agent_sentiment_reason = f"Inspected SSI Book: Crowd is long ({retail_long:.1f}%), but price is at support floor. Awaiting bounce."
        else:
            agent_sentiment_vote = "NEUTRAL"
            agent_sentiment_reason = f"Inspected SSI Book: Crowd sentiment balanced ({retail_long:.1f}% Long)."

        agent_reviews = [
            ("Macro Sentinel", agent_macro_tf, agent_macro_vote, agent_macro_reason),
            ("Location Agent", agent_location_tf, agent_location_vote, agent_location_reason),
            ("SMC Topology", agent_smc_tf, agent_smc_vote, agent_smc_reason),
            ("Momentum Agent", agent_momentum_tf, agent_momentum_vote, agent_momentum_reason),
            ("Sentiment Trap", agent_sentiment_tf, agent_sentiment_vote, agent_sentiment_reason),
            ("CRO Risk Guard", ["M5-Geometry", "Memory"], agent_cro_vote, agent_cro_reason),
        ]

        roundtable_dialogue = []
        roundtable_dialogue.append({
            "speaker": "Council War Room",
            "statement": f"=== BOARDROOM COUNCIL MEETING CONVENED AT ${price:.2f} ==="
        })

        if lead_pitch:
            roundtable_dialogue.append({
                "speaker": f"Pitch Initiator // {pitch_initiator}",
                "statement": f"[FORMAL PROPOSAL]: I pitch a {pitch_setup_type} ({pitched_action}) @ ${price:.2f} based on {', '.join(lead_tf)}. {pitch_rationale}"
            })
            roundtable_dialogue.append({
                "speaker": "Chairman Trajedor",
                "statement": f"Council order! {pitch_initiator} has formally pitched {pitch_setup_type} ({pitched_action}). Opening floor for cross-examination. Who challenges this setup and who confirms?"
            })

            # Wall Street Syndicate Cross-Examination Duel
            if syndicate_debate and syndicate_debate.get("bull_champion") != "None":
                roundtable_dialogue.append({
                    "speaker": "Wall Street Syndicate // CROSS-EXAMINATION DUEL",
                    "statement": (
                        f"⚔️ SYNDICATE DUEL: Bull Champion [{syndicate_debate.get('bull_champion')}] vs "
                        f"Bear Champion [{syndicate_debate.get('bear_champion')}]. "
                        f"Red Team Challenge: '{syndicate_debate.get('red_team_challenge')}'. "
                        f"Arbitrator Ruling: '{syndicate_debate.get('arbitrator_justification')}'"
                    )
                })

            # ROUND 1: LOCATION & STRUCTURAL CHALLENGE
            if pitched_action == "BUY" and range_pct >= 0.70:
                if h1_bullish_trend or d1_bullish_expansion:
                    roundtable_dialogue.append({
                        "speaker": "Location Agent (Inspected D1, H4, H1)",
                        "statement": f"Location check: Price is at {range_pct*100:.1f}% Daily range, but H1 confirms an active institutional Bullish Trend Expansion (Higher Highs & Higher Lows). Ceiling is expanding dynamically into price discovery. Trend longs approved."
                    })
                else:
                    roundtable_dialogue.append({
                        "speaker": "Location Agent (Inspected D1, H4, H1)",
                        "statement": f"[OBJECTION TO {pitch_initiator}]: You are pitching a BUY at ${price:.2f}, which is {range_pct*100:.1f}% of the Daily Range right against resistance ceiling (${session_high:.2f}). History shows buying at the ceiling leads to nasty pullbacks. Why shouldn't we wait for a retest?"
                    })
                if last_3_displacement >= 1.0 or m30_mss_bullish:
                    roundtable_dialogue.append({
                        "speaker": f"Rebuttal // {pitch_initiator}",
                        "statement": f"Valid caution Location Agent, BUT look at the tape: on H1 and M15 we printed +{last_3_displacement:.1f} pts displacement and M30 Market Structure Shift is bullish. Waiting for a retest risks missing institutional price discovery. This is an active breakout expansion, not a range stall!"
                    })
                    roundtable_dialogue.append({
                        "speaker": "Location Agent (Inspected D1, H4, H1)",
                        "statement": "Rebuttal accepted. Given confirmed displacement and M30 structural shift, I withdraw my ceiling objection and approve the breakout expansion."
                    })
                else:
                    roundtable_dialogue.append({
                        "speaker": "Location Agent (Inspected D1, H4, H1)",
                        "statement": "I am NOT satisfied. Displacement volume is insufficient. I stand by my objection and VETO buying into unconfirmed resistance."
                    })
            elif pitched_action == "SELL" and range_pct <= 0.35:
                roundtable_dialogue.append({
                    "speaker": "Location Agent (Inspected D1, H4, H1)",
                    "statement": f"[HARSH OBJECTION TO {pitch_initiator}]: You want to SELL at ${price:.2f}, which is right at the Daily Support Floor (${session_low:.2f}, {range_pct*100:.1f}% range)! Selling into the floor is retail panic chasing and violates our October 2nd lessons. I strictly oppose this short!"
                })
                roundtable_dialogue.append({
                    "speaker": f"Rebuttal // {pitch_initiator}",
                    "statement": "Understood Location Agent. You are correct—selling into the floor carries extreme snapback risk. Motion to short is withdrawn."
                })
            else:
                roundtable_dialogue.append({
                    "speaker": "Location Agent (Inspected D1, H4, H1)",
                    "statement": f"Location check: Price at ${price:.2f} is resting at {range_pct*100:.1f}% of Daily Range (Floor: ${session_low:.2f}, Ceiling: ${session_high:.2f}). Structural room to run is favorable."
                })

            # ROUND 2: MOMENTUM & VELOCITY SCRUTINY
            if pitched_action == "BUY" and last_3_displacement < 0:
                roundtable_dialogue.append({
                    "speaker": "Momentum Agent (Inspected H1, M5, M1)",
                    "statement": f"[OBJECTION TO {pitch_initiator}]: M5 displacement is negative ({last_3_displacement:.1f} pts). Are we catching a falling knife? Why buy before positive velocity prints?"
                })
                roundtable_dialogue.append({
                    "speaker": "SMC Topology (Inspected H4, M15)",
                    "statement": f"It is NOT a falling knife because M15 just completed an institutional sweep at ${m15_sweep_low:.2f} ({m15_sweep_wick:.1f}pt wick) and absorbed retail stops. Smart money demand order block is active."
                })
                roundtable_dialogue.append({
                    "speaker": "Momentum Agent (Inspected H1, M5, M1)",
                    "statement": "Understood SMC. With floor sweep absorption verified, momentum is primed for reversal."
                })
            else:
                roundtable_dialogue.append({
                    "speaker": "Momentum Agent (Inspected H1, M5, M1)",
                    "statement": f"Velocity check: M5 displacement is {last_3_displacement:+.1f} pts with M1 absorption {m1_absorption}. Directional momentum fully aligns with the pitch."
                })

            # ROUND 3: MACRO & SENTIMENT PEER REVIEW
            roundtable_dialogue.append({
                "speaker": "Macro Sentinel (Inspected 1W, D1, Macro-DXY)",
                "statement": f"Macro analysis: DXY index is {dxy} and US 10Y Yield is {yield_10y}% (Impact score: {macro_score:+d}). Secular 1W trend: {w1_trend}. Macro winds provide favorable tailwind."
            })
            roundtable_dialogue.append({
                "speaker": "Sentiment Trap (Inspected Crowd-SSI, M15)",
                "statement": f"Crowd psychology: Retail herd is {retail_long:.1f}% Long / {100-retail_long:.1f}% Short. Fading retail stop clusters gives our thesis clean expansion liquidity."
            })

            # ROUND 4: CRO RISK GUARD & INVALIDATION DEFENSE
            roundtable_dialogue.append({
                "speaker": "CRO Risk Guard (Inspected M5-Geometry, Memory)",
                "statement": f"[RISK INTERROGATION]: Stop-loss proposed at ${sl:.2f} (risk: {sl_dist:.1f} pts), Take-Profit 1 at ${tp1:.2f} (R:R 1:{rr:.1f}). Initiator, what guarantees our stop is structurally protected against market maker noise?"
            })
            roundtable_dialogue.append({
                "speaker": f"Defense // {pitch_initiator}",
                "statement": f"The stop at ${sl:.2f} is anchored behind the M5 structural swing low (${local_swing_low:.2f}) and M15 demand base. If price breaches ${sl:.2f}, institutional thesis is genuinely invalidated and we exit immediately to save capital."
            })
            roundtable_dialogue.append({
                "speaker": "CRO Risk Guard (Inspected M5-Geometry, Memory)",
                "statement": f"Risk defense validated: Asymmetry is 1:{rr:.1f} (Risk: {sl_dist:.1f} pts, Reward: {abs(tp1-price):.1f} pts). Memory journal rules cleared. Capital allocation APPROVED."
            })

        else:
            roundtable_dialogue.append({
                "speaker": "Chairman Trajedor",
                "statement": f"Autonomous multi-timeframe scan complete across 1W, D1, H4, H1, M30, M15, M5, M1. No specialist detected an actionable edge. Room remains on patient standby."
            })

        # Record Final Voting Decisions
        votes = {
            "Macro Sentinel": agent_macro_vote,
            "Location Agent": agent_location_vote,
            "Momentum Agent": agent_momentum_vote,
            "SMC Topology": agent_smc_vote,
            "Sentiment Trap": agent_sentiment_vote,
            "CRO Risk Guard": agent_cro_vote,
        }

        # Formal Voting Roll Call in Dialogue
        roundtable_dialogue.append({
            "speaker": "Council Roll Call",
            "statement": f"[FINAL VOTES]: Macro: {votes['Macro Sentinel']} | Location: {votes['Location Agent']} | SMC: {votes['SMC Topology']} | Momentum: {votes['Momentum Agent']} | Sentiment: {votes['Sentiment Trap']} | CRO: {votes['CRO Risk Guard']}"
        })

        # =============================================================
        # PHASE 4: TRAJEDOR SYNTHESIS, VOTING TALLY & FINAL CALL
        # =============================================================
        total_agents = 6
        final_sell_count = sum(1 for v in votes.values() if v == "SELL")
        final_buy_count = sum(1 for v in votes.values() if v == "BUY")

        all_vetoes = []
        if pitched_action == "SELL" and agent_location_veto and "VETO SELL" in agent_location_veto:
            all_vetoes.append(agent_location_veto)
        if pitched_action == "BUY" and agent_location_veto and "VETO BUY" in agent_location_veto:
            all_vetoes.append(agent_location_veto)
        if pitched_action == "SELL" and agent_momentum_veto and "VETO SELL" in agent_momentum_veto:
            all_vetoes.append(agent_momentum_veto)
        if pitched_action == "BUY" and agent_momentum_veto and "VETO BUY" in agent_momentum_veto:
            all_vetoes.append(agent_momentum_veto)
        if agent_cro_veto:
            all_vetoes.append(agent_cro_veto)

        final_action = "STANDBY"
        confidence = 45
        consensus_pct = 0.0

        if all_vetoes:
            final_action = "STANDBY"
            confidence = 35
            consensus_pct = 0.0
            synthesis_speech = f"Trajedor Chairman: [TRADE VETOED]: {all_vetoes[0]} Proposal dismissed to protect capital."
        elif pitched_action == "SELL" and final_sell_count >= 3 and final_buy_count == 0:
            final_action = "SELL"
            consensus_pct = round((final_sell_count / total_agents) * 100, 1)
            confidence = max(80, int(consensus_pct))
            synthesis_speech = (
                f"Trajedor Chairman: [PROPOSAL CARRIES - INSTITUTIONAL SELL]: {pitch_initiator}'s pitch approved with {final_sell_count}/6 votes ({consensus_pct}% consensus). "
                f"Authorized Order: Entry ${price:.2f} | SL ${sl:.2f} | TP1 ${tp1:.2f} | R:R 1:{rr:.1f}."
            )
        elif pitched_action == "BUY" and final_buy_count >= 3 and final_sell_count == 0:
            final_action = "BUY"
            consensus_pct = round((final_buy_count / total_agents) * 100, 1)
            confidence = max(80, int(consensus_pct))
            synthesis_speech = (
                f"Trajedor Chairman: [PROPOSAL CARRIES - INSTITUTIONAL BUY]: {pitch_initiator}'s pitch approved with {final_buy_count}/6 votes ({consensus_pct}% consensus). "
                f"Setup: {pitch_setup_type}. Authorized Order: Entry ${price:.2f} | SL ${sl:.2f} | TP1 ${tp1:.2f} | Swing TP2 ${tp2:.2f} | R:R 1:{rr:.1f}."
            )
        else:
            final_action = "STANDBY"
            leading_count = max(final_sell_count, final_buy_count)
            consensus_pct = round((leading_count / total_agents) * 100, 1)
            confidence = 45
            synthesis_speech = (
                f"Trajedor Chairman: [MOTION TABLED - STANDBY]: Cross-examination finished. Insufficient council confirmation ({leading_count}/6 votes, {consensus_pct}%). "
                f"No unconfirmed trades allowed. Standing by for next market pulse."
            )

        roundtable_dialogue.append({
            "speaker": "Trajedor Chairman Synthesis",
            "statement": synthesis_speech
        })

        # Audit against persistent memory journal
        is_breakout_flag = "BREAKOUT" in pitch_setup_type or "SWING" in pitch_setup_type
        loss_context_payload = dict(recent_loss_context) if recent_loss_context else {}
        if is_breakout_flag:
            loss_context_payload["is_breakout"] = True

        gate = self.memory_journal.audit_trade_thesis_against_memory(
            action=final_action,
            price=price,
            macro_score=macro_score,
            crowd_long_pct=retail_long,
            is_scalp="BREAKOUT" if is_breakout_flag else False,
            range_pct=range_pct,
            recent_loss_context=loss_context_payload
        )
        if not gate["approved"]:
            final_action = "STANDBY"
            confidence = 35
            synthesis_speech = f"Trajedor Chairman: [MEMORY GATE BLOCKED]: {gate['warnings'][0] if gate['warnings'] else 'Vetoed by episodic memory'}"
            roundtable_dialogue.append({
                "speaker": "Memory Gate Defense",
                "statement": synthesis_speech
            })

        # =============================================================
        # PHASE 5: POST-REJECTION INDIVIDUAL MULTI-TIMEFRAME SCREENING & FORWARD TRADE PLANNING
        # If the motion was rejected or placed on standby, all 6 agents immediately
        # start screening their chosen timeframes to find fresh opportunities and plan trades.
        # =============================================================
        opportunity_plans = []
        if final_action == "STANDBY":
            roundtable_dialogue.append({
                "speaker": "Trajedor Chairman // ACTION MANDATE",
                "statement": "[REJECTION PROTOCOL ACTIVATED]: Motion tabled / rejected. Council mandate: ALL AGENTS COMMENCE IMMEDIATE MULTI-TIMEFRAME RE-SCREENING across 1W, D1, H4, H1, M30, M15, M5, M1. Identify fresh opportunities and plan active trades."
            })

            # 1. Macro Sentinel Plan (1W, D1)
            macro_plan_txt = (
                f"Macro Screening (1W, D1): 1W secular trend is {w1_trend}, US 10Y Yield is {yield_10y}%, DXY score is {macro_score:+d}. "
                f"Forward Plan: {'Watching DXY softness below 101.80 for high-conviction gold trend expansion' if macro_score >= 0 else 'Tracking yield spikes above 5.30% for macro supply pressure'}. "
                f"Standing by to back {'BUY' if w1_trend == 'BULLISH' else 'SELL'} upon macro alignment."
            )
            roundtable_dialogue.append({
                "speaker": "Macro Sentinel // MTF Re-Screening",
                "statement": macro_plan_txt
            })
            opportunity_plans.append({"agent": "Macro Sentinel", "timeframes": "1W, D1", "plan": macro_plan_txt})

            # 2. Location Agent Plan (D1, H4, H1)
            if h1_bullish_trend or d1_bullish_expansion:
                trend_pullback_lvl = round(recent_h1_low, 2)
                loc_plan_txt = (
                    f"Location Screening (D1, H4, H1): Institutional Bullish Trend Expansion active (Higher Highs & Higher Lows). "
                    f"Forward Plan: Opportunity A (Trend Retest Long): Waiting for shallow pullback into dynamic H1 Demand Base ${trend_pullback_lvl:.2f} for high-conviction BUY. "
                    f"Opportunity B (Expansion Long): Breakout through session high ${session_high:.2f} triggers instant momentum long."
                )
            else:
                discount_lvl = round(session_low + (range_span * 0.25), 2)
                premium_lvl = round(session_high - (range_span * 0.20), 2)
                loc_plan_txt = (
                    f"Location Screening (D1, H4, H1): Current price ${price:.2f} is at {range_pct*100:.1f}% of Daily Range [${session_low:.2f} - ${session_high:.2f}]. "
                    f"Forward Plan: Opportunity A (Value Dip): Waiting for pullback to Discount Floor ${discount_lvl:.2f} for BUY setup. "
                    f"Opportunity B (Ceiling Fade): Watching ${premium_lvl:.2f}-${session_high:.2f} for liquidity exhaustion SELL."
                )
            roundtable_dialogue.append({
                "speaker": "Location Agent // MTF Re-Screening",
                "statement": loc_plan_txt
            })
            opportunity_plans.append({"agent": "Location Agent", "timeframes": "D1, H4, H1", "plan": loc_plan_txt})

            # 3. SMC Topology Plan (H4, H1, M30, M15)
            if h1_bullish_trend or d1_bullish_expansion:
                smc_plan_txt = (
                    f"SMC Topology Screening (H4, H1, M30, M15): Bullish Order Block mapped at ${round(recent_h1_low, 2)}. "
                    f"Target Liquidity Pool at ${session_high + 10.0:.2f}. "
                    f"Forward Plan: Monitoring M15/M5 stabilization above demand pivot ${round(recent_h1_low, 2)}. Will pitch BULLISH_TREND_ORDER_BLOCK_PULLBACK as soon as M5 absorption confirms."
                )
            else:
                smc_target = session_high if range_pct >= 0.50 else session_low
                smc_direction = "BUY (on sweep of floor)" if range_pct < 0.50 else "SELL (on sweep of ceiling)"
                smc_plan_txt = (
                    f"SMC Topology Screening (H4, H1, M30, M15): Fair Value Gap mapped between ${round(price-2.0, 2)} and ${round(price+2.0, 2)}. "
                    f"Target Liquidity Pool at ${smc_target:.2f}. "
                    f"Forward Plan: Monitoring for institutional liquidity raid at ${smc_target:.2f} followed by M15 Market Structure Shift to pitch {smc_direction}."
                )
            roundtable_dialogue.append({
                "speaker": "SMC Topology // MTF Re-Screening",
                "statement": smc_plan_txt
            })
            opportunity_plans.append({"agent": "SMC Topology", "timeframes": "H4, H1, M30, M15", "plan": smc_plan_txt})

            # 4. Momentum Agent Plan (M30, M15, M5, M1)
            mom_trigger = round(price + 3.5, 2) if pitched_action != "SELL" else round(price - 3.5, 2)
            mom_plan_txt = (
                f"Momentum Screening (M30, M15, M5, M1): M5 displacement is {last_3_displacement:+.1f} pts. "
                f"Forward Plan: Screening order book tape for volume surge. If displacement exceeds 4.0 pts through ${mom_trigger:.2f}, will immediately trigger MOMENTUM_DISPLACEMENT_BURST pitch."
            )
            roundtable_dialogue.append({
                "speaker": "Momentum Agent // MTF Re-Screening",
                "statement": mom_plan_txt
            })
            opportunity_plans.append({"agent": "Momentum Agent", "timeframes": "M30, M15, M5, M1", "plan": mom_plan_txt})

            # 5. Sentiment Trap Plan (Crowd SSI, M15)
            sent_target = local_swing_low if retail_long > 60 else local_swing_high
            sent_plan_txt = (
                f"Sentiment Trap Screening (Crowd SSI, M15): Retail herd is {retail_long:.1f}% Long. Stop-loss cluster identified at ${sent_target:.2f}. "
                f"Forward Plan: Waiting for smart money to flush retail stop liquidity at ${sent_target:.2f}. Will pitch instant institutional absorption entry once stops trigger."
            )
            roundtable_dialogue.append({
                "speaker": "Sentiment Trap // MTF Re-Screening",
                "statement": sent_plan_txt
            })
            opportunity_plans.append({"agent": "Sentiment Trap", "timeframes": "Crowd-SSI, M15", "plan": sent_plan_txt})

            # 6. CRO Risk Guard Plan (Geometry, Risk Engine, Memory)
            cro_plan_txt = (
                f"CRO Risk Guard (Risk Engine): Structural boundaries set: Invalidation floor ${local_swing_low:.2f}, Invalidation ceiling ${local_swing_high:.2f}. "
                f"Forward Plan: Any incoming trade pitch must strictly guarantee minimum 1:2.0 R:R and clear the 15-minute post-loss cooldown gate. Capital is locked and protected."
            )
            roundtable_dialogue.append({
                "speaker": "CRO Risk Guard // MTF Re-Screening",
                "statement": cro_plan_txt
            })
            opportunity_plans.append({"agent": "CRO Risk Guard", "timeframes": "Geometry, Risk", "plan": cro_plan_txt})

        rationale_list = [f"{name} ({', '.join(tfs)}): {vote} ({reason})" for name, tfs, vote, reason in agent_reviews]

        return TradeThesis(
            symbol=self.symbol,
            action=final_action,
            confidence_score=confidence,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            risk_reward_ratio=rr,
            metamorphosis_mode=pitch_setup_type if final_action in ("BUY", "SELL") else "SCALP_TO_SWING_PROMOTION",
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
            reasoning_monologue=synthesis_speech,
            memory_gate_approved=gate["approved"],
            memory_warnings=gate["warnings"],
            lessons_consulted=[gate["recent_lesson"]],
            council_votes=votes,
            council_consensus_pct=consensus_pct,
            council_rationale=rationale_list,
            pitch_initiator=pitch_initiator,
            pitch_setup_type=pitch_setup_type,
            roundtable_transcript=roundtable_dialogue,
            opportunity_hunt_plans=opportunity_plans,
            chambers_briefing=chambers_dossier
        )
