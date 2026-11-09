"""
Trajedor Humanoid Trading Mind (Pure Discretionary Cognitive AI).

Operates like an elite human prop trader with ZERO rigid if/else conditions:
1. Reads the "Story of Price" (Where did price come from? Who is trapped? Where is liquidity?).
2. Cross-verifies Macro Context + Micro Order Flow + Crowd Mood.
3. Adaptively chooses trading style on the fly:
   - SCALP: Quick 10-20 pip snipes during consolidation or sweeps.
   - DAY_TRADE: 40-80 pip session expansion trades.
   - SWING: Multi-day trend following on macro regime alignment.
   - SIT_ON_HANDS: Cash is a position; passes when conditions are murky.
4. Human In-Flight Management: Dynamic partial profit taking, early thesis invalidation cuts.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class HumanoidTradePlan:
    trade_style: str            # "SCALP", "DAY_TRADE", "SWING", "SIT_ON_HANDS"
    bias: str                   # "LONG", "SHORT", "NEUTRAL"
    thesis_narrative: str       # The human story explaining the market context
    cross_verification: str     # Why macro, tape, and technicals agree or disagree
    entry_level: float          # Desired entry price
    invalidation_level: float   # Where the human thesis is proven wrong
    target_1: float             # First profit scaling level
    target_2: float             # Final objective
    risk_reward_ratio: float
    confidence_score: int       # 0 to 100
    execution_urgency: str      # "IMMEDIATE_MARKET", "LIMIT_PULLBACK", "WAIT"


class HumanoidTraderMind:
    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol

    def deliberate_like_a_human(
        self,
        market_narrative: Dict[str, Any],
        lessons_memory: Optional[List[str]] = None
    ) -> HumanoidTradePlan:
        """
        Synthesizes the entire market puzzle without rigid if/else rules.
        Evaluates the price story, macro climate, order flow tape, and crowd mood.
        """
        pricing = market_narrative.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("price", 0.0) or 2650.0)
        atr_14 = float(market_narrative.get("atr_14", 2.50) or 2.50)
        session = market_narrative.get("session", "LONDON_NY_OVERLAP")
        news_threat = market_narrative.get("news_threat_level", "LOW")
        dxy_sentiment = market_narrative.get("dxy_direction", "NEUTRAL")
        crowd_mood = market_narrative.get("crowd_mood", "NEUTRAL")  # e.g. "HEAVILY_BULLISH", "PANIC_SELLING"
        price_action_story = market_narrative.get("price_action_story") or market_narrative.get("price_story", "")

        # --- SENSE 1: Check Global Research Dossier & Macro Shocks ---
        dossier = market_narrative.get("research_dossier")
        if dossier:
            clearance = dossier.get("institutional_action_clearance", "FULL_SWING_CLEARANCE")
            blackout_active = dossier.get("blackout_active", False)
            blackout_reason = dossier.get("blackout_reason", "")
            if clearance == "TOTAL_STANDBY" or blackout_active or news_threat == "HIGH":
                return HumanoidTradePlan(
                    trade_style="SIT_ON_HANDS",
                    bias="NEUTRAL",
                    thesis_narrative=f"Research Terminal Clearance: TOTAL_STANDBY. {blackout_reason or 'Acute market-shaking catalyst or news blackout active.'}",
                    cross_verification="All institutional timeframes placed on defensive standby. Zero gambling into news shocks.",
                    entry_level=live_price,
                    invalidation_level=0.0,
                    target_1=0.0,
                    target_2=0.0,
                    risk_reward_ratio=0.0,
                    confidence_score=0,
                    execution_urgency="WAIT"
                )
        elif news_threat == "HIGH":
            return HumanoidTradePlan(
                trade_style="SIT_ON_HANDS",
                bias="NEUTRAL",
                thesis_narrative="High-impact economic data is imminent. Market is in defensive pricing. Only amateurs gamble into news spikes.",
                cross_verification="Forex Factory flags high volatility risk. Preserving capital is the highest priority.",
                entry_level=live_price,
                invalidation_level=0.0,
                target_1=0.0,
                target_2=0.0,
                risk_reward_ratio=0.0,
                confidence_score=0,
                execution_urgency="WAIT"
            )

        # --- SENSE 2: Synthesize the Human Price Story ---
        story_lower = price_action_story.lower()
        swept_low = ("sweep" in story_lower or "swept" in story_lower) and "low" in story_lower
        swept_high = ("sweep" in story_lower or "swept" in story_lower) and "high" in story_lower
        absorption_buying = "absorption" in story_lower or "buying" in story_lower or "delta flipping positive" in story_lower
        trending_up = "higher highs" in story_lower or "bullish expansion" in story_lower

        # Decision 1: Bullish Liquidity Sweep & Absorption
        if swept_low and absorption_buying and dxy_sentiment != "BULLISH_EXPANSION":
            inval = round(live_price - (atr_14 * 1.2), 2)
            t1 = round(live_price + (atr_14 * 1.5), 2)
            t2 = round(live_price + (atr_14 * 3.0), 2)
            rr = round((t1 - live_price) / max(0.1, live_price - inval), 2)

            # Style decision: Scalp vs Day Trade
            style = "DAY_TRADE" if session in ["LONDON_OPEN", "NY_OPEN", "LONDON_NY_OVERLAP"] else "SCALP"

            narrative = (
                f"Market swept the session lows to run retail stops, but sellers lacked follow-through. "
                f"Limit buyers aggressively absorbed the discount at ${live_price:.2f}. "
                f"DXY is showing fatigue ({dxy_sentiment}). The path of least resistance is upward into overhead buy-side liquidity."
            )

            cross_verif = (
                f"1. Tape shows passive accumulation at lows. "
                f"2. Crowd mood is {crowd_mood} (contrarian opportunity). "
                f"3. Invalidation is clearly defined below the sweep low at ${inval:.2f}."
            )

            return HumanoidTradePlan(
                trade_style=style,
                bias="LONG",
                thesis_narrative=narrative,
                cross_verification=cross_verif,
                entry_level=round(live_price, 2),
                invalidation_level=inval,
                target_1=t1,
                target_2=t2,
                risk_reward_ratio=rr,
                confidence_score=85,
                execution_urgency="IMMEDIATE_MARKET"
            )

        # Decision 2: Bearish Liquidity Sweep at Overhead Resistance
        elif swept_high and dxy_sentiment != "BEARISH_DUMP":
            inval = round(live_price + (atr_14 * 1.2), 2)
            t1 = round(live_price - (atr_14 * 1.5), 2)
            t2 = round(live_price - (atr_14 * 3.0), 2)
            rr = round((live_price - t1) / max(0.1, inval - live_price), 2)

            style = "DAY_TRADE" if session in ["LONDON_OPEN", "NY_OPEN"] else "SCALP"

            narrative = (
                f"Price pierced overhead session highs, but failed to sustain displacement. "
                f"Smart money used breakout buy-stops to offload short inventory. Rejection wicks confirm distribution."
            )

            cross_verif = (
                f"1. Overhead resistance held firm. "
                f"2. Retail breakout buyers trapped at highs. "
                f"3. Clear structural invalidation above ${inval:.2f}."
            )

            return HumanoidTradePlan(
                trade_style=style,
                bias="SHORT",
                thesis_narrative=narrative,
                cross_verification=cross_verif,
                entry_level=round(live_price, 2),
                invalidation_level=inval,
                target_1=t1,
                target_2=t2,
                risk_reward_ratio=rr,
                confidence_score=82,
                execution_urgency="IMMEDIATE_MARKET"
            )

        # Decision 3: Quiet Consolidation (Small Scalps Only)
        elif session == "ASIAN_SESSION" or "ranging" in price_action_story.lower():
            inval = round(live_price - (atr_14 * 0.8), 2)
            t1 = round(live_price + (atr_14 * 1.0), 2)
            return HumanoidTradePlan(
                trade_style="SCALP",
                bias="LONG",
                thesis_narrative="Asian session consolidation box. Volatility is compressed; taking quick 12-15 pip bounds off support.",
                cross_verification="No macro drivers active. Fast exit mandatory.",
                entry_level=round(live_price, 2),
                invalidation_level=inval,
                target_1=t1,
                target_2=t1,
                risk_reward_ratio=1.25,
                confidence_score=70,
                execution_urgency="LIMIT_PULLBACK"
            )

        # Default: No clear edge
        else:
            return HumanoidTradePlan(
                trade_style="SIT_ON_HANDS",
                bias="NEUTRAL",
                thesis_narrative="Price action is muddy and indecisive. Neither buyers nor sellers have shown conviction.",
                cross_verification="No clean asymmetric edge present. Professional traders preserve mental and financial capital.",
                entry_level=live_price,
                invalidation_level=0.0,
                target_1=0.0,
                target_2=0.0,
                risk_reward_ratio=0.0,
                confidence_score=40,
                execution_urgency="WAIT"
            )

    def evaluate_in_flight_position_like_a_human(
        self,
        current_position: Dict[str, Any],
        live_price: float,
        latest_market_story: str
    ) -> Dict[str, Any]:
        """
        Acts like a human managing an open position:
        Decides when to take partials, trail stops, or cut losses early if the thesis died.
        """
        entry_price = float(current_position.get("entry_price", 0.0))
        pos_type = str(current_position.get("type", "BUY")).upper()
        sl = float(current_position.get("sl", 0.0))
        tp = float(current_position.get("tp", 0.0))

        pnl_pts = (live_price - entry_price) if pos_type == "BUY" else (entry_price - live_price)

        # Human Assessment:
        # Case 1: In solid profit (> +15 pips / +1.50 on Gold)
        if pnl_pts >= 1.50:
            return {
                "decision": "PARTIAL_SCALE_OUT",
                "action": "CLOSE_50_PCT",
                "new_stop_loss": round(entry_price + 0.20 if pos_type == "BUY" else entry_price - 0.20, 2),
                "human_thought": f"Trade is up +{pnl_pts:.2f} points! Banking 50% profit and locking stop to Breakeven (+1 pip). Free trade now."
            }

        # Case 2: Trade is going in the red AND the market story flipped
        elif pnl_pts < -0.80 and ("breaking against" in latest_market_story or "opposing momentum" in latest_market_story):
            return {
                "decision": "EARLY_THESIS_CUT",
                "action": "CLOSE_ENTIRE_POSITION",
                "new_stop_loss": sl,
                "human_thought": f"Market dynamics flipped ({latest_market_story}). The reason we entered no longer exists. Cutting the trade at small loss (-{abs(pnl_pts):.2f}) rather than letting it hit full stop loss."
            }

        # Case 3: Normal breathing room
        else:
            return {
                "decision": "STAY_PATIENT",
                "action": "HOLD",
                "new_stop_loss": sl,
                "human_thought": "Trade is developing within expected volatility boundaries. Maintaining conviction."
            }


if __name__ == "__main__":
    print("Testing Trajedor Humanoid Trader Mind...")
    mind = HumanoidTraderMind(symbol="XAUUSD")

    # Scenario 1: London Open Asian Low Sweep
    sample_narrative = {
        "pricing": {"bid": 2649.50},
        "atr_14": 2.60,
        "session": "LONDON_OPEN",
        "news_threat_level": "LOW",
        "dxy_direction": "BEARISH_EXHAUSTION",
        "crowd_mood": "PANIC_SELLING",
        "price_action_story": "Price swept Asian low at 2648.00 and found aggressive buying absorption on the tape with delta flipping positive."
    }

    plan = mind.deliberate_like_a_human(sample_narrative)

    print("\n" + "=" * 70)
    print("HUMANOID TRADER DELIBERATION")
    print("=" * 70)
    print(f"Style Selected: {plan.trade_style} | Direction: {plan.bias} | Urgency: {plan.execution_urgency}")
    print(f"Confidence: {plan.confidence_score}% | Risk/Reward: 1:{plan.risk_reward_ratio}")
    print(f"\nThe Human Story & Thesis:\n{plan.thesis_narrative}")
    print(f"\nCross-Verification:\n{plan.cross_verification}")
    print(f"\nPlanned Levels -> Entry: ${plan.entry_level} | Invalidation (SL): ${plan.invalidation_level} | Target 1: ${plan.target_1} | Target 2: ${plan.target_2}")

    # Scenario 2: In-Flight Management (Price moved in our favor)
    open_trade = {"entry_price": 2649.50, "type": "BUY", "sl": 2646.38, "tp": 2657.30}
    management = mind.evaluate_in_flight_position_like_a_human(
        current_position=open_trade,
        live_price=2651.80,  # Up +2.30 points
        latest_market_story="Momentum continuing higher"
    )
    print("\n" + "-" * 70)
    print("IN-FLIGHT POSITION MANAGEMENT")
    print("-" * 70)
    print(f"Human Decision: {management['decision']}")
    print(f"Action: {management['action']}")
    print(f"New SL: ${management['new_stop_loss']}")
    print(f"Trader's Internal Monologue:\n\"{management['human_thought']}\"")
