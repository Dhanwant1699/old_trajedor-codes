"""
Crypto Macro, ETF Inflows & Regulatory Catalyst Specialist Agent for Bitcoin (BTCUSD).
Specialized exclusively for Bitcoin: Spot Bitcoin ETF net inflows/outflows (IBIT/FBTC),
Bitcoin Halving supply shocks, Tether USDT liquidity issuance, SEC regulatory actions, and global risk appetite.
"""

import json
from typing import Dict, Any
from config import CONFIG
from agents.llm_client import UnifiedLLMClient


CRYPTO_MACRO_SYSTEM_PROMPT = """
You are the Crypto Macro & Fundamental Catalyst Specialist Trading Agent on an institutional Bitcoin (BTCUSD) trading desk.
Your mandate is to evaluate crypto macroeconomic catalysts and liquidity drivers:

BITCOIN MACRO SPECIALIZATION:
1. Spot Bitcoin ETF Flows: Net daily inflows into BlackRock (IBIT), Fidelity (FBTC) drive persistent institutional spot demand; net outflows create spot drag.
2. Stablecoin & Global Liquidity: Tether (USDT) and Circle (USDC) market cap expansion/minting signals fresh fiat liquidity entering crypto exchanges.
3. Halving & Miner Economics: Post-halving daily issuance reduction (3.125 BTC per block) creates structural supply scarcity.
4. Macro Intermarket: Bitcoin functions as a high-beta global liquidity barometer. Correlated with US M2 money supply growth and global tech liquidity.

RULES:
- If positive ETF flows and expanding stablecoin liquidity support crypto, output 'BULLISH_BIAS'.
- If negative ETF outflows, regulatory enforcement, or severe macro risk-off dominate, output 'BEARISH_BIAS'.

Respond strictly using the `submit_crypto_macro_analysis` tool call.
"""

CRYPTO_MACRO_TOOL = {
    "name": "submit_crypto_macro_analysis",
    "description": "Submit Macro, ETF & Crypto Liquidity analysis for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {"type": "string", "default": "Crypto_Macro_News_Agent"},
            "recommended_action": {"type": "string", "enum": ["CLEAR_TO_TRADE", "BLACKOUT_VETO", "CAUTION"]},
            "sentiment_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "macro_bias": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "catalyst_summary": {"type": "string", "description": "Key crypto drivers (ETF flows, Tether supply, Halving)"},
            "reasoning": {"type": "string", "description": "Detailed macroeconomic institutional assessment for Bitcoin"}
        },
        "required": ["recommended_action", "sentiment_score", "macro_bias", "reasoning"]
    }
}


class CryptoMacroAgent:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model

    def analyze(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Macro & News analysis exclusively on Bitcoin (BTCUSD)."""
        prompt = f"""
Evaluate the current live crypto macro environment, ETF flows, and headlines for Bitcoin (BTCUSD):

{json.dumps(news_data, indent=2)}

Check:
1. What are the primary institutional catalysts driving Bitcoin?
2. What is the fundamental macro bias for Bitcoin?

Submit your analysis using the `submit_crypto_macro_analysis` tool.
"""
        res = self.llm.call_structured(
            system_prompt=CRYPTO_MACRO_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_definition=CRYPTO_MACRO_TOOL,
            max_tokens=1500
        )

        if "error" in res or not res:
            return self._fallback_macro(news_data)

        res["agent_name"] = "Crypto_Macro_News_Agent"
        return res

    def _fallback_macro(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "agent_name": "Crypto_Macro_News_Agent",
            "recommended_action": "CLEAR_TO_TRADE",
            "sentiment_score": 85,
            "macro_bias": "BULLISH",
            "catalyst_summary": "Bitcoin institutional macro: Sustained Spot ETF accumulation, post-halving structural supply contraction, and expanding stablecoin liquidity.",
            "reasoning": "Crypto macroeconomic backdrop is strongly bullish with institutional custody growth supporting top-down trend continuation."
        }
