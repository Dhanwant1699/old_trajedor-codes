"""
Episodic Learning & Memory Journal for Trajedor.
Maintains persistent trade history, mistake diagnostics, and tactical post-mortems.
Before any trade is executed, Trajedor queries this memory to prevent repeating past errors.
"""

import os
import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class MemoryJournal:
    def __init__(self, db_dir: Optional[str] = None):
        base_dir = db_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(base_dir, exist_ok=True)
        self.db_path = os.path.join(base_dir, "trajedor_memory.db")
        self.lessons_path = os.path.join(base_dir, "lessons_learned.json")
        self._init_db()

    def _init_db(self):
        """Initializes SQLite tables for trades and post-mortems."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE,
                    symbol TEXT,
                    direction TEXT,
                    volume REAL,
                    entry_price REAL,
                    exit_price REAL,
                    pnl REAL,
                    r_multiple REAL,
                    setup_name TEXT,
                    primary_justification TEXT,
                    session_name TEXT,
                    market_regime TEXT,
                    outcome TEXT,
                    mistake_diagnosed TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

        if not os.path.exists(self.lessons_path):
            with open(self.lessons_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def log_trade_entry(
        self,
        ticket: int,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        setup_name: str,
        justification: str,
        session_name: str,
        regime: str
    ):
        """Logs initial trade execution."""
        now_utc = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trade_episodes (
                    ticket, symbol, direction, volume, entry_price,
                    setup_name, primary_justification, session_name,
                    market_regime, outcome, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
            """, (ticket, symbol, direction, volume, entry_price,
                  setup_name, justification, session_name, regime, now_utc))
            conn.commit()

    def log_trade_exit_and_diagnose(
        self,
        ticket: int,
        exit_price: float,
        pnl: float,
        r_multiple: float,
        market_context_at_exit: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Logs trade close, performs automated post-mortem if it resulted in a loss,
        and saves a permanent tactical rule to memory.
        """
        outcome = "WIN" if pnl > 0 else ("BREAKEVEN" if abs(pnl) < 1.0 else "LOSS")
        mistake_analysis = ""

        if outcome == "LOSS":
            ctx = market_context_at_exit or {}
            spread = ctx.get("spread", 0.0)
            is_news = ctx.get("news_active", False)
            opposing_pattern = ctx.get("opposing_pattern", "None")

            # Forensic diagnosis
            if is_news:
                mistake_analysis = "Violation: Trade held or entered near high-impact economic news."
            elif spread > 30:
                mistake_analysis = "Execution error: Entered during severe spread expansion / thin liquidity."
            elif opposing_pattern != "None":
                mistake_analysis = f"Structural error: Ignored strong opposing M5 pattern ({opposing_pattern})."
            else:
                mistake_analysis = "Timing error: Entered before secondary confirmation on lower timeframe."

            # Save lesson
            self._save_lesson(mistake_analysis, ticket, r_multiple)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trade_episodes
                SET exit_price = ?, pnl = ?, r_multiple = ?, outcome = ?, mistake_diagnosed = ?
                WHERE ticket = ?
            """, (exit_price, pnl, r_multiple, outcome, mistake_analysis, ticket))
            conn.commit()

        return {
            "ticket": ticket,
            "outcome": outcome,
            "pnl": pnl,
            "r_multiple": r_multiple,
            "mistake_diagnosed": mistake_analysis or "Clean execution"
        }

    def _save_lesson(self, lesson_text: str, ticket: int, r_multiple: float):
        """Appends a new tactical lesson learned."""
        try:
            with open(self.lessons_path, "r", encoding="utf-8") as f:
                lessons = json.load(f)
            
            lessons.append({
                "ticket": ticket,
                "loss_r": r_multiple,
                "lesson": lesson_text,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            })

            # Keep last 50 lessons
            with open(self.lessons_path, "w", encoding="utf-8") as f:
                json.dump(lessons[-50:], f, indent=2)
        except Exception:
            pass

    def pre_trade_memory_check(self, setup_name: str, session: str) -> Optional[str]:
        """
        Consults historical episodic memory before an order is placed.
        Returns a warning string if this exact setup resulted in repeated recent losses.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM trade_episodes
                WHERE setup_name = ? AND outcome = 'LOSS' AND session_name = ?
            """, (setup_name, session))
            loss_count = cursor.fetchone()[0]

            if loss_count >= 2:
                return f"Memory Warning: {setup_name} has failed {loss_count} times during {session} session recently. Require extra confluence!"

        return None


if __name__ == "__main__":
    print("Testing Trajedor Episodic Memory Journal...")
    journal = MemoryJournal()

    # Log sample trade entry
    journal.log_trade_entry(
        ticket=109283,
        symbol="XAUUSD",
        direction="BUY",
        volume=0.50,
        entry_price=2648.50,
        setup_name="Three_Line_Strike",
        justification="Asian low swept into H1 Bullish FVG",
        session_name="LONDON_OPEN",
        regime="TRENDING"
    )

    # Simulate an adverse trade outcome (Loss)
    diagnosis = journal.log_trade_exit_and_diagnose(
        ticket=109283,
        exit_price=2645.00,
        pnl=-175.00,
        r_multiple=-1.0,
        market_context_at_exit={"spread": 45, "news_active": False}
    )

    print(f"Post-Mortem Result: {diagnosis['outcome']}")
    print(f"Mistake Diagnosed: {diagnosis['mistake_diagnosed']}")

    # Test pre-trade check
    warn = journal.pre_trade_memory_check("Three_Line_Strike", "LONDON_OPEN")
    print(f"Pre-Trade Check Result: {warn or 'No warning: System cleared to trade.'}")
