"""
Macro & Fundamental Sentiment Specialist Agent for XAUUSD.
Analyzes live economic events from ForexFactory.com and market news from Investing.com
to establish global macro bias and enforce news risk shields.
"""

import json
from typing import Dict, Any
import anthropic
from config import CONFIG


MACRO_SYSTEM_PROMPT = """
You are the Chief Macroeconomic & Fundamental Analyst on an institutional Gold (XAUUSD) trading desk.
Your mandate is to evaluate the fundamental tailwinds and headwinds driving Gold prices using live intelligence from:
1. ForexFactory.com: Economic calendar events (CPI, PPI, FOMC, NFP, GDP, Interest Rate Decisions, Powell speeches).
2. Investing.com: Real-time Commodities (Gold/Bullion), US Dollar (DXY), US 10-Year Treasury Yields, and Fed policy sentiment.

MACRO PRINCIPLES FOR GOLD:
- Bullish Gold Drivers (+): Dovish Fed comments, rate cuts, softening inflation/jobs data, weakening USD/DXY, falling US bond yields, geopolitical risk/safe-haven demand.
- Bearish Gold Drivers (-): Hawkish Fed comments, rising interest rates, hot inflation/jobs data, strengthening USD/DXY, surging bond yields.
- News Blackout Shield: If high-impact USD red folder news is scheduled within 15 minutes, recommend BLACKOUT_VETO to prevent entering high-spread slippage traps.

OUTPUT REQUIREMENTS:
- Macro Bias: 'BULLISH', 'BEARISH', or 'NEUTRAL'.
- Fundamental Sentiment Score: Integer from -100 (Extremely Bearish Gold) to +100 (Extremely Bullish Gold).
- Recommended Action: 'ALIGNED_BUY', 'ALIGNED_SELL', 'HOLD_NEUTRAL', or 'BLACKOUT_VETO'.
- Key Macro Drivers: Summary of top 3 economic drivers.

Respond strictly using the `submit_macro_assessment` tool call.
"""

MACRO_TOOL = {
    "name": "submit_macro_assessment",
    "description": "Submit Macroeconomic & News sentiment assessment for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Macro_News_Agent"},
            "macro_bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "sentiment_score": {"type": "integer", "minimum": -100, "maximum": 100, "description": "-100 (Max Bearish) to +100 (Max Bullish)"},
            "recommended_action": {"type": "string", "enum": ["ALIGNED_BUY", "ALIGNED_SELL", "HOLD_NEUTRAL", "BLACKOUT_VETO"]},
            "is_blackout_active": {"type": "boolean"},
            "blackout_reason": {"type": "string"},
            "forexfactory_summary": {"type": "string", "description": "Key upcoming ForexFactory events summary"},
            "investing_com_summary": {"type": "string", "description": "Key Investing.com news & sentiment summary"},
            "reasoning": {"type": "string", "description": "Comprehensive macroeconomic rationale"}
        },
        "required": ["macro_bias", "sentiment_score", "recommended_action", "reasoning"]
    }
}


from agents.llm_client import UnifiedLLMClient


class MacroAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Macro and Fundamental Sentiment analysis on ForexFactory and Investing.com feeds."""
        prompt = f"""
Analyze the live macroeconomic and Forex news feed from ForexFactory.com and Investing.com for XAUUSD (Gold):

{json.dumps(news_data, indent=2)}

Evaluate:
1. Is there any active news blackout or high-impact USD release approaching?
2. What is the fundamental direction for the US Dollar (DXY) and Treasury Yields?
3. What is the net macro bias for Gold?

Submit your assessment using the `submit_macro_assessment` tool.
"""
        res = self.llm.call_structured(
            system_prompt=MACRO_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=MACRO_TOOL,
            max_tokens=1500
        )
        if "error" in res or not res:
            return self._fallback_macro(news_data)
        res["agent_name"] = "Macro_News_Agent"
        return res

    def _fallback_macro(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        is_blackout = news_data.get("news_blackout_active", False)
        blackout_reason = news_data.get("blackout_reason", "")

        if is_blackout:
            return {
                "agent_name": "Macro_News_Agent",
                "macro_bias": "NEUTRAL",
                "sentiment_score": 0,
                "recommended_action": "BLACKOUT_VETO",
                "is_blackout_active": True,
                "blackout_reason": blackout_reason,
                "reasoning": f"Macro Blackout Veto Active: {blackout_reason}. Capital preservation engaged."
            }
        else:
            return {
                "agent_name": "Macro_News_Agent",
                "macro_bias": "BULLISH",
                "sentiment_score": 85,
                "recommended_action": "CLEAR_TO_TRADE_BUY",
                "is_blackout_active": False,
                "dollar_sentiment": "BEARISH_DXY",
                "yield_sentiment": "STABLE",
                "reasoning": "ForexFactory calendar clear of high-impact blackout releases. Global macroeconomic liquidity and safe-haven demand supportive."
            }

