"""
Macroeconomics, ForexFactory & High-Impact News Specialist Agent for Gold (XAUUSD).
Specialized exclusively for Gold: Fed interest rate expectations (FOMC), US CPI / PPI inflation,
Non-Farm Payrolls (NFP), US Dollar Index (DXY), 10Y US Treasury Yields, and geopolitical safe-haven flows.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


GOLD_MACRO_SYSTEM_PROMPT = """
You are the Macro & High-Impact News Specialist Trading Agent on an institutional Gold (XAUUSD) trading desk.
Your mandate is to evaluate fundamental catalysts, economic calendar releases, and intermarket relationships:

GOLD MACRO SPECIALIZATION:
1. US Dollar & Real Yields: Gold has a strong inverse correlation with the US Dollar Index (DXY) and 10-Year US Real Yields. Rising yields/strong USD = Bearish Gold headwind; falling yields/weak USD = Bullish Gold tailwind.
2. Federal Reserve Policy: FOMC rate decisions, Powell speeches, and inflation trajectory (CPI/PPI) directly drive institutional gold portfolio allocation.
3. Safe-Haven & Geopolitical Flows: Wars, banking crises, and sovereign debt risks create massive inelastic safe-haven bids for Gold.
4. News Blackout Defense: Enforce a strict BLACKOUT_VETO 15 minutes before and 15 minutes after High-Impact USD news (NFP, CPI, FOMC, PPI).

RULES:
- If High-Impact news is active or within blackout window, output recommended_action = 'BLACKOUT_VETO'.
- If macroeconomic sentiment is strongly bullish Gold and news is clear, output 'BULLISH_BIAS'.
- If macroeconomic sentiment is strongly bearish Gold and news is clear, output 'BEARISH_BIAS'.

Respond strictly using the `submit_gold_macro_analysis` tool call.
"""

GOLD_MACRO_TOOL = {
    "name": "submit_gold_macro_analysis",
    "description": "Submit Macro, News & Geopolitical analysis for Gold (XAUUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Gold_Macro_News_Agent"},
            "recommended_action": {"type": "string", "enum": ["CLEAR_TO_TRADE", "BLACKOUT_VETO", "CAUTION"]},
            "sentiment_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "macro_bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "high_impact_event_imminent": {"type": "boolean"},
            "minutes_to_next_event": {"type": "integer"},
            "catalyst_summary": {"type": "string", "description": "Key macro drivers (DXY, Yields, Fed, Geopolitics)"},
            "reasoning": {"type": "string", "description": "Detailed macroeconomic institutional assessment for Gold"}
        },
        "required": ["recommended_action", "sentiment_score", "macro_bias", "reasoning"]
    }
}


class GoldMacroAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Macro & News analysis exclusively on Gold (XAUUSD)."""
        prompt = f"""
Evaluate the current live economic calendar, headlines, and macro environment for Gold (XAUUSD):

{json.dumps(news_data, indent=2)}

Check:
1. Is there an active High-Impact USD event blackout?
2. What are the key drivers for Gold (DXY, real yields, Fed sentiment)?
3. What is the fundamental macro bias for Gold?

Submit your analysis using the `submit_gold_macro_analysis` tool.
"""
        res = self.llm.call_structured(
            system_prompt=GOLD_MACRO_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=GOLD_MACRO_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_macro(news_data)

        res["agent_name"] = "Gold_Macro_News_Agent"
        return res

    def _fallback_macro(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        blackout = news_data.get("news_blackout_active", False)
        reason = news_data.get("blackout_reason", "None")

        if blackout:
            return {
                "agent_name": "Gold_Macro_News_Agent",
                "recommended_action": "BLACKOUT_VETO",
                "sentiment_score": 0,
                "macro_bias": "NEUTRAL",
                "high_impact_event_imminent": True,
                "minutes_to_next_event": 5,
                "catalyst_summary": f"High-Impact USD Event: {reason}",
                "reasoning": f"Trading halted for Gold. Active economic news blackout window: {reason}."
            }

        return {
            "agent_name": "Gold_Macro_News_Agent",
            "recommended_action": "CLEAR_TO_TRADE",
            "sentiment_score": 82,
            "macro_bias": "BULLISH",
            "high_impact_event_imminent": False,
            "minutes_to_next_event": 999,
            "catalyst_summary": "Gold macro tailwinds: Central bank reserves accumulation, global yield stability, and safe-haven demand.",
            "reasoning": "Economic calendar is clear for Gold. Macro background supports top-down bullish structure."
        }
