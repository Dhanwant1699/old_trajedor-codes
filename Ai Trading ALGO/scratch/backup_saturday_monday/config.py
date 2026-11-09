"""
Configuration module for Claude XAUUSD AI Trader.
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file from project root if present
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


@dataclass(frozen=True)
class TradingConfig:
    # Multi-Provider Selection: "anthropic", "nvidia", "groq", or "ollama"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "anthropic").lower()

    # Anthropic Claude API (Supports: claude-sonnet-5, claude-3-7-sonnet-20250219, claude-haiku-4-5)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

    # NVIDIA NIM Cloud (Free Tier from build.nvidia.com)
    # Active Models: "meta/llama-3.2-11b-vision-instruct" (fast, multilingual: Hindi/Marathi/English), "deepseek-ai/deepseek-v4-flash-0731"
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")

    # Groq Cloud API (Free Tier from console.groq.com)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # General AI Parameters
    CLAUDE_TEMPERATURE: float = float(os.getenv("CLAUDE_TEMPERATURE", "0.2"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2048"))

    # MT5 Broker Settings
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0")) if os.getenv("MT5_LOGIN") else 0
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_PATH: str = os.getenv("MT5_PATH", "")

    # Trading Symbols & Identifiers (Multi-Asset: Gold & Bitcoin)
    SYMBOL: str = os.getenv("TRADING_SYMBOL", "XAUUSD")
    SYMBOLS_RAW: str = os.getenv("TRADING_SYMBOLS", "XAUUSD,BTCUSD")
    MAGIC_NUMBER: int = int(os.getenv("MAGIC_NUMBER", "777888"))
    MAGIC_NUMBERS: dict = None  # Populated in post_init or helper

    @property
    def SYMBOLS(self) -> list:
        # Only XAUUSD - no Bitcoin
        return ["XAUUSD"]


    # Risk Management Rules
    MAX_RISK_PER_TRADE_PCT: float = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "1.5"))
    MAX_PORTFOLIO_AGGREGATE_RISK_PCT: float = float(os.getenv("MAX_PORTFOLIO_AGGREGATE_RISK_PCT", "5.0"))  # Hard 5% max risk cap across ALL open AI trades combined
    MIN_RISK_REWARD_RATIO: float = float(os.getenv("MIN_RISK_REWARD_RATIO", "1.5"))
    MAX_DAILY_DRAWDOWN_PCT: float = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "100.0"))
    MAX_SPREAD_POINTS: float = float(os.getenv("MAX_SPREAD_POINTS", "45.0"))
    BTC_MAX_SPREAD_POINTS: float = float(os.getenv("BTC_MAX_SPREAD_POINTS", "2500.0"))

    MAX_OPEN_TRADES: int = int(os.getenv("MAX_OPEN_TRADES", "1"))  # Strictly 1 single position only (Zero duplicate)
    MAX_LOT_SIZE: float = float(os.getenv("MAX_LOT_SIZE", "0.10"))  # Hard max limit for Gold: 0.10 lots
    BTC_MAX_LOT_SIZE: float = float(os.getenv("BTC_MAX_LOT_SIZE", "0.50"))  # Hard max limit for Bitcoin: up to 0.50 lots
    MIN_LOT_SIZE: float = float(os.getenv("MIN_LOT_SIZE", "0.01"))  # Minimum micro lot

    # Professional Institutional Trailing Stop Manager
    TRAILING_STOP_ENABLED: bool = os.getenv("TRAILING_STOP_ENABLED", "true").lower() == "true"
    TRAILING_BE_TRIGGER_R: float = float(os.getenv("TRAILING_BE_TRIGGER_R", "0.65"))       # Gold: Move to BE at +0.65R
    TRAILING_LOCK_TRIGGER_R: float = float(os.getenv("TRAILING_LOCK_TRIGGER_R", "0.80"))   # Gold: Lock profit (+0.4R) at +0.8R gain
    TRAILING_ATR_MULTIPLIER: float = float(os.getenv("TRAILING_ATR_MULTIPLIER", "1.35"))   # Gold: Trail SL dynamically by 1.35x ATR
    TRAILING_BUFFER_POINTS: float = float(os.getenv("TRAILING_BUFFER_POINTS", "6.0"))      # Gold: Breakeven profit buffer in points (0.40 - 0.60)

    # Bitcoin (BTCUSD) Dedicated Natural Volatility Trailing & Breakeven Parameters
    BTC_TRAILING_BE_TRIGGER_R: float = float(os.getenv("BTC_TRAILING_BE_TRIGGER_R", "1.25"))       # BTC: Move to BE only after +1.25R (breathes through breakout retests)
    BTC_TRAILING_LOCK_TRIGGER_R: float = float(os.getenv("BTC_TRAILING_LOCK_TRIGGER_R", "1.75"))   # BTC: Lock profit (+0.75R) at +1.75R gain
    BTC_TRAILING_ATR_MULTIPLIER: float = float(os.getenv("BTC_TRAILING_ATR_MULTIPLIER", "2.75"))   # BTC: Wide 2.75x ATR trail to capture $3k-$5k mega trends
    BTC_TRAILING_BUFFER_DOLLARS: float = float(os.getenv("BTC_TRAILING_BUFFER_DOLLARS", "75.0"))   # BTC: Explicit $75.00 dollar buffer (prevents $0.35 micro-wick shakeouts)
    BTC_MIN_TRAIL_DISTANCE: float = float(os.getenv("BTC_MIN_TRAIL_DISTANCE", "950.0"))            # BTC: Minimum $950.00 trailing buffer
    BTC_MIN_TRAIL_STEP: float = float(os.getenv("BTC_MIN_TRAIL_STEP", "50.0"))                      # BTC: $50.00 ratchet step
    
    # Partial Take Profit & Breakeven
    MOVE_SL_TO_BE_AT_TP1: bool = os.getenv("MOVE_SL_TO_BE_AT_TP1", "true").lower() == "true"
    CLOSE_PARTIAL_PCT_AT_TP1: float = float(os.getenv("CLOSE_PARTIAL_PCT_AT_TP1", "50.0"))

    # Timeframes & Precision 5-Minute Candle Confirmation
    EXECUTION_TIMEFRAME: str = os.getenv("EXECUTION_TIMEFRAME", "M5")      # 5-min execution timeframe
    TRIGGER_TIMEFRAME: str = os.getenv("TRIGGER_TIMEFRAME", "M5")          # Precision entry timing on 5-min candle confirmation
    CONTEXT_TIMEFRAME: str = os.getenv("CONTEXT_TIMEFRAME", "H1")
    MACRO_TIMEFRAME: str = os.getenv("MACRO_TIMEFRAME", "H4")

    # CRO 5-Minute Agent Deliberation Cadence (CRO asks each agent's opinion every 5-min candle close)
    COUNCIL_DELIBERATION_INTERVAL_SECONDS: int = int(os.getenv("COUNCIL_DELIBERATION_INTERVAL_SECONDS", "300"))

    # Institutional Entry Tolerance Band (±1.0 pt tolerance zone)
    SNIPER_M5_TRIGGER_ENABLED: bool = os.getenv("SNIPER_M5_TRIGGER_ENABLED", "true").lower() == "true"
    ENTRY_TOLERANCE_POINTS: float = float(os.getenv("ENTRY_TOLERANCE_POINTS", "1.0"))          # Gold: e.g. ±1.0 pt buffer (4037.5 - 4039.5)
    BTC_ENTRY_TOLERANCE_POINTS: float = float(os.getenv("BTC_ENTRY_TOLERANCE_POINTS", "35.0"))  # BTC: ±$35.0 buffer

    # News Filter
    ENABLE_NEWS_FILTER: bool = os.getenv("ENABLE_NEWS_FILTER", "true").lower() == "true"
    NEWS_BLACKOUT_MINUTES: int = int(os.getenv("NEWS_BLACKOUT_MINUTES", "15"))

    # Execution Loop Interval (seconds)
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "1"))  # 1-second agile loop for tick-by-tick sniper observation & instant execution



# Global Config Instance
CONFIG = TradingConfig()


def get_model_api_kwargs(model: str = CONFIG.CLAUDE_MODEL, max_tokens: int = CONFIG.MAX_TOKENS) -> dict:
    """Helper to dynamically configure API parameters across Claude versions (Sonnet 5, 3.7, Haiku)."""
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
    }
    # In Sonnet 5 / Fable, temperature is handled via adaptive thinking
    if "sonnet-5" not in model.lower() and "fable" not in model.lower() and "opus-5" not in model.lower():
        kwargs["temperature"] = CONFIG.CLAUDE_TEMPERATURE
    return kwargs

