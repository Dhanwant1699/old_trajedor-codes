"""
Claude AI Trading Brain for XAUUSD (Gold).
Uses Anthropic's Claude 3.7 / 3.5 Sonnet with Tool Calling to generate
institutional-grade trade decisions from technical and macro data.
"""

from typing import Dict, Any, Optional
import json
import anthropic
from config import CONFIG


SYSTEM_PROMPT = """
You are an elite Institutional Quantitative and Price Action Trader specializing in XAUUSD (Gold).
Your objective is to generate high-probability, risk-controlled trading decisions (BUY, SELL, HOLD, CLOSE_POSITION)
by fusing:
1. Multi-Timeframe Market Structure (M15 Execution, H1 Trend Context, H4 Macro).
2. Smart Money Concepts (SMC) & ICT:
   - Asian Session Liquidity Sweeps (Asian High/Low raided during London/NY open).
   - Fair Value Gaps (FVGs) and Order Block mitigation.
   - Break of Structure (BOS) vs Change of Character (CHoCH).
   - Dynamic ATR-based Stop Loss positioning (never enter without structural invalidation).
3. Real-Time Macro Feeds from ForexFactory.com & Investing.com:
   - ForexFactory Economic Calendar: High-Impact (Red Folder) USD events (CPI, FOMC, NFP, PPI, Powell speeches).
   - Investing.com Breaking Feeds: Gold/Commodities sentiment, DXY trends, Fed speaker comments, and geopolitical risk.
   - Inverse DXY correlation (Strong USD = Bearish Gold; Weak USD / Rate Cuts / Geopolitical Risk = Bullish Gold).
   - Strict News Blackout awareness (Do not enter new positions within 15 minutes of High-Impact USD Red Folder news).

TRADING RULES:
- High Selectivity: Only recommend BUY or SELL when there is clear multi-timeframe confluence (Minimum Confidence Score >= 75).
- If the market is consolidating, choppy, hovering near midpoint of a range, or approaching high-impact news, choose 'HOLD'.
- Every BUY/SELL MUST have a strictly calculated Stop Loss (SL) based on recent structural swing invalidation or FVG edge, plus Take Profit 1 (at least 1.5R) and Take Profit 2 (2.5R+).
- Never risk more than the specified risk percentage (default 1.0%).
- If an existing open trade has reached its invalidation or trend has fundamentally reversed, you may issue 'CLOSE_POSITION'.

You MUST respond using the `submit_trade_decision` tool call.
"""

TRADE_DECISION_TOOL = {
    "name": "submit_trade_decision",
    "description": "Submit the finalized trade decision for XAUUSD after analyzing technical market structure and news.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["BUY", "SELL", "HOLD", "CLOSE_POSITION"],
                "description": "Action to take for XAUUSD."
            },
            "confidence_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Confidence level (0-100). Minimum 75 required for BUY/SELL."
            },
            "market_bias": {
                "type": "string",
                "enum": ["BULLISH", "BEARISH", "NEUTRAL"],
                "description": "Overall structural bias for Gold."
            },
            "setup_name": {
                "type": "string",
                "description": "Name of the setup (e.g. 'Asian_Low_Sweep_M15_FVG_Retest', 'H1_BOS_Pullback', 'None/Consolidation')."
            },
            "entry_price": {
                "type": "number",
                "description": "Target entry price (or current market price)."
            },
            "stop_loss": {
                "type": "number",
                "description": "Exact Stop Loss price level beyond structural invalidation."
            },
            "take_profit_1": {
                "type": "number",
                "description": "First Take Profit target (1.5R to 2R)."
            },
            "take_profit_2": {
                "type": "number",
                "description": "Second Take Profit target (2.5R+ or opposing liquidity pool)."
            },
            "risk_percent": {
                "type": "number",
                "description": "Risk percentage of account equity (default 1.0)."
            },
            "close_ticket": {
                "type": "integer",
                "description": "If action is CLOSE_POSITION, the MT5 ticket number to close."
            },
            "technical_confluence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific technical confluences supporting this setup."
            },
            "macro_news_impact": {
                "type": "string",
                "description": "Assessment of current USD/yield news sentiment on Gold."
            },
            "detailed_reasoning": {
                "type": "string",
                "description": "Detailed explanation of why this decision was made."
            }
        },
        "required": ["action", "confidence_score", "market_bias", "detailed_reasoning"]
    }
}


class ClaudeTraderAgent:
    """
    Interfaces with Anthropic API to analyze market state and generate trade signals.
    """
    def __init__(self, api_key: str = CONFIG.ANTHROPIC_API_KEY, model: str = CONFIG.CLAUDE_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = None
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_and_decide(self, market_data: Dict[str, Any], news_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends the complete market state and news context to Claude and parses the structured decision.
        """
        if not self.client:
            return {
                "action": "HOLD",
                "confidence_score": 0,
                "market_bias": "NEUTRAL",
                "detailed_reasoning": "Anthropic API key is not configured in .env. Please set ANTHROPIC_API_KEY."
            }

        # Build prompt payload
        user_message = f"""
Analyze the current live XAUUSD (Gold) market data and news sentiment below to make a trading decision:

=== MARKET CONTEXT & STRUCTURE ===
{json.dumps(market_data, indent=2)}

=== NEWS & MACRO SENTIMENT ===
{json.dumps(news_data, indent=2)}

Evaluate:
1. Is there an active News Blackout or high-impact event imminent?
2. What is the H4/H1 macro trend alignment?
3. Has Asian High or Low liquidity been raided?
4. Are there unmitigated M15 Fair Value Gaps (FVGs) or order blocks offering high Risk:Reward entries?
5. Is the Risk-to-Reward ratio at least 1:{CONFIG.MIN_RISK_REWARD_RATIO}?

Submit your decision using the `submit_trade_decision` tool.
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=CONFIG.MAX_TOKENS,
                temperature=CONFIG.CLAUDE_TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                tools=[TRADE_DECISION_TOOL],
                tool_choice={"type": "tool", "name": "submit_trade_decision"}
            )

            # Parse tool call response
            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_trade_decision":
                    return block.input

            # Fallback if no tool use was returned
            return {
                "action": "HOLD",
                "confidence_score": 0,
                "market_bias": "NEUTRAL",
                "detailed_reasoning": "Claude did not return a structured tool call. Holding position."
            }

        except Exception as e:
            print(f"[ClaudeTrader] API Error: {e}")
            return {
                "action": "HOLD",
                "confidence_score": 0,
                "market_bias": "NEUTRAL",
                "detailed_reasoning": f"Claude API error: {str(e)}"
            }
