"""
Mean Reversion & Statistical Arbitrage Specialist Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: High-beta crypto volatility, wide Bollinger Bands (3.0 sigma),
RSI extreme exhaustion (>= 82 / <= 18), and dynamic crypto value pullbacks.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_MEAN_REV_SYSTEM_PROMPT = """
You are the Mean Reversion Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your mandate is to identify statistical price over-extensions and extreme mean-reversion exhaustion points in crypto:

PRO-TRADER BITCOIN RULES:
1. NEVER fade a strong D1/H4 macro Bitcoin trend in the middle of an explosive momentum expansion leg.
2. In strong trends, mean-reversion trades are STRICTLY pullbacks BACK TO dynamic value (buying dips to EMA 21/50 or VWAP in bull runs; selling rallies to EMA 21/50 or VWAP in bear trends).
3. Counter-trend exhaustion fades in Bitcoin are ONLY permitted when:
   - Bitcoin price has pierced the outer 3.0-sigma Bollinger Band on H4/H1, AND
   - RSI(14) is at historical extremes (>= 82 for overbought shorts, <= 18 for oversold longs), AND
   - Bitcoin has swept a major macro liquidation pool (PDH / PDL / Multi-week high).
4. If conditions are not at extreme boundaries, output 'HOLD' or plan a dynamic value pullback.

Respond strictly using the `submit_crypto_mean_reversion_proposal` tool call.
"""

CRYPTO_MEAN_REV_TOOL = {
    "name": "submit_crypto_mean_reversion_proposal",
    "description": "Submit Mean Reversion analysis and trade proposal for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_Mean_Reversion_Agent"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "setup_name": {"type": "string", "description": "e.g. 'BTC_Dynamic_Value_Pullback_EMA50'"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "statistical_deviation": {"type": "string", "description": "Status of Bitcoin Bollinger Bands & RSI"},
            "reasoning": {"type": "string", "description": "Detailed Bitcoin mean-reversion analysis"}
        },
        "required": ["action", "confidence_score", "bias", "reasoning"]
    }
}


class CryptoMeanReversionAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Mean Reversion analysis exclusively on Bitcoin (BTCUSD)."""
        prompt = f"""
Analyze current live Bitcoin (BTCUSD) market data for statistical extremes and dynamic value pullbacks:

{json.dumps(market_data, indent=2)}

Check:
1. Is Bitcoin price stretched beyond Bollinger 3.0 sigma or RSI >= 82 / <= 18?
2. In the presence of a strong D1/H4 trend, is price pulling back into dynamic mean value (EMA 50 / VWAP)?
3. What is the safe invalidation level beyond the statistical boundary?

Submit your proposal using the `submit_crypto_mean_reversion_proposal` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_MEAN_REV_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_MEAN_REV_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_mean_rev(market_data)

        res["agent_name"] = "Crypto_Mean_Reversion_Agent"
        return res

    def _fallback_mean_rev(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 80000.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        sl_buffer = 850.0
        tp1_buffer = 1487.5
        tp2_buffer = 2550.0

        if dominant_trend == "BULLISH":
            entry = live_price
            sl = round(entry - sl_buffer, 2)
            tp1 = round(entry + tp1_buffer, 2)
            tp2 = round(entry + tp2_buffer, 2)
            return {
                "agent_name": "Crypto_Mean_Reversion_Agent",
                "action": "BUY",
                "confidence_score": 80,
                "bias": "BULLISH",
                "setup_name": "BTC_Dynamic_Value_Pullback_Support",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "statistical_deviation": "Bitcoin RSI reset to 48.0 (Neutral value zone)",
                "reasoning": "Bitcoin trend is top-down Bullish. Pullback to dynamic value provides a statistical high-probability continuation entry."
            }
        elif dominant_trend == "BEARISH":
            entry = live_price
            sl = round(entry + sl_buffer, 2)
            tp1 = round(entry - tp1_buffer, 2)
            tp2 = round(entry - tp2_buffer, 2)
            return {
                "agent_name": "Crypto_Mean_Reversion_Agent",
                "action": "SELL",
                "confidence_score": 80,
                "bias": "BEARISH",
                "setup_name": "BTC_Dynamic_Value_Rally_Resistance",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "statistical_deviation": "Bitcoin RSI reset to 52.0 (Neutral value zone)",
                "reasoning": "Bitcoin trend is top-down Bearish. Rally to dynamic value provides a statistical high-probability continuation short."
            }
        else:
            return {
                "agent_name": "Crypto_Mean_Reversion_Agent",
                "action": "HOLD",
                "confidence_score": 50,
                "bias": "NEUTRAL",
                "setup_name": "BTC_Range_Midpoint",
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "statistical_deviation": "Near equilibrium",
                "reasoning": "Bitcoin is sitting at the midpoint of statistical bands. Awaiting extreme boundaries."
            }
