# Architecture Specification: TRAJEDOR (Jarvis) Evolutionary Humanoid AI Trader

## 1. Executive Summary & Vision
**Trajedor** is an evolutionary, humanoid AI trading mind engineered for Spot Gold (`XAUUSD`) and global financial markets. 

Unlike rigid, rule-based algorithmic bots, Trajedor functions as a **sentient cognitive trader**:
* **Reasons dynamically** by synthesizing live price action, macro fundamentals, breaking news, and real-time social sentiment.
* **Draws directly on charts**, visually plotting Order Blocks, Fair Value Gaps, liquidity levels, and trade targets.
* **Adapts across multi-timeframe styles**: dynamically switching between **Scalping (M1-M5)**, **Day Trading (M15-H1)**, and **Swing Trading (H4-Daily)**.
* **Active In-Flight Diagnostics ("Trade Doctor")**: When a trade goes against the plan, it instantly investigates *why* in real-time, inspects structural breakdown vs. temporary sweeps, and dynamically cuts, hedges, or de-risks positions to preserve capital.
* **Manages positions like an elite human hedge-fund trader**: dynamically taking partial profits, trailing structural stops, and cutting losing trades early when market conditions shift.
* **Executes across multiple MetaTrader 5 accounts** simultaneously with custom risk profiles per account.
* **Self-Improves and Learns from Mistakes**: logs every trade into a persistent episodic memory bank, performing post-mortems and consulting historical lessons before executing future orders.

---

## 2. System Architecture & Directory Layout

Target Directory: `c:\Users\Golu\OneDrive\Desktop\trajedor\AI Trading ALGO\`

```
AI Trading ALGO/
│
├── config/
│   ├── settings.py              # Master settings: risk %, symbols, timeframe thresholds
│   ├── accounts.json            # Multi-account configuration (Prop, Personal, Swing)
│   └── .env                     # Local credentials (MT5 logins, API keys, passwords)
│
├── src/
│   ├── __init__.py
│   ├── cognitive_brain.py       # Core LLM Reasoning & Deliberation Engine (The Humanoid Mind)
│   ├── trade_doctor.py          # Real-Time In-Flight Diagnostics & Active Defense Engine
│   ├── mt5_multi_account.py     # Multi-Terminal MetaTrader 5 Bridge & Order Dispatcher
│   ├── chart_vision.py          # Visual Chart Plotter (Draws OBs, FVGs, targets & saves PNGs)
│   ├── memory_journal.py        # Episodic Learning Engine & Mistake Database (Self-Improvement)
│   ├── trading_personas.py      # Adaptive Style Engine (Scalper, Day Trader, Swing Trader)
│   ├── news_sentinel.py         # Live Forex Factory Calendar & Blackout Guard
│   ├── sentiment_sentinel.py    # Stocktwits & X Real-Time Crowd Sentiment Radar
│   ├── risk_guardian.py         # Dynamic Kelly Sizing, ATR Stops, and Daily Drawdown Circuit Breaker
│   └── jarvis_executive.py      # Real-Time Event Loop & Terminal Live HUD Interface
│
├── memory/
│   ├── trade_history.db         # Persistent SQLite database of all historical trades & outcomes
│   ├── lessons_learned.json     # Continuous memory of mistakes and tactical corrections
│   └── chart_snapshots/         # Visual chart images with AI drawings (Entry, SL, TP, OBs)
│
├── tests/                       # Test-Driven Development (TDD) verification suite
│   ├── __init__.py
│   ├── test_trade_doctor.py
│   ├── test_cognitive_brain.py
│   ├── test_memory_journal.py
│   ├── test_chart_vision.py
│   └── test_risk_guardian.py
│
├── run_trajedor.py              # Main CLI execution launcher
└── README.md                    # Operator Manual & Setup Guide
```

---

## 3. Subsystem Deep-Dive

### 3.1 Cognitive Reasoning Brain (`cognitive_brain.py`)
* Operates as a Chain-of-Thought deliberation loop:
  1. **Regime Diagnosis:** Evaluates whether market is trending, sweeping liquidity, consolidating, or in a pre-news lull.
  2. **Multi-Source Synthesis:** Synthesizes MT5 technicals + Forex Factory news calendar + Real Yields (10Y TIPS) + DXY + Stocktwits crowd sentiment.
  3. **Trade Thesis Generation:** Drafts a written gameplan with entry trigger, specific invalidation level, and multi-stage profit targets.
  4. **Pre-Trade Memory Query:** Before pulling the trigger, queries `memory_journal.py` to check for similar past mistakes.

### 3.2 Real-Time In-Flight Diagnostics & Active Defense ("Trade Doctor" - `trade_doctor.py`)
When a planned trade begins moving into an adverse loss, **Trajedor DOES NOT sit passively waiting for the stop-loss to hit**.

```
                           [ TRADE MOVES INTO ADVERSE LOSS ]
                                           │
                                           ▼
                   ┌───────────────────────────────────────────────┐
                   │    INSTANT REAL-TIME FORENSIC INVESTIGATION   │
                   │  1. Did DXY or Real Yields suddenly reverse?  │
                   │  2. Did breaking unscheduled news hit?        │
                   │  3. Did M5 market structure cleanly break?    │
                   │  4. Did volume/order book flip against us?    │
                   └───────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
        [ THESIS INVALIDATED ]                         [ LIQUIDITY SWEEP / NOISE ]
     Structural shift or macro shock               Thesis intact; market hunting stops
                    │                                             │
                    ▼                                             ▼
   ┌─────────────────────────────────┐           ┌─────────────────────────────────┐
   │     ACTIVE DEFENSE ACTION:      │           │         STAY THE COURSE:        │
   │ 1. Cut loss IMMEDIATELY (-0.3R) │           │ 1. Maintain conviction          │
   │    Save 70% of risk capital!    │           │ 2. Avoid premature panic close  │
   │ 2. Partial derisk (close 50%)   │           │ 3. Log observation in memory    │
   │ 3. Log instant post-mortem      │           └─────────────────────────────────┘
   └─────────────────────────────────┘
```

* **Immediate Forensic Check:**
  * **Macro Shock:** Did DXY or 10Y Yields experience an impulsive breakout?
  * **Breaking News:** Did an unscheduled news alert cross the wire?
  * **Structural Invalidation:** Did price print an opposing displacement candle with an FVG against the position?
* **Decisive Position Actions:**
  * **Emergency Early Cut:** Exits the trade at $-0.2R$ to $-0.4R$ before the hard stop loss is reached, preserving capital.
  * **Emergency Partial De-Risk:** Closes 50% immediately to limit exposure while leaving a micro runner if recovery is possible.
  * **Instant Forensic Memory Log:** Logs the exact point of failure into episodic memory so the system updates its intraday bias immediately.

### 3.3 Visual Chart Plotter & Technical Drawing (`chart_vision.py`)
* Automatically renders high-resolution candlestick charts:
  * **Order Block Boxes** (colored zones showing institutional supply/demand).
  * **Fair Value Gaps** (shaded rectangles indicating price imbalances).
  * **Liquidity Sweeps** (dotted horizontal lines marking swept BSL/SSL highs and lows).
  * **Trade Overlays**: Visual Green entry line, Red Stop-Loss line, and Gold Take-Profit lines.
* Saves visual chart snapshots to `memory/chart_snapshots/` for every executed trade and post-trade review.

### 3.4 Episodic Learning & Memory Journal (`memory_journal.py`)
* The Self-Improvement Engine:
  * Logs the complete trade lifecycle: Entry Time, Setup Pattern, Reason for Entry, Market Context, Exit Time, P&L, and Result.
  * **Automated Post-Mortem Diagnostics:**
    * If a trade results in a loss, evaluates:
      * Did price violate structure?
      * Was it entered during low liquidity or spread expansion?
      * Did I chase the candle instead of waiting for a retest?
    * Extracts a **Tactical Lesson** and appends it to `lessons_learned.json`.
  * **Pre-Trade Sanity Check:**
    * When a new setup forms, searches memory for similar historical losses to prevent repeating emotional or technical errors.

### 3.5 Multi-Style Trading Personas (`trading_personas.py`)
Trajedor adapts between three distinct market mindsets:
* **The Scalper (M1 - M5):** Focuses on Asian session extremes and London open sweeps. Target: 10 to 25 pips.
* **The Day Trader (M15 - H1):** Focuses on session expansions, Fair Value Gap retests, and structural trend continuation. Target: 40 to 90 pips.
* **The Swing Trader (H4 - Daily):** Driven by macro interest rate cycles, inflation trends, and weekly order blocks. Target: 150 to 400+ pips.

### 3.6 Multi-Account Master Allocator (`mt5_multi_account.py`)
* Connects to multiple MT5 accounts:
  * **Account 1 (Prop Firm):** Strict daily loss limits (e.g. max 1% per day, 0.5% per trade).
  * **Account 2 (Personal Growth):** Fractional Kelly sizing (0.75% to 1.0% risk per trade).
  * **Account 3 (Swing):** Tailored for multi-day swing positions.
* Dispatches and synchronizes positions across all configured accounts in parallel.

---

## 4. Test-Driven Development (TDD) Plan
Following Superpowers methodology:
1. `test_trade_doctor.py`: Verify that when price simulates adverse movement, the Trade Doctor diagnoses the cause and executes early de-risking/early exit before the full stop is hit.
2. `test_memory_journal.py`: Verify that trades are stored, losses trigger post-mortems, and pre-trade memory lookups return applicable warnings.
3. `test_chart_vision.py`: Verify chart generation and accurate drawing of OBs, FVGs, and SL/TP lines.
4. `test_trading_personas.py`: Verify dynamic switching between Scalper, Day Trader, and Swing Trader profiles.
5. `test_risk_guardian.py`: Verify strict risk enforcement and multi-account lot calculations.
