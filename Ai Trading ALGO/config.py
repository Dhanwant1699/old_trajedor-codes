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

    # Trading Symbols & Identifiers (Dedicated Pure Gold XAUUSD)
    SYMBOL: str = os.getenv("TRADING_SYMBOL", "XAUUSD")
    SYMBOLS_RAW: str = os.getenv("TRADING_SYMBOLS", "XAUUSD")
    MAGIC_NUMBER: int = int(os.getenv("MAGIC_NUMBER", "777888"))
    MAGIC_NUMBERS: dict = None  # Populated in post_init or helper

    @property
    def SYMBOLS(self) -> list:
        raw = os.getenv("TRADING_SYMBOLS", self.SYMBOLS_RAW)
        return [s.strip().upper() for s in raw.split(",") if s.strip() and s.strip().upper() == "XAUUSD"] or ["XAUUSD"]


    # Risk Management Rules
    MAX_RISK_PER_TRADE_PCT: float = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "1.5"))
    MIN_RISK_REWARD_RATIO: float = float(os.getenv("MIN_RISK_REWARD_RATIO", "1.75"))
    MAX_DAILY_DRAWDOWN_PCT: float = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "3.0"))
    MAX_SPREAD_POINTS: float = float(os.getenv("MAX_SPREAD_POINTS", "12.0"))

    MAX_OPEN_TRADES: int = int(os.getenv("MAX_OPEN_TRADES", "1"))  # Strictly 1 single position only (Zero duplicate)
    MAX_LOT_SIZE: float = float(os.getenv("MAX_LOT_SIZE", "5.00"))  # Dynamic ceiling: allows AI to trade 0.20, 0.30, 0.50+ lots based on admin settings & equity
    MIN_LOT_SIZE: float = float(os.getenv("MIN_LOT_SIZE", "0.01"))  # Minimum micro lot

    # Professional Institutional Trailing Stop Manager
    TRAILING_STOP_ENABLED: bool = os.getenv("TRAILING_STOP_ENABLED", "true").lower() == "true"
    TRAILING_BE_TRIGGER_R: float = float(os.getenv("TRAILING_BE_TRIGGER_R", "0.5"))       # Move to BE early at +0.5R
    TRAILING_LOCK_TRIGGER_R: float = float(os.getenv("TRAILING_LOCK_TRIGGER_R", "0.8"))   # Lock profit (+0.4R) at +0.8R gain
    TRAILING_ATR_MULTIPLIER: float = float(os.getenv("TRAILING_ATR_MULTIPLIER", "1.2"))   # Trail SL dynamically by 1.2x ATR
    TRAILING_BUFFER_POINTS: float = float(os.getenv("TRAILING_BUFFER_POINTS", "6.0"))      # Breakeven profit buffer in points
    
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

    # Web Dashboard Port
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "1111"))




    # ============================================================
    # PHASE 1 - STAGED PIPELINE SETTINGS (non-negotiable gates)
    # ============================================================
    PIPELINE_MODE: str = os.getenv("PIPELINE_MODE", "staged")  # 'staged' = sequential gates | 'legacy' = parallel quorum
    LIVE_TRADING_ENABLED: bool = os.getenv("LIVE_TRADING_ENABLED", "true").lower() == "true"
    MIN_HARMONY_SCORE: int = int(os.getenv("MIN_HARMONY_SCORE", "70"))
    MIN_ORDERFLOW_LIFTERS_PCT: float = float(os.getenv("MIN_ORDERFLOW_LIFTERS_PCT", "55.0"))
    MIN_ORDERFLOW_HITTERS_PCT: float = float(os.getenv("MIN_ORDERFLOW_HITTERS_PCT", "55.0"))
    MAX_ENTRY_CHASE_ATR: float = float(os.getenv("MAX_ENTRY_CHASE_ATR", "0.30"))
    EARLY_CUT_ENABLED: bool = os.getenv("EARLY_CUT_ENABLED", "true").lower() == "true"
    COOLDOWN_MINUTES_AFTER_LOSS: int = int(os.getenv("COOLDOWN_MINUTES_AFTER_LOSS", "20"))
    NEWS_BLACKOUT_MINUTES: int = int(os.getenv("NEWS_BLACKOUT_MINUTES", "30"))
    NEWS_BLACKOUT_POST_MINUTES: int = int(os.getenv("NEWS_BLACKOUT_POST_MINUTES", "15"))
    ATR_ZONE_DISTANCE_MULTIPLIER: float = float(os.getenv("ATR_ZONE_DISTANCE_MULTIPLIER", "1.0"))


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

