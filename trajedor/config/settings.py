"""
TRAJEDOR - Master Configuration & Global Hyperparameters.
Defines risk caps, execution thresholds, and account routing.
"""

import os
import json
from dataclasses import dataclass
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
UI_DIR = os.path.join(BASE_DIR, "ui")
ACCOUNTS_FILE = os.path.join(CONFIG_DIR, "accounts.json")


@dataclass
class TrajedorSettings:
    SYSTEM_NAME: str = "TRAJEDOR JARVIS MARK-85"
    VERSION: str = "2.0.0-EVOLUTIONARY"
    PRIMARY_SYMBOL: str = "XAUUSD"
    PORT: int = 1111
    MAGIC_NUMBER: int = 888999  # Pure Trajedor AI Magic Number (strictly separates from manual trades)

    # Risk & Defense Hyperparameters
    MAX_RISK_PER_TRADE_PCT: float = 1.0       # Max 1.0% account risk per trade
    DAILY_PROFIT_TARGET_USD: float = 150.0   # Daily profit lock threshold
    DAILY_MAX_DRAWDOWN_USD: float = 60.0     # Daily circuit breaker
    HARD_LOT_CAP: float = 0.10               # Absolute hard lot cap

    # Trade Doctor Active Defense Settings
    EARLY_CUT_R_THRESHOLD: float = -0.65     # Thesis invalidation cut (at least 4.0 pts adverse displacement)
    BREAKEVEN_R_TRIGGER: float = 0.75        # Lock stop-loss to entry after +0.75R expansion
    PARTIAL_DERISK_PCT: float = 50.0         # De-risk 50% on structure warning

    # Multi-Timeframe Thresholds
    TIMEFRAMES: tuple = ("1Y", "6M", "1M", "1W", "D1", "H4", "H1", "M15", "M5")


SETTINGS = TrajedorSettings()


def load_accounts_config() -> Dict[str, Any]:
    """Loads configured MT5 accounts from accounts.json."""
    accounts_file = os.path.join(CONFIG_DIR, "accounts.json")
    if os.path.exists(accounts_file):
        try:
            with open(accounts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Return empty dict if no configuration exists; discovered dynamically
    return {}


def save_accounts_config(accounts_data: Dict[str, Any]) -> bool:
    """Saves updated accounts configuration."""
    accounts_file = os.path.join(CONFIG_DIR, "accounts.json")
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump(accounts_data, f, indent=2)
        return True
    except Exception as e:
        print(f"[TrajedorConfig] Error saving accounts: {e}")
        return False
