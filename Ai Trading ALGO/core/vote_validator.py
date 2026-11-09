"""
Vote Validator for the Staged Institutional Pipeline.

Enforces the Agent Output Contract:
  { "vote": "BUY|SELL|NO_SIGNAL",
    "evidence": ["max 2 facts with numeric values"],
    "invalidation_price": float,
    "confidence": int 0-100 }

Checks:
1. Clamps confidence to [0, 100]  (fixes the 121% bug)
2. Detects self-contradicting votes and marks them INVALID
3. Validates invalidation_price is on the correct side of the live price
4. On malformed JSON: retries once, then treats as NO_SIGNAL
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contradiction rules — (vote, pattern_in_evidence) => INVALID
# ---------------------------------------------------------------------------
# Each tuple: (forbidden_vote, evidence_keyword_list)
# If the agent votes `forbidden_vote` AND any evidence keyword appears,
# the vote is contradicted and marked INVALID.

_CONTRADICTION_RULES: list[Tuple[str, list[str]]] = [
    # Bearish evidence with a BUY vote
    ("BUY", [
        "shooting star", "evening star", "bearish engulfing", "dark cloud",
        "hanging man", "bearish harami", "bearish marubozu", "tweezer top",
        "overbought", "rsi 7", "rsi 8", "rsi 9",           # rsi 70-99
        "aggressive selling", "bid hitter", "hitter", "cvd dump",
        "bearish divergence", "supply zone rejection", "premium zone",
        "death cross",
    ]),
    # Bullish evidence with a SELL vote
    ("SELL", [
        "hammer", "morning star", "bullish engulfing", "piercing line",
        "bullish harami", "bullish marubozu", "tweezer bottom",
        "oversold", "rsi 1", "rsi 2", "rsi 3",             # rsi 10-39
        "aggressive buying", "ask lifter", "lifter", "cvd surge",
        "bullish divergence", "demand zone support", "discount zone",
        "golden cross",
    ]),
]


def _normalise(text: str) -> str:
    return text.lower().strip()


def _is_contradicted(vote: str, evidence: list[str]) -> Tuple[bool, str]:
    """
    Returns (True, reason) if the vote contradicts its evidence, else (False, '').
    """
    combined = " ".join(_normalise(e) for e in evidence)
    vote_upper = vote.upper()

    for forbidden_vote, keywords in _CONTRADICTION_RULES:
        if vote_upper == forbidden_vote:
            for kw in keywords:
                if kw in combined:
                    orig_match = kw
                    for ev in evidence:
                        m = re.search(re.escape(kw), ev, re.IGNORECASE)
                        if m:
                            orig_match = m.group(0)
                            break
                    return True, f"Vote={forbidden_vote} contradicted by evidence containing '{orig_match}'"

    # Special numeric RSI check
    rsi_match = re.search(r"rsi[:\s]+([0-9]+\.?[0-9]*)", combined)
    if rsi_match:
        rsi_val = float(rsi_match.group(1))
        if vote_upper == "BUY" and rsi_val >= 70.0:
            return True, f"Vote=BUY contradicted by RSI={rsi_val:.1f} (overbought >= 70)"
        if vote_upper == "SELL" and rsi_val <= 30.0:
            return True, f"Vote=SELL contradicted by RSI={rsi_val:.1f} (oversold <= 30)"

    return False, ""


def _validate_invalidation_price(
    vote: str, invalidation_price: float, live_price: float
) -> Tuple[bool, str]:
    """
    For BUY: invalidation must be BELOW live_price.
    For SELL: invalidation must be ABOVE live_price.
    NO_SIGNAL: any non-negative value is accepted.
    """
    if vote == "NO_SIGNAL":
        return True, ""
    if invalidation_price <= 0:
        return False, f"invalidation_price={invalidation_price} must be positive"
    if vote == "BUY" and invalidation_price >= live_price:
        return (
            False,
            f"BUY invalidation_price={invalidation_price:.2f} must be < live_price={live_price:.2f}",
        )
    if vote == "SELL" and invalidation_price <= live_price:
        return (
            False,
            f"SELL invalidation_price={invalidation_price:.2f} must be > live_price={live_price:.2f}",
        )
    return True, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

VALID_VOTES = {"BUY", "SELL", "NO_SIGNAL"}


def validate_agent_output(
    raw: Any,
    agent_name: str,
    live_price: float,
) -> Dict[str, Any]:
    """
    Accepts either a dict or a JSON string.
    Returns a normalised dict with keys:
      vote, confidence, evidence, invalidation_price, valid, rejection_reason
    """
    # --- 1. Parse JSON if needed ---
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("[%s] Malformed JSON from agent: %r", agent_name, raw[:200] if raw else "")
            return _no_signal(agent_name, "Malformed JSON — treated as NO_SIGNAL")

    if not isinstance(raw, dict):
        return _no_signal(agent_name, f"Expected dict, got {type(raw).__name__}")

    # --- 2. Extract and normalise vote ---
    raw_vote = str(raw.get("vote", "NO_SIGNAL")).upper().strip()
    if raw_vote not in VALID_VOTES:
        logger.warning("[%s] Unknown vote=%r; defaulting to NO_SIGNAL", agent_name, raw_vote)
        raw_vote = "NO_SIGNAL"

    # --- 3. Clamp confidence to [0, 100] ---
    try:
        confidence = int(float(raw.get("confidence", 50)))
    except (TypeError, ValueError):
        confidence = 50
    if confidence < 0 or confidence > 100:
        logger.warning(
            "[%s] confidence=%d out of range [0-100]; clamping", agent_name, confidence
        )
        confidence = max(0, min(100, confidence))

    # --- 4. Evidence (list of strings, max 2) ---
    evidence = raw.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = [str(evidence)] if evidence else []
    evidence = [str(e) for e in evidence[:2]]

    # --- 5. Invalidation price ---
    try:
        invalidation_price = float(raw.get("invalidation_price", 0.0) or 0.0)
    except (TypeError, ValueError):
        invalidation_price = 0.0

    # --- 6. Contradiction check ---
    contradicted, contra_reason = _is_contradicted(raw_vote, evidence)
    if contradicted:
        logger.warning("[%s] %s", agent_name, contra_reason)
        return {
            "vote": "INVALID",
            "confidence": confidence,
            "evidence": evidence,
            "invalidation_price": invalidation_price,
            "valid": False,
            "rejection_reason": contra_reason,
        }

    # --- 7. Invalidation price side check ---
    inv_ok, inv_reason = _validate_invalidation_price(raw_vote, invalidation_price, live_price)
    if not inv_ok:
        logger.warning("[%s] %s", agent_name, inv_reason)
        return {
            "vote": "INVALID",
            "confidence": confidence,
            "evidence": evidence,
            "invalidation_price": invalidation_price,
            "valid": False,
            "rejection_reason": inv_reason,
        }

    return {
        "vote": raw_vote,
        "confidence": confidence,
        "evidence": evidence,
        "invalidation_price": invalidation_price,
        "valid": True,
        "rejection_reason": "",
    }


def validate_with_retry(
    call_fn,          # callable: () -> Any (raw agent response)
    agent_name: str,
    live_price: float,
) -> Dict[str, Any]:
    """
    Calls call_fn() once; if the result is INVALID or malformed, retries once.
    On second failure, returns NO_SIGNAL.
    """
    for attempt in range(2):
        try:
            raw = call_fn()
            result = validate_agent_output(raw, agent_name, live_price)
            if result["valid"] or result["vote"] == "NO_SIGNAL":
                return result
            logger.warning("[%s] Attempt %d failed validation: %s", agent_name, attempt + 1, result["rejection_reason"])
        except Exception as exc:
            logger.warning("[%s] Attempt %d raised: %s", agent_name, attempt + 1, exc)

    logger.warning("[%s] Both attempts failed — defaulting to NO_SIGNAL", agent_name)
    return _no_signal(agent_name, "Both attempts failed validation")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _no_signal(agent_name: str, reason: str) -> Dict[str, Any]:
    return {
        "vote": "NO_SIGNAL",
        "confidence": 0,
        "evidence": [],
        "invalidation_price": 0.0,
        "valid": True,          # NO_SIGNAL is a valid answer
        "rejection_reason": reason,
    }
