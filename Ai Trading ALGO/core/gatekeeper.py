"""
Gatekeeper — standalone version for scratch/testing.
Imports trade_plan directly from scratch (no core. prefix needed).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import CONFIG

# Import from same scratch directory
try:
    from core.trade_plan import GateResult, TradeDirection
except ModuleNotFoundError:
    from trade_plan import GateResult, TradeDirection

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_utc(iso_str: str) -> Optional[datetime]:
    if not iso_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(iso_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


class Gatekeeper:
    """
    Runs Stage 1 deterministic permission gates.
    All thresholds read from CONFIG so nothing is hardcoded.
    """

    def __init__(
        self,
        harmony_min: Optional[int] = None,
        max_spread: Optional[float] = None,
        min_rr: Optional[float] = None,
        max_daily_dd: Optional[float] = None,
        max_open_trades: Optional[int] = None,
        cooldown_mins: Optional[int] = None,
        news_pre_mins: Optional[int] = None,
        news_post_mins: Optional[int] = None,
    ):
        self.harmony_min: int     = harmony_min if harmony_min is not None else getattr(CONFIG, "MIN_HARMONY_SCORE", 70)
        self.max_spread: float    = max_spread if max_spread is not None else getattr(CONFIG, "MAX_SPREAD_POINTS", 12.0)
        self.min_rr: float        = min_rr if min_rr is not None else getattr(CONFIG, "MIN_RISK_REWARD_RATIO", 1.75)
        self.max_daily_dd: float  = max_daily_dd if max_daily_dd is not None else getattr(CONFIG, "MAX_DAILY_DRAWDOWN_PCT", 3.0)
        self.max_open_trades: int = max_open_trades if max_open_trades is not None else getattr(CONFIG, "MAX_OPEN_TRADES", 1)
        self.cooldown_mins: int   = cooldown_mins if cooldown_mins is not None else getattr(CONFIG, "COOLDOWN_MINUTES_AFTER_LOSS", 20)
        self.news_pre_mins: int   = news_pre_mins if news_pre_mins is not None else getattr(CONFIG, "NEWS_BLACKOUT_MINUTES", 30)
        self.news_post_mins: int  = news_post_mins if news_post_mins is not None else getattr(CONFIG, "NEWS_BLACKOUT_POST_MINUTES", 15)

    def check_all(self, snapshot: Dict[str, Any], direction: str) -> GateResult:
        direction = direction.upper()
        for gate_fn in [
            self.gate_news_blackout,
            self.gate_liquidity,
            self.gate_h4_regime,
            self.gate_macro_harmony,
            self.gate_account_safety,
        ]:
            result = gate_fn(snapshot, direction)
            if not result.passed:
                logger.info("[GATEKEEPER] BLOCKED at %s | %s", result.failed_gate, result.reason)
                return result
        logger.info("[GATEKEEPER] ALL gates PASSED for direction=%s", direction)
        return GateResult(passed=True, reason="All gates passed")

    def gate_news_blackout(self, snapshot: Dict[str, Any], direction: str) -> GateResult:
        name = "NEWS_BLACKOUT"
        now = _utc_now()
        for bw in snapshot.get("blackout_windows", []):
            if hasattr(bw, "start_utc"):
                start_str, end_str, event = bw.start_utc, bw.end_utc, bw.event
            else:
                start_str = bw.get("start_utc", "")
                end_str   = bw.get("end_utc", "")
                event     = bw.get("event", "Unknown")
            start = _parse_utc(start_str)
            end   = _parse_utc(end_str)
            if start and end and (start <= now <= end):
                return GateResult(
                    passed=False, failed_gate=name,
                    reason=f"Active blackout window: '{event}'",
                    metrics={"event": event, "window_end": end_str},
                )
        if snapshot.get("news_blackout_active", False):
            return GateResult(
                passed=False, failed_gate=name,
                reason=snapshot.get("blackout_reason", "High-impact event imminent"),
                metrics={"news_blackout_active": True},
            )
        return GateResult(passed=True)

    def gate_liquidity(self, snapshot: Dict[str, Any], direction: str) -> GateResult:
        name = "LIQUIDITY"
        spread = float(snapshot.get("spread_points", 0.0) or 0.0)
        clearance = str(snapshot.get("execution_clearance", "CLEAR_OPTIMAL")).upper()
        if "BLACKOUT" in clearance or "SEVERE" in clearance:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"Liquidity blackout: execution_clearance={clearance}",
                metrics={"clearance": clearance, "spread_points": spread},
            )
        if spread > self.max_spread:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"Spread {spread:.1f} pts > max {self.max_spread:.1f} pts",
                metrics={"spread_points": spread, "max_spread": self.max_spread},
            )
        return GateResult(passed=True)

    def gate_h4_regime(self, snapshot: Dict[str, Any], direction: str) -> GateResult:
        name = "H4_REGIME"
        regime = str(snapshot.get("h4_regime") or snapshot.get("regime", "UNKNOWN")).upper()
        is_buy  = direction == "BUY"
        is_sell = direction == "SELL"
        if "TRENDING_BEARISH" in regime and is_buy:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"H4 regime={regime}: BUY vetoed in confirmed bearish trend",
                metrics={"h4_regime": regime, "direction": direction},
            )
        if "TRENDING_BULLISH" in regime and is_sell:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"H4 regime={regime}: SELL vetoed in confirmed bullish trend",
                metrics={"h4_regime": regime, "direction": direction},
            )
        if "MEAN_REVERTING_RANGE" in regime:
            setup_type = str(snapshot.get("setup_type", "BREAKOUT")).upper()
            if "BREAKOUT" in setup_type or "CONTINUATION" in setup_type:
                return GateResult(
                    passed=False, failed_gate=name,
                    reason=f"H4 regime={regime}: breakout-chasing vetoed in ranging market",
                    metrics={"h4_regime": regime, "setup_type": setup_type},
                )
        return GateResult(passed=True)

    def gate_macro_harmony(self, snapshot: Dict[str, Any], direction: str) -> GateResult:
        name = "MACRO_HARMONY"
        harmony = float(snapshot.get("harmony_score", 0.0) or 0.0)
        if harmony < self.harmony_min:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"Harmony {harmony:.0f}% < minimum {self.harmony_min}%",
                metrics={"harmony_score": harmony, "harmony_min": self.harmony_min},
            )
        d1_trend = str(snapshot.get("d1_trend", "NEUTRAL")).upper()
        h4_trend = str(snapshot.get("h4_trend", "NEUTRAL")).upper()
        is_buy  = direction == "BUY"
        is_sell = direction == "SELL"
        if is_buy and "BEARISH" in d1_trend:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"BUY blocked: D1 trend={d1_trend} opposes direction",
                metrics={"d1_trend": d1_trend, "h4_trend": h4_trend},
            )
        if is_buy and "BEARISH" in h4_trend:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"BUY blocked: H4 trend={h4_trend} opposes direction",
                metrics={"d1_trend": d1_trend, "h4_trend": h4_trend},
            )
        if is_sell and "BULLISH" in d1_trend:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"SELL blocked: D1 trend={d1_trend} opposes direction",
                metrics={"d1_trend": d1_trend, "h4_trend": h4_trend},
            )
        if is_sell and "BULLISH" in h4_trend:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"SELL blocked: H4 trend={h4_trend} opposes direction",
                metrics={"d1_trend": d1_trend, "h4_trend": h4_trend},
            )
        return GateResult(passed=True)

    def gate_account_safety(self, snapshot: Dict[str, Any], direction: str) -> GateResult:
        name = "ACCOUNT_SAFETY"
        dd_pct = float(snapshot.get("daily_dd_pct", 0.0) or 0.0)
        if dd_pct >= self.max_daily_dd:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"Daily drawdown {dd_pct:.2f}% >= max {self.max_daily_dd:.2f}%",
                metrics={"daily_dd_pct": dd_pct, "max_daily_dd": self.max_daily_dd},
            )
        open_count = int(snapshot.get("open_positions_count", 0) or 0)
        if open_count >= self.max_open_trades:
            return GateResult(
                passed=False, failed_gate=name,
                reason=f"Open trades {open_count} >= max {self.max_open_trades}",
                metrics={"open_positions_count": open_count},
            )
        last_loss_utc = snapshot.get("last_loss_utc", "")
        if last_loss_utc:
            last_loss = _parse_utc(last_loss_utc)
            if last_loss:
                elapsed_mins = (_utc_now() - last_loss).total_seconds() / 60.0
                if elapsed_mins < self.cooldown_mins:
                    remaining = self.cooldown_mins - elapsed_mins
                    return GateResult(
                        passed=False, failed_gate=name,
                        reason=f"Post-loss cooldown: {remaining:.0f} min remaining (cooldown={self.cooldown_mins} min)",
                        metrics={"elapsed_mins": round(elapsed_mins, 1), "cooldown_mins": self.cooldown_mins},
                    )
        return GateResult(passed=True)


def build_snapshot_from_payload(
    market_payload: Dict[str, Any] = None,
    news_payload: Dict[str, Any] = None,
    *args,
    market_data: Dict[str, Any] = None,
    news_data: Dict[str, Any] = None,
    daily_plan: Any = None,
    open_positions_count: int = 0,
    daily_dd_pct: float = 0.0,
    last_loss_utc: str = "",
) -> Dict[str, Any]:
    if market_payload is None:
        market_payload = market_data or {}
    if news_payload is None:
        news_payload = news_data or {}
    pricing   = market_payload.get("pricing", {})
    spread    = float(pricing.get("spread_points", 0.0) or 0.0)
    liq       = market_payload.get("liquidity_execution_quality", {})
    clearance = str(liq.get("clearance", "CLEAR_OPTIMAL"))
    radar     = market_payload.get("multi_tf_patterns", {})
    harmony   = float(radar.get("harmony_score", 0.0) or 0.0)
    tf        = radar.get("timeframes", {})
    d1_trend  = str(tf.get("D1", {}).get("bias", "NEUTRAL")).upper()
    h4_trend  = str(tf.get("H4", {}).get("bias", "NEUTRAL")).upper()
    regime_d  = market_payload.get("regime_analysis", {})
    h4_regime = str(regime_d.get("regime", "UNKNOWN")).upper()
    bw        = getattr(daily_plan, "blackout_windows", []) if daily_plan else []
    return {
        "spread_points": spread,
        "execution_clearance": clearance,
        "harmony_score": harmony,
        "d1_trend": d1_trend,
        "h4_trend": h4_trend,
        "h4_regime": h4_regime,
        "daily_dd_pct": daily_dd_pct,
        "open_positions_count": open_positions_count,
        "last_loss_utc": last_loss_utc,
        "blackout_windows": bw,
        "news_blackout_active": news_payload.get("news_blackout_active", False),
        "blackout_reason": news_payload.get("blackout_reason", ""),
    }
