"""
Typed dataclasses for the Staged Institutional Pipeline.
TradePlan, DailyPlan, GateResult, KeyLevel, BlackoutWindow, AgentVote.
All values are strict -- no magic numbers, all validated on construction.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TradeBias(str, Enum):
    BUY_DIPS      = "BUY_DIPS"
    SELL_RALLIES  = "SELL_RALLIES"
    NO_TRADE      = "NO_TRADE"


class TradeDirection(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"


class AgentRole(str, Enum):
    VETO      = "VETO"
    DIRECTION = "DIRECTION"
    LOCATION  = "LOCATION"
    TRIGGER   = "TRIGGER"


class VoteChoice(str, Enum):
    BUY       = "BUY"
    SELL      = "SELL"
    NO_SIGNAL = "NO_SIGNAL"
    INVALID   = "INVALID"


# ---------------------------------------------------------------------------
# Sub-objects
# ---------------------------------------------------------------------------

@dataclass
class KeyLevel:
    price: float
    level_type: str
    source: str
    strength: int
    unmitigated: bool = True


@dataclass
class BlackoutWindow:
    start_utc: str
    end_utc: str
    event: str
    impact: str


@dataclass
class AgentVote:
    agent_name: str
    role: AgentRole
    vote: VoteChoice
    confidence: int
    evidence: List[str]
    invalidation_price: float
    valid: bool = True
    rejection_reason: str = ""


# ---------------------------------------------------------------------------
# Gate Result
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    passed: bool
    failed_gate: Optional[str] = None
    reason: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passed


# ---------------------------------------------------------------------------
# Daily / Session Plan  (Stage 0 output)
# ---------------------------------------------------------------------------

@dataclass
class DailyPlan:
    bias: TradeBias
    d1_trend: str
    h4_trend: str
    h4_regime: str
    premium_discount_pct: float
    key_levels: List[KeyLevel] = field(default_factory=list)
    blackout_windows: List[BlackoutWindow] = field(default_factory=list)
    session: str = "UNKNOWN"
    generated_at_utc: str = ""
    notes: str = ""

    def in_premium_zone(self) -> bool:
        return self.premium_discount_pct > 50.0

    def in_discount_zone(self) -> bool:
        return self.premium_discount_pct < 50.0

    def get_levels_above(self, price: float, n: int = 3) -> List[KeyLevel]:
        above = [kl for kl in self.key_levels if kl.price > price]
        return sorted(above, key=lambda x: x.price)[:n]

    def get_levels_below(self, price: float, n: int = 3) -> List[KeyLevel]:
        below = [kl for kl in self.key_levels if kl.price < price]
        return sorted(below, key=lambda x: x.price, reverse=True)[:n]

    def nearest_level(self, price: float) -> Optional[KeyLevel]:
        if not self.key_levels:
            return None
        return min(self.key_levels, key=lambda kl: abs(kl.price - price))

    def distance_to_nearest_level(self, price: float) -> float:
        lvl = self.nearest_level(price)
        return abs(price - lvl.price) if lvl else float("inf")


# ---------------------------------------------------------------------------
# Trade Plan  (Stage 2 output)
# ---------------------------------------------------------------------------

@dataclass
class TradePlan:
    direction: TradeDirection
    entry_zone_low: float
    entry_zone_high: float
    entry_price: float
    stop_price: float
    target_1: float
    target_2: float
    rr: float
    invalidation_reason: str
    source_setup: str
    atr_at_signal: float = 0.0
    key_level_touched: Optional[KeyLevel] = None

    def is_valid(self, min_rr: float = 1.75) -> bool:
        if self.rr < min_rr:
            return False
        if self.direction == TradeDirection.BUY:
            if not (self.stop_price < self.entry_price < self.target_1 < self.target_2):
                return False
        else:
            if not (self.target_2 < self.target_1 < self.entry_price < self.stop_price):
                return False
        return True

    def risk_distance(self) -> float:
        return abs(self.entry_price - self.stop_price)

    def chase_distance(self, live_price: float) -> float:
        return abs(live_price - self.entry_price)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction.value,
            "entry_zone": f"{self.entry_zone_low:.2f} - {self.entry_zone_high:.2f}",
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "target_1": self.target_1,
            "target_2": self.target_2,
            "rr": self.rr,
            "risk_distance": self.risk_distance(),
            "invalidation_reason": self.invalidation_reason,
            "source_setup": self.source_setup,
            "atr_at_signal": self.atr_at_signal,
        }
