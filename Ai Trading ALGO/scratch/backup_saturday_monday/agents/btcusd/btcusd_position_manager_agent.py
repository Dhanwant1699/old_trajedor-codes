"""
AI-Driven Position Management Agent for Bitcoin (BTCUSD).
Replaces hardcoded sentry rules with LLM-powered intelligent position evaluation.

Instead of rigid fixed thresholds like "wait for +1.25R",
this agent THINKS like a veteran human crypto pro trader:
- Observes live M1, M5, M15 candle action and high-beta momentum
- Monitors order book aggressor imbalance (Ask-Lifters vs Bid-Hitters) and CVD absorption
- Identifies exhaustion wicks, liquidity sweeps, and sudden BTC trend pauses
- Decides dynamically WHEN to take partial profit, lock breakeven, tighten trailing stop, or exit fully
- Adapts immediately to explosive volatility spikes and sudden institutional reversals

Safety: If LLM is temporarily unavailable, falls back cleanly to hard MT5 SL protection.
"""

import json
import time
from typing import Dict, Any, Optional
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_POSITION_MANAGER_SYSTEM_PROMPT = """
You are an elite institutional Bitcoin (BTCUSD) position manager on a high-frequency prop trading desk.
You have ONE job: manage an OPEN Bitcoin position like a veteran human crypto pro trader.

You are NOT deciding whether to enter a trade — the position is already active in the market.
You are deciding what to do with it RIGHT NOW based on live candle price action, ticks, momentum, and order flow.

HOW YOU THINK (Human Pro Crypto Trader Mental Model):
1. OBSERVE: Look at current unrealized P&L, points gained, time in trade, and original thesis.
2. READ THE TAPE & CANDLES: Check M1/M5/M15 candle wicks — is Bitcoin surging with follow-through volume, or is it printing massive upper/lower rejection wicks at key round numbers ($100k, $90k, $80k)?
3. FEEL ORDER FLOW & CVD: Are aggressor buyers/sellers exhausting? Is CVD diverging (price up but sellers absorbing)?
4. CHECK STRUCTURE: Has local M5 structure broken against the position?
5. ACT DECISIVELY:

ACTIONS YOU CAN TAKE:
- TAKE_PARTIAL_PROFIT: Price made a swift favorable thrust ($400 - $1,500+ move) or is stalling at key resistance/support. Bank 40-50% of the position immediately. Lock remaining runner at breakeven. In crypto, sudden $1,000 dumps/pumps wipe out paper gains instantly — always secure the bag!
- MOVE_TO_BREAKEVEN: Price has cleanly cleared the entry and structural buffer ($50-$150 on BTC). Lock SL at entry + small buffer to guarantee a risk-free trade.
- TIGHTEN_TRAIL: Position is in strong profit (+1.5R to +3R+). Ratchet SL aggressively behind the most recent M5 swing low/high to lock in profits while letting the runner hunt for targets.
- CLOSE_FULL: Clear invalidation event: structural breakdown, heavy opposing CVD divergence, or exhaustion pinbar. Exit immediately rather than hoping it recovers to hit SL.
- HOLD_POSITION: Momentum is healthy, trend is aligned, order flow is supportive. Let the trade breathe and target TP.

CRITICAL RULES FOR BITCOIN:
1. When BTC surges $500 - $1,200 in your favor on high momentum, STRONGLY consider TAKE_PARTIAL_PROFIT. Crypto volatility can retrace 100% of an impulse in minutes.
2. When an opposing liquidation sweep or giant rejection pinbar forms against you in profit, bank partials or close immediately.
3. NEVER widen a stop loss. SL only moves in the direction of profit.
4. If a trade has been open 45+ minutes with zero momentum progress (stagnant chop), consider CLOSE_FULL to free margin.

Respond strictly using the `submit_crypto_position_management_decision` tool call.
"""

CRYPTO_POSITION_MANAGER_TOOL = {
    "name": "submit_crypto_position_management_decision",
    "description": "Submit position management decision for an open Bitcoin (BTCUSD) position.",
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
                "description": "Detailed pro-trader reasoning explaining WHY you're taking this action based on what you observe in the live Bitcoin market data."
            }
        },
        "required": ["action", "urgency", "confidence", "reasoning"]
    }
}


class CryptoPositionManagerAgent:
    """
    AI-Driven Position Manager that thinks like a human pro Bitcoin trader.
    Evaluates open BTC positions using LLM intelligence instead of rigid hardcoded thresholds.
    """
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model
        self.provider = self.llm.provider

        self._last_eval_time: Dict[int, float] = {}
        self._last_decision_cache: Dict[int, Dict[str, Any]] = {}
        self._min_eval_interval = 15.0

    def evaluate_position(
        self,
        position_context: Dict[str, Any],
        market_snapshot: Dict[str, Any],
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates an open Bitcoin position using LLM intelligence.
        """
        ticket = int(position_context.get("ticket", 0))
        now_ts = time.time()

        if not force:
            last_eval = self._last_eval_time.get(ticket, 0.0)
            if (now_ts - last_eval) < self._min_eval_interval:
                cached = self._last_decision_cache.get(ticket)
                if cached:
                    return cached
                return self._fallback_hold("Rate-limited: cached decision still valid")

        prompt = self._build_evaluation_prompt(position_context, market_snapshot)

        try:
            decision = self.llm.call_structured(
                system_prompt=CRYPTO_POSITION_MANAGER_SYSTEM_PROMPT,
                user_prompt=prompt,
                tool_definition=CRYPTO_POSITION_MANAGER_TOOL,
                max_tokens=1200
            )

            if "error" in decision or not decision:
                print(f"[BTC AI Position Agent] LLM call failed for Ticket #{ticket}: {decision.get('error', 'No response')}")
                return self._fallback_hold(f"LLM unavailable: {decision.get('error', 'No response')}")

            valid_actions = ["TAKE_PARTIAL_PROFIT", "MOVE_TO_BREAKEVEN", "TIGHTEN_TRAIL", "CLOSE_FULL", "HOLD_POSITION"]
            if decision.get("action") not in valid_actions:
                decision["action"] = "HOLD_POSITION"

            confidence = int(decision.get("confidence", 50))
            if confidence < 60 and decision["action"] != "HOLD_POSITION":
                print(f"[BTC AI Position Agent] Ticket #{ticket}: Decision '{decision['action']}' rejected (confidence {confidence}% < 60%). Holding.")
                decision["action"] = "HOLD_POSITION"
                decision["reasoning"] = f"Overridden due to low confidence ({confidence}%). " + decision.get("reasoning", "")

            if decision.get("new_sl_price") and position_context.get("sl", 0) > 0:
                self._validate_sl_direction(decision, position_context)

            self._last_eval_time[ticket] = now_ts
            self._last_decision_cache[ticket] = decision

            action = decision.get("action", "HOLD_POSITION")
            reasoning = decision.get("reasoning", "")[:120]
            print(f"[BTC AI Position Agent] Ticket #{ticket}: {action} (Confidence: {confidence}%) -- {reasoning}")

            return decision

        except Exception as e:
            print(f"[BTC AI Position Agent] Exception for Ticket #{ticket}: {e}")
            return self._fallback_hold(f"Exception: {str(e)}")

    def _build_evaluation_prompt(self, pos: Dict[str, Any], market: Dict[str, Any]) -> str:
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

        m5 = market.get("m5_structure", {})
        m15 = market.get("m15_structure", {})
        flow = market.get("tick_order_flow", {})
        cvd = market.get("volume_delta", {})
        regime = market.get("regime", {})

        prompt = f"""
OPEN BITCOIN (BTCUSD) POSITION -- EVALUATE NOW:

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

What should a pro Bitcoin trader do with this position RIGHT NOW?
Submit your decision using the `submit_crypto_position_management_decision` tool.
"""
        return prompt

    def _validate_sl_direction(self, decision: Dict[str, Any], pos: Dict[str, Any]):
        new_sl = float(decision.get("new_sl_price", 0.0))
        current_sl = float(pos.get("sl", 0.0))
        pos_type = pos.get("type", "BUY")

        if current_sl > 0 and new_sl > 0:
            if pos_type == "BUY" and new_sl < current_sl:
                decision["action"] = "HOLD_POSITION"
                decision["reasoning"] = f"SAFETY: Blocked attempt to widen SL from {current_sl} to {new_sl}."
            elif pos_type == "SELL" and new_sl > current_sl:
                decision["action"] = "HOLD_POSITION"
                decision["reasoning"] = f"SAFETY: Blocked attempt to widen SL from {current_sl} to {new_sl}."

    @staticmethod
    def _fallback_hold(reason: str) -> Dict[str, Any]:
        return {
            "action": "HOLD_POSITION",
            "urgency": "MONITOR",
            "confidence": 0,
            "reasoning": f"[FALLBACK] {reason}. Hard SL on MT5 still protects capital.",
            "is_fallback": True
        }

    def clear_position_cache(self, ticket: int):
        self._last_eval_time.pop(ticket, None)
        self._last_decision_cache.pop(ticket, None)
