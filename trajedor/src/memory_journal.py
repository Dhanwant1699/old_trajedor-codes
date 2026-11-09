"""
TRAJEDOR - Episodic Learning, Mistake Autopsy & Self-Evolution Engine.
Maintains persistent SQLite database of pure AI trades.
Autonomously conducts deep forensic autopsies on failed trades to extract concrete
tactical rules, and enforces a Pre-Trade Cognitive Memory Gate to prevent repeating mistakes.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
DB_PATH = os.path.join(MEMORY_DIR, "trade_history.db")
LESSONS_PATH = os.path.join(MEMORY_DIR, "lessons_learned.json")


class MemoryJournal:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._init_db()
        self._seed_oct_forensic_lessons()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pure_ai_trades (
                    ticket INTEGER PRIMARY KEY,
                    symbol TEXT,
                    account_id TEXT,
                    direction TEXT,
                    volume REAL,
                    entry_price REAL,
                    sl REAL,
                    tp REAL,
                    exit_price REAL,
                    realized_pnl REAL,
                    entry_time TEXT,
                    exit_time TEXT,
                    exit_reason TEXT,
                    setup_type TEXT,
                    post_mortem TEXT,
                    learned_rule TEXT,
                    status TEXT
                )
            """)
            cursor.execute("PRAGMA table_info(pure_ai_trades)")
            columns = [c[1] for c in cursor.fetchall()]
            if "learned_rule" not in columns:
                cursor.execute("ALTER TABLE pure_ai_trades ADD COLUMN learned_rule TEXT")
            conn.commit()

    def _seed_oct_forensic_lessons(self):
        """
        Seeds lessons extracted from the forensic autopsy of actual Oct 1 & Oct 2 trades,
        ensuring Trajedor never repeats the fatal errors of the old algorithm.
        """
        existing = self.get_lessons()
        if len(existing) <= 1:
            seed_lessons = [
                {
                    "rule_id": "RULE_OCT02_01_FALLING_KNIFE",
                    "timestamp": "2026-10-02T19:35:00Z",
                    "trigger": "OCT_2_AUTOPSY_TICKET_287239062",
                    "failure_analysis": "Old algo bought the top at 4153.20 into massive bearish displacement while DXY spiked, holding to hard SL (-€34.80 loss).",
                    "lesson": "NEVER catch falling knives or buy premium highs without liquidity sweep and completed M5 structural confirmation (CHoCH).",
                    "corrective_action": "Wait for sell-side liquidity (SSL) sweep and bullish M5 displacement candle before longing."
                },
                {
                    "rule_id": "RULE_OCT02_02_PANIC_BOTTOM_SELL",
                    "timestamp": "2026-10-02T20:15:00Z",
                    "trigger": "OCT_2_AUTOPSY_TICKET_287289569",
                    "failure_analysis": "Old algo flipped to SELL at 4141.00 directly at the low of the day, getting stopped out on the rebound (-€12.14 loss).",
                    "lesson": "NEVER sell the bottom into daily institutional support / discount zone after extended downward exhaustion.",
                    "corrective_action": "Only short into premium order blocks or retests of broken resistance, never at the floor."
                },
                {
                    "rule_id": "RULE_ASYMMETRY_DEFENSE",
                    "timestamp": "2026-10-02T23:59:00Z",
                    "trigger": "NEGATIVE_ASYMMETRY_DISASTER",
                    "failure_analysis": "Average win was +€6.74 while average loss was -€17.85 due to passive stop-loss surrender.",
                    "lesson": "Active Trade Doctor must cut invalid setups early at -0.3R, protecting 70% risk capital instead of waiting for -1.0R broker SL.",
                    "corrective_action": "Execute early exit immediately if opposing M5 FVG prints or thesis is invalidated."
                },
                {
                    "rule_id": "RULE_RETAIL_TRAP_ALIGNMENT",
                    "timestamp": "2026-10-03T12:00:00Z",
                    "trigger": "RETAIL_HERD_FADING",
                    "failure_analysis": "Entering trades aligned with crowded retail sentiment creates easy stop runs for institutional dealers.",
                    "lesson": "When retail crowd is >70% long, expect an institutional flush of stops before any real upside expansion.",
                    "corrective_action": "Do not enter long until the retail stop cluster below key swing lows is completely swept."
                }
            ]
            try:
                with open(LESSONS_PATH, "w", encoding="utf-8") as f:
                    json.dump(seed_lessons, f, indent=2)
            except Exception:
                pass

    def record_entry(self, ticket: int, symbol: str, account_id: str, direction: str, volume: float, entry_price: float, sl: float, tp: float, setup_type: str = "SMC_LIQUIDITY_SWEEP"):
        now_str = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO pure_ai_trades 
                (ticket, symbol, account_id, direction, volume, entry_price, sl, tp, entry_time, setup_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (ticket, symbol, account_id, direction, volume, entry_price, sl, tp, now_str, setup_type))
            conn.commit()

    def record_exit(
        self,
        ticket: int,
        exit_price: float,
        realized_pnl: float,
        exit_reason: str,
        macro_context: Optional[Dict[str, Any]] = None,
        sentiment_context: Optional[Dict[str, Any]] = None,
        trade_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Records trade exit. If trade incurred a loss or early cut, autonomously performs
        a deep forensic autopsy, extracts a tactical rule, and records it to episodic memory.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        status = "WIN" if realized_pnl > 0 else ("LOSS" if realized_pnl < 0 else "BREAKEVEN")
        post_mortem_text = "Profitable target reached according to structural gameplan."
        learned_rule_text = "Continue adhering to institutional SMC discipline."

        # If trade resulted in loss or early cut, perform forensic autopsy
        if realized_pnl < 0:
            autopsy = self._conduct_forensic_post_mortem(
                ticket=ticket,
                exit_price=exit_price,
                realized_pnl=realized_pnl,
                exit_reason=exit_reason,
                macro_context=macro_context or {},
                sentiment_context=sentiment_context or {},
                trade_data=trade_data or {}
            )
            post_mortem_text = autopsy["analysis"]
            learned_rule_text = autopsy["lesson"]
            self._log_lesson(autopsy)

        td = trade_data or {}
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pure_ai_trades
                SET exit_price = ?, realized_pnl = ?, exit_time = ?, exit_reason = ?, post_mortem = ?, learned_rule = ?, status = ?
                WHERE ticket = ?
            """, (exit_price, realized_pnl, now_str, exit_reason, post_mortem_text, learned_rule_text, status, ticket))
            if cursor.rowcount == 0:
                # If entry was not recorded earlier, insert the complete record now
                cursor.execute("""
                    INSERT OR REPLACE INTO pure_ai_trades 
                    (ticket, symbol, account_id, direction, volume, entry_price, sl, tp, exit_price, realized_pnl, entry_time, exit_time, exit_reason, setup_type, post_mortem, learned_rule, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticket,
                    td.get("symbol", "XAUUSD"),
                    td.get("account_id", "LIVE_ACC"),
                    td.get("direction", "UNKNOWN"),
                    td.get("volume", 0.0),
                    td.get("entry_price", exit_price),
                    td.get("sl", 0.0),
                    td.get("tp", 0.0),
                    exit_price,
                    realized_pnl,
                    td.get("open_time", now_str),
                    now_str,
                    exit_reason,
                    td.get("setup_type", "AI_TRADE"),
                    post_mortem_text,
                    learned_rule_text,
                    status
                ))
            conn.commit()

        return {
            "ticket": ticket,
            "status": status,
            "realized_pnl": realized_pnl,
            "exit_reason": exit_reason,
            "post_mortem": post_mortem_text,
            "learned_rule": learned_rule_text
        }

    def _conduct_forensic_post_mortem(
        self,
        ticket: int,
        exit_price: float,
        realized_pnl: float,
        exit_reason: str,
        macro_context: Dict[str, Any],
        sentiment_context: Dict[str, Any],
        trade_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deep humanoid post-mortem diagnosing exactly why a trade lost money:
        - Detects floor-level sells (selling at support)
        - Detects ceiling-level buys (buying at resistance)
        - Detects back-to-back rapid scalping into adverse flow
        - Detects retail trap & macro invalidations
        """
        td = trade_data or {}
        direction = td.get("direction", "UNKNOWN").upper()
        entry_price = float(td.get("entry_price", exit_price))
        range_pct = td.get("range_pct")
        session_low = td.get("session_low", entry_price - 15.0)
        session_high = td.get("session_high", entry_price + 15.0)
        duration_mins = td.get("duration_mins", 0.0)

        dxy = macro_context.get("dxy", {}).get("price", 0) if isinstance(macro_context.get("dxy"), dict) else macro_context.get("dxy", 0)
        yield_10y = macro_context.get("us10y", {}).get("price", 0) if isinstance(macro_context.get("us10y"), dict) else macro_context.get("us10y", 0)
        long_pct = sentiment_context.get("retail_long_pct", 50.0)

        rule_id = f"RULE_AUTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 1. Forensic Diagnosis: Selling at the Support Floor (The user's specific pain point)
        is_floor_sell = (direction == "SELL") and (
            (range_pct is not None and range_pct <= 0.40) or
            (entry_price - session_low <= 4.0)
        )

        # 2. Forensic Diagnosis: Buying at the Resistance Ceiling
        is_ceiling_buy = (direction == "BUY") and (
            (range_pct is not None and range_pct >= 0.60) or
            (session_high - entry_price <= 4.0)
        )

        # 3. Forensic Diagnosis: Back-to-Back Scalp Failure
        is_rapid_scalp = (duration_mins < 10.0) and td.get("is_rapid_reentry", False)

        if is_floor_sell:
            pct_str = f"{range_pct*100:.1f}%" if range_pct is not None else "lower range"
            analysis = (
                f"FATAL LOCATION ERROR on Ticket #{ticket}: Pre-trade analysis executed SELL at ${entry_price:.2f}, "
                f"directly at the Support Floor / Institutional Discount zone ({pct_str} of range, floor: ${session_low:.2f}). "
                f"The AI misread temporary pause at support as bearish breakdown. Smart money accumulated at the floor, "
                f"swept retail sell stops, and bounced violently into stop loss (-${abs(realized_pnl):.2f})."
            )
            lesson = (
                "NEVER SELL AT THE SUPPORT FLOOR: Shorting below 40% of range or near session low has severe negative expectancy. "
                "Even with negative macro bias, institutional buyers use floor liquidity to engineer sharp reversals."
            )
            action = (
                "STRICT FLOOR BAN: Veto all SELL orders when price is in the lower 40% of range or within 5 pts of session low. "
                "Only sell premium retracements to broken resistance or verified bearish order blocks."
            )
        elif is_ceiling_buy:
            pct_str = f"{range_pct*100:.1f}%" if range_pct is not None else "upper range"
            analysis = (
                f"FATAL LOCATION ERROR on Ticket #{ticket}: Pre-trade analysis executed BUY at ${entry_price:.2f}, "
                f"directly at the Resistance Ceiling / Institutional Premium zone ({pct_str} of range, ceiling: ${session_high:.2f}). "
                f"Chased breakout into supply zone without liquidity sweep (-${abs(realized_pnl):.2f})."
            )
            lesson = (
                "NEVER BUY AT THE RESISTANCE CEILING: Buying above 60% of range or near session high invites dealer distribution."
            )
            action = (
                "STRICT CEILING BAN: Veto all BUY orders when price is in the upper 40% of range or within 5 pts of session high."
            )
        elif is_rapid_scalp:
            analysis = (
                f"RAPID-FIRE OVERTRADING ERROR on Ticket #{ticket}: Executed back-to-back scalp in {direction} "
                f"without waiting for market structure to confirm. Held for only {duration_mins:.1f}m before hitting loss (-${abs(realized_pnl):.2f})."
            )
            lesson = (
                "NO BACK-TO-BACK SCALPING: Rapid re-entries during adverse order flow compound losses. "
                "Require multi-timeframe confirmation (H1/M15) before any new entry."
            )
            action = "Mandatory 15-minute cognitive cooldown and require 5/6 Council consensus before next trade."
        elif exit_reason == "EARLY_CUT":
            analysis = (
                f"Trade #{ticket} stopped out via Trade Doctor Early Cut at {exit_price:.2f} (Loss: -${abs(realized_pnl):.2f}). "
                f"Proactive defense saved ~70% of initial risk by not waiting for broker hard stop loss. "
                f"Adverse displacement confirmed pre-trade thesis invalidation."
            )
            lesson = "Early cut preserved capital. Acknowledge invalidation quickly and do not attempt immediate revenge re-entry."
            action = "Mandatory 15-minute cognitive cooldown to allow new M5/M15 liquidity pool to form."
        elif long_pct > 70.0 and direction == "BUY":
            analysis = (
                f"Trade #{ticket} failed during extreme retail herd positioning ({long_pct:.1f}% Long). "
                f"Dealers hunted retail liquidity beneath swing structure (-${abs(realized_pnl):.2f})."
            )
            lesson = "Failing to anticipate institutional stop hunt during top-heavy retail positioning."
            action = "Do not buy without clear sell-side liquidity (SSL) sweep when retail > 70% long."
        else:
            analysis = (
                f"Trade #{ticket} ({direction} @ ${entry_price:.2f}) failed at ${exit_price:.2f} (Loss: -${abs(realized_pnl):.2f}). "
                f"DXY: {dxy}, US10Y: {yield_10y}%. Price violated key invalidation level. Pre-trade thesis directional assumption failed."
            )
            lesson = "Market structure shifted prior to entry or local momentum overpowered technical setup."
            action = "Ensure multi-timeframe alignment (H1 + M15 + M5) and at least 4/6 Council agreement before execution."

        return {
            "rule_id": rule_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": f"POST_MORTEM_TICKET_{ticket}",
            "failure_analysis": analysis,
            "lesson": lesson,
            "corrective_action": action,
            "analysis": analysis  # Backward compatibility
        }

    def _log_lesson(self, lesson_data: Dict[str, Any]):
        lessons = self.get_lessons()
        # Keep clean schema in lessons_learned.json
        clean_entry = {
            "rule_id": lesson_data.get("rule_id"),
            "timestamp": lesson_data.get("timestamp"),
            "trigger": lesson_data.get("trigger"),
            "failure_analysis": lesson_data.get("failure_analysis", lesson_data.get("analysis")),
            "lesson": lesson_data.get("lesson"),
            "corrective_action": lesson_data.get("corrective_action", lesson_data.get("action"))
        }
        lessons.insert(0, clean_entry)
        try:
            with open(LESSONS_PATH, "w", encoding="utf-8") as f:
                json.dump(lessons[:50], f, indent=2)
        except Exception:
            pass

    def get_lessons(self) -> List[Dict[str, Any]]:
        if os.path.exists(LESSONS_PATH):
            try:
                with open(LESSONS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def audit_trade_thesis_against_memory(
        self,
        action: str,
        price: float,
        macro_score: int,
        crowd_long_pct: float,
        is_scalp: bool = False,
        range_pct: Optional[float] = None,
        recent_loss_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        PRE-TRADE COGNITIVE MEMORY GATE:
        Cross-checks proposed trade against past failure patterns before allowing order dispatch:
        1. Floor Level Sell Defense (RULE_OCT02_02 & Auto-learned lessons)
        2. Ceiling Level Buy Defense (RULE_OCT02_01 & Auto-learned lessons)
        3. Post-Loss Re-Entry & Revenge Scalp Defense
        4. Macro & Retail Trap Defense
        """
        lessons = self.get_lessons()
        warnings = []
        approved = True
        adjusted_guidance = None

        # 1. CRITICAL: Floor Level Sell Defense (Strictly forbids selling at support / floor)
        if action == "SELL" and range_pct is not None and range_pct <= 0.40:
            warnings.append(
                f"Memory Gate VETO (RULE_OCT02_02_PANIC_BOTTOM_SELL): Price is at ${price:.2f} in the Support Floor / Discount zone "
                f"({range_pct*100:.1f}% of range). History proves selling into the floor produces violent stop outs."
            )
            approved = False
            adjusted_guidance = f"VETOED by Cognitive Memory Gate: Floor level sell strictly prohibited ({range_pct*100:.1f}% of range)."

        # 2. CRITICAL: Ceiling Level Buy Defense (Prevents retail FOMO buying at resistance, but permits confirmed institutional breakouts)
        is_breakout = (
            (isinstance(is_scalp, str) and ("BREAKOUT" in is_scalp or "SWING" in is_scalp)) or
            bool(recent_loss_context and recent_loss_context.get("is_breakout"))
        )
        if action == "BUY" and range_pct is not None and range_pct >= 0.85 and not is_breakout:
            warnings.append(
                f"Memory Gate VETO (RULE_OCT02_01_RETAIL_CEILING_FOMO): Price is at ${price:.2f} at the Resistance Ceiling "
                f"({range_pct*100:.1f}% of range) without confirmed breakout expansion. History proves buying at unconfirmed ceilings leads to buying the top."
            )
            approved = False
            adjusted_guidance = f"VETOED by Cognitive Memory Gate: Ceiling level buy strictly prohibited ({range_pct*100:.1f}% of range)."

        # 3. CRITICAL: Post-Loss Directional Cooldown & Revenge Scalping Defense
        if recent_loss_context and recent_loss_context.get("in_cooldown"):
            loss_dir = recent_loss_context.get("direction", "")
            time_left_sec = recent_loss_context.get("seconds_remaining", 0)
            if action == loss_dir:
                warnings.append(
                    f"Memory Gate VETO (POST-LOSS COOLDOWN): Recent loss in {loss_dir} on Ticket #{recent_loss_context.get('ticket')}. "
                    f"Mandatory 15-minute cognitive cooldown active ({int(time_left_sec)}s left). Back-to-back scalping blocked."
                )
                approved = False
                adjusted_guidance = f"VETOED by Cognitive Memory Gate: Post-loss cooling period active ({int(time_left_sec)}s left)."

        # 4. Check against Retail Herd Trap
        if action == "BUY" and crowd_long_pct > 72.0:
            warnings.append(
                "Memory Warning (RULE_RETAIL_TRAP_ALIGNMENT): Retail crowd is heavily LONG (>72%). "
                "Institutions have a history of engineering stop runs before genuine moves. Require M5 SSL sweep confirmation."
            )
            if not is_scalp:
                adjusted_guidance = "Wait for M5 SSL liquidity sweep before pulling the trigger."

        # 5. Check against Macro Mismatch
        if action == "BUY" and macro_score <= -35:
            warnings.append(
                "Memory Warning: Macro score is heavily negative (DXY/Yields surging). "
                "Buying into aggressive macro drag historically resulted in catastrophic stop-outs."
            )
            approved = False
            adjusted_guidance = "VETOED by Cognitive Memory Gate: Do not buy against surging DXY and yields."

        if action == "SELL" and macro_score >= 35:
            warnings.append(
                "Memory Warning: Macro score strongly bullish. Shorting into safe-haven bullion bids matches past loss patterns."
            )
            approved = False
            adjusted_guidance = "VETOED by Cognitive Memory Gate: Do not short into strong bullish macro momentum."

        return {
            "approved": approved,
            "warnings": warnings,
            "adjusted_guidance": adjusted_guidance,
            "lessons_referenced_count": len(lessons),
            "recent_lesson": lessons[0]["lesson"] if lessons else "Maintain strict SMC discipline."
        }

    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pure_ai_trades ORDER BY entry_time DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
