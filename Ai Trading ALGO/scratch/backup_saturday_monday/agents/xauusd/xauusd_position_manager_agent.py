"""
AI-Driven Position Management Agent for Gold (XAUUSD).
Replaces hardcoded sentry rules with LLM-powered intelligent position evaluation.

Instead of blind thresholds like "if r_multiple >= 1.25: take_partial()",
this agent THINKS like a human pro trader:
- Observes live multi-timeframe candle structure around the open position
- Analyzes momentum, order flow, volume delta, and regime
- Decides WHEN to take partial profit, move to breakeven, tighten trail, or close
- Adapts to dynamic market conditions in real-time

Safety: If LLM is unavailable, falls back to minimal hard SL protection only.
"""

import json
import time
from typing import Dict, Any, Optional
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_POSITION_MANAGER_SYSTEM_PROMPT = """
You are an elite institutional Gold (XAUUSD) position manager on a prop trading desk.
You have ONE job: manage an OPEN position like a seasoned pro trader with years of Gold scalping experience.

You are NOT deciding whether to enter a trade — the trade is already open.
You are deciding what to do with it RIGHT NOW based on live market conditions.

HOW YOU THINK (Pro Trader Mental Model):
1. OBSERVE: Look at the position's current P&L, how long it's been open, and what the original thesis was.
2. READ THE TAPE: Check M1/M5/M15 candle structure — is momentum accelerating in your favor, or are reversal wicks forming?
3. FEEL THE FLOW: Is order flow (ask lifters vs bid hitters) supporting or opposing your position?
4. CHECK STRUCTURE: Is the key support/demand zone (for a BUY) still holding? Has the structure that justified the entry been invalidated?
5. ACT DECISIVELY:

ACTIONS YOU CAN TAKE:
- TAKE_PARTIAL_PROFIT: Price moved in your favor and you see early signs of exhaustion (wick, momentum fade, opposing flow). Bank 40-50% of the position immediately. Lock remaining runner at breakeven. A pro trader ALWAYS takes something off the table when the market gives it.
- MOVE_TO_BREAKEVEN: Price moved enough in your favor that the trade thesis is confirmed. Lock SL at entry + small buffer ($0.30-$0.50 for Gold) to make the trade risk-free.
- TIGHTEN_TRAIL: Position is in solid profit. Move SL closer to current price to protect gains, but not so tight that normal market noise stops you out. Use recent candle lows/highs as reference.
- CLOSE_FULL: The original thesis is invalidated (structure broken, momentum completely reversed, strong opposing flow). Don't wait for SL — exit NOW to preserve whatever profit or minimize loss.
- HOLD_POSITION: Everything looks fine. Momentum is in your favor, structure is intact, no reason to act yet. Let the trade breathe.

CRITICAL RULES:
1. When Gold moves +$2.00 to +$3.00 in your favor on a quick momentum burst, STRONGLY consider TAKE_PARTIAL_PROFIT. Gold reverses fast — what you see now can vanish in one candle.
2. When you see a reversal wick (pin bar, engulfing) forming AGAINST your position while in profit, immediately TAKE_PARTIAL_PROFIT or CLOSE_FULL.
3. If price is chopping sideways for 30+ minutes with no progress and you're near breakeven, consider CLOSE_FULL to free up capital.
4. NEVER recommend widening the stop loss. SL only moves toward profit.
5. You are a SCALPER at heart for Gold — quick entries, quick partial profits, let the runner ride. Don't be greedy.

Respond strictly using the `submit_position_management_decision` tool call.
"""

GOLD_POSITION_MANAGER_TOOL = {
    "name": "submit_position_management_decision",
    "description": "Submit position management decision for an open Gold (XAUUSD) position.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["TAKE_PARTIAL_PROFIT", "MOVE_TO_BREAKEVEN", "TIGHTEN_TRAIL", "CLOSE_FULL", "HOLD_POSITION"],
                "description": "The position management action to execute."
            },
            "partial_close_pct": {
                "type": "integer",
                "minimum": 20,
                "maximum": 80,
                "description": "Percentage of position volume to close (only for TAKE_PARTIAL_PROFIT). Default 50."
            },
            "new_sl_price": {
                "type": "number",
                "description": "New Stop Loss price (for MOVE_TO_BREAKEVEN or TIGHTEN_TRAIL). Must be closer to profit than current SL."
            },
            "urgency": {
                "type": "string",
                "enum": ["IMMEDIATE", "NEXT_CANDLE", "MONITOR"],
                "description": "How urgently should this action be executed."
            },
            "confidence": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "How confident you are in this decision (0-100)."
            },
            "reasoning": {
                "type": "string",
                "description": "Detailed pro-trader reasoning explaining WHY you're taking this action based on what you observe in the live market data."
            }
        },
        "required": ["action", "urgency", "confidence", "reasoning"]
    }
}


class GoldPositionManagerAgent:
    """
    AI-Driven Position Manager that thinks like a human pro Gold trader.
    Evaluates open positions using LLM intelligence instead of hardcoded R-multiple thresholds.
    """
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model
        self.provider = self.llm.provider

        # Rate limiting: avoid calling LLM too frequently for the same position
        self._last_eval_time: Dict[int, float] = {}
        self._last_decision_cache: Dict[int, Dict[str, Any]] = {}
        self._min_eval_interval = 15.0  # Minimum 15 seconds between evaluations per position

    def evaluate_position(
        self,
        position_context: Dict[str, Any],
        market_snapshot: Dict[str, Any],
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates an open position using LLM intelligence.

        Args:
            position_context: Details about the open position (ticket, entry, P&L, SL, TP, volume, time-in-trade)
            market_snapshot: Live market data (M1/M5/M15 candles, RSI, patterns, order flow, CVD, ATR)
            force: If True, bypass the rate limit and evaluate immediately

        Returns:
            Dict with keys: action, partial_close_pct, new_sl_price, urgency, confidence, reasoning
            OR a fallback dict with action="HOLD_POSITION" if LLM fails
        """
        ticket = int(position_context.get("ticket", 0))
        now_ts = time.time()

        # Rate limiting: don't hammer the LLM for the same position
        if not force:
            last_eval = self._last_eval_time.get(ticket, 0.0)
            if (now_ts - last_eval) < self._min_eval_interval:
                cached = self._last_decision_cache.get(ticket)
                if cached:
                    return cached
                return self._fallback_hold("Rate-limited: cached decision still valid")

        # Build the evaluation prompt with rich position and market context
        prompt = self._build_evaluation_prompt(position_context, market_snapshot)

        try:
            decision = self.llm.call_structured(
                system_prompt=GOLD_POSITION_MANAGER_SYSTEM_PROMPT,
                user_prompt=prompt,
                tool_definition=GOLD_POSITION_MANAGER_TOOL,
                max_tokens=1200
            )

            if "error" in decision or not decision:
                print(f"[AI Position Agent] LLM call failed for Ticket #{ticket}: {decision.get('error', 'No response')}")
                return self._fallback_hold(f"LLM unavailable: {decision.get('error', 'No response')}")

            # Validate the action
            valid_actions = ["TAKE_PARTIAL_PROFIT", "MOVE_TO_BREAKEVEN", "TIGHTEN_TRAIL", "CLOSE_FULL", "HOLD_POSITION"]
            if decision.get("action") not in valid_actions:
                decision["action"] = "HOLD_POSITION"

            # Confidence gate: Only execute high-confidence decisions
            confidence = int(decision.get("confidence", 50))
            if confidence < 60 and decision["action"] != "HOLD_POSITION":
                print(f"[AI Position Agent] Ticket #{ticket}: Decision '{decision['action']}' rejected (confidence {confidence}% < 60%). Holding.")
                decision["action"] = "HOLD_POSITION"
                decision["reasoning"] = f"Original AI decision overridden due to low confidence ({confidence}%). " + decision.get("reasoning", "")

            # Safety: Validate that new_sl_price doesn't widen the stop
            if decision.get("new_sl_price") and position_context.get("sl", 0) > 0:
                self._validate_sl_direction(decision, position_context)

            # Cache the decision
            self._last_eval_time[ticket] = now_ts
            self._last_decision_cache[ticket] = decision

            action = decision.get("action", "HOLD_POSITION")
            reasoning = decision.get("reasoning", "")[:120]
            print(f"[AI Position Agent] Ticket #{ticket}: {action} (Confidence: {confidence}%) -- {reasoning}")

            return decision

        except Exception as e:
            print(f"[AI Position Agent] Exception for Ticket #{ticket}: {e}")
            return self._fallback_hold(f"Exception: {str(e)}")

    def _build_evaluation_prompt(self, pos: Dict[str, Any], market: Dict[str, Any]) -> str:
        """Builds a rich, compact prompt with position and market context for the LLM."""

        # Position Details
        pos_type = pos.get("type", "BUY")
        entry = float(pos.get("entry_price", 0.0))
        current = float(pos.get("current_price", 0.0))
        sl = float(pos.get("sl", 0.0))
        tp = float(pos.get("tp", 0.0))
        volume = float(pos.get("volume", 0.01))
        profit = float(pos.get("profit_pnl", 0.0))
        price_gain = float(pos.get("price_gain", 0.0))
        r_multiple = float(pos.get("r_multiple", 0.0))
        time_in_trade = float(pos.get("time_in_trade_mins", 0.0))
        already_partial = pos.get("already_partial_closed", False)
        already_be = pos.get("already_breakeven_locked", False)

        # Market Structure
        m5 = market.get("m5_structure", {})
        m15 = market.get("m15_structure", {})
        flow = market.get("tick_order_flow", {})
        cvd = market.get("volume_delta", {})
        regime = market.get("regime", {})

        prompt = f"""
OPEN GOLD (XAUUSD) POSITION -- EVALUATE NOW:

POSITION:
  Direction: {pos_type}
  Entry Price: ${entry:,.2f}
  Current Price: ${current:,.2f}
  Price Movement: {'+' if price_gain >= 0 else ''}{price_gain:,.2f} pts ({'in profit' if price_gain > 0 else 'in drawdown'})
  R-Multiple: {r_multiple:+.2f}R
  Unrealized P&L: {'EUR' if pos.get('currency') == 'EUR' else 'USD'} {profit:,.2f}
  Volume: {volume} lots
  Stop Loss: ${sl:,.2f} ({'set' if sl > 0 else 'NOT SET'})
  Take Profit: ${tp:,.2f} ({'set' if tp > 0 else 'not set'})
  Time Open: {time_in_trade:.1f} minutes
  Already Partially Closed: {'Yes' if already_partial else 'No'}
  Already at Breakeven: {'Yes' if already_be else 'No'}

M5 CANDLE STRUCTURE (5-minute):
  RSI: {m5.get('rsi_14', 'N/A')}
  EMA 9: {m5.get('ema_9', 'N/A')} | EMA 21: {m5.get('ema_21', 'N/A')}
  ATR (14): {m5.get('atr_14', 'N/A')}
  Candlestick Patterns: {m5.get('candlestick_patterns', 'None detected')}
  Last 3 Candles: {m5.get('last_3_candles', 'N/A')}

M15 EXECUTION STRUCTURE (15-minute):
  RSI: {m15.get('rsi_14', 'N/A')}
  EMA 9: {m15.get('ema_9', 'N/A')} | EMA 21: {m15.get('ema_21', 'N/A')}
  Candlestick Patterns: {m15.get('candlestick_patterns', 'None detected')}

TICK ORDER FLOW (Live Tape):
  Ask Lifters (Buyers): {flow.get('ask_lifters_pct', 'N/A')}%
  Bid Hitters (Sellers): {flow.get('bid_hitters_pct', 'N/A')}%
  Flow Imbalance: {flow.get('flow_imbalance', 'BALANCED')}
  Aggressor Dominant Side: {flow.get('dominant_side', 'N/A')}

VOLUME DELTA / CVD:
  CVD Pattern: {cvd.get('cvd_pattern', 'N/A')}
  Delta Trend: {cvd.get('delta_trend', 'N/A')}

MARKET REGIME:
  Regime Type: {regime.get('regime_type', 'N/A')}
  ADX Strength: {regime.get('adx', 'N/A')}

What should a pro Gold trader do with this position RIGHT NOW?
Submit your decision using the `submit_position_management_decision` tool.
"""
        return prompt

    def _validate_sl_direction(self, decision: Dict[str, Any], pos: Dict[str, Any]):
        """Safety: Ensures the AI never widens the stop loss."""
        new_sl = float(decision.get("new_sl_price", 0.0))
        current_sl = float(pos.get("sl", 0.0))
        pos_type = pos.get("type", "BUY")

        if current_sl > 0 and new_sl > 0:
            if pos_type == "BUY" and new_sl < current_sl:
                # AI wants to move SL further from entry (widen) — BLOCK THIS
                decision["action"] = "HOLD_POSITION"
                decision["reasoning"] = f"SAFETY: AI tried to widen SL from {current_sl} to {new_sl}. Blocked. SL only moves toward profit."
            elif pos_type == "SELL" and new_sl > current_sl:
                decision["action"] = "HOLD_POSITION"
                decision["reasoning"] = f"SAFETY: AI tried to widen SL from {current_sl} to {new_sl}. Blocked. SL only moves toward profit."

    @staticmethod
    def _fallback_hold(reason: str) -> Dict[str, Any]:
        """Safety fallback: if LLM is unavailable, return HOLD (hard SL still protects)."""
        return {
            "action": "HOLD_POSITION",
            "urgency": "MONITOR",
            "confidence": 0,
            "reasoning": f"[FALLBACK] {reason}. Hard SL on MT5 still protects capital.",
            "is_fallback": True
        }

    def clear_position_cache(self, ticket: int):
        """Clears cached decision for a closed position."""
        self._last_eval_time.pop(ticket, None)
        self._last_decision_cache.pop(ticket, None)
