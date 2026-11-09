"""
Trend Following & Momentum Specialist Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: High-beta crypto trend continuation across D1/H4/H1 EMA 50/200 stacks,
momentum acceleration, and deep crypto pullback dynamics.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_TREND_SYSTEM_PROMPT = """
You are the Trend & Momentum Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your mandate is to trade strictly in the direction of dominant Top-Down Bitcoin Trends (D1 -> H4 -> H1 -> M15):
1. Macro Trend Stack (D1 / H4): Position of Bitcoin price relative to EMA 50 & EMA 200, slope of EMA ribbon, and long-term crypto momentum.
2. Intermediate Trend (H1): Directional structure of EMA 9/21/50 clouds confirming Bitcoin super-trend continuation.
3. Pullback Entry Execution (M15): Buying Bitcoin pullbacks into dynamic EMA 21 / EMA 50 support in bull runs; selling rallies into EMA 21 / EMA 50 resistance in bear trends.
4. Momentum Thrust (M5): Fast momentum alignment confirming the Bitcoin continuation leg.

PRO-TRADER BITCOIN RULES:
- NEVER fight the dominant D1 and H4 Bitcoin macro trend.
- If Bitcoin D1 is Bullish and H4 is Bullish, look strictly for H1/M15 pullback BUY opportunities.
- If Bitcoin D1 is Bearish and H4 is Bearish, look strictly for H1/M15 rally SELL opportunities.
- If timeframes are conflicted or Bitcoin is trapped in low-liquidity weekend compression, output 'HOLD'.
- Place Stop Loss below dynamic trend support (EMA 50 or swing low + $500-$1,500 buffer).
- Target at least 1.75R (TP1) to 3.0R (TP2) trailing trend targets.

Respond strictly using the `submit_crypto_trend_proposal` tool call.
"""

CRYPTO_TREND_TOOL = {
    "name": "submit_crypto_trend_proposal",
    "description": "Submit Trend Following analysis and trade proposal for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_Trend_Momentum_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'BTC_H1_H4_Bullish_Trend_M15_EMA50_Pullback'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "timeframe_alignment": {"type": "string", "description": "Status of Bitcoin H4, H1, M15 alignment"},
            "reasoning": {"type": "string", "description": "Detailed Bitcoin trend & momentum analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class CryptoTrendAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Trend & Momentum analysis exclusively on Bitcoin (BTCUSD)."""
        prompt = f"""
Analyze the current live Bitcoin (BTCUSD) market data across D1, H4, H1, M15, M5:

{json.dumps(market_data, indent=2)}

Check:
1. Is Bitcoin H4 macro trend aligned with H1 intermediate trend?
2. Where is current Bitcoin price relative to M15 EMA 50 and EMA 200?
3. Is price pulling back into high-probability trend continuation support/resistance?
4. What is the ATR volatility state for Bitcoin?

Submit your proposal using the `submit_crypto_trend_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_TREND_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_TREND_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_trend(market_data)

        res["agent_name"] = "Crypto_Trend_Momentum_Agent"
        return res

    def _fallback_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 80000.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        d1_bias = top_down.get("d1_bias", "BULLISH")
        h4_bias = top_down.get("h4_bias", "BULLISH")
        h1_bias = top_down.get("h1_bias", "BULLISH")
        m15_bias = top_down.get("m15_bias", "BULLISH")
        
        sl_buffer = 850.0
        tp1_buffer = 1487.5
        tp2_buffer = 2550.0

        if d1_bias == "BULLISH" and h4_bias == "BULLISH":
            entry = live_price
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Crypto_Trend_Momentum_Agent",
                "action": "BUY",
                "confidence_score": 88,
                "bias": "BULLISH",
                "setup_name": "BTC_TopDown_Macro_Trend_Continuation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "timeframe_alignment": f"D1: {d1_bias} | H4: {h4_bias} | H1: {h1_bias} | M15: {m15_bias}",
                "reasoning": f"Bitcoin Top-Down Bullish alignment (D1/H4). Treating lower timeframe consolidation as high-probability pullback buy."
            }
        elif d1_bias == "BEARISH" and h4_bias == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Crypto_Trend_Momentum_Agent",
                "action": "SELL",
                "confidence_score": 88,
                "bias": "BEARISH",
                "setup_name": "BTC_TopDown_Macro_Trend_Continuation",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "timeframe_alignment": f"D1: {d1_bias} | H4: {h4_bias} | H1: {h1_bias} | M15: {m15_bias}",
                "reasoning": f"Bitcoin Top-Down Bearish alignment (D1/H4). Treating lower timeframe bounces as high-probability rally sell."
            }
        else:
            return {
                "agent_name": "Crypto_Trend_Momentum_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "BTC_Timeframe_Conflict",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "timeframe_alignment": f"D1: {d1_bias} | H4: {h4_bias} | H1: {h1_bias}",
                "reasoning": "Bitcoin macro timeframes are conflicted. Standing aside until alignment clears."
            }
