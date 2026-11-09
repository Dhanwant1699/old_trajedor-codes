# ⚡ TRAJEDOR: Autonomous Institutional AI Trading Council & Cockpit

**Trajedor** is an autonomous, multi-account algorithmic trading system and visual cockpit engineered for Gold (`XAUUSD`), foreign exchange, and multi-asset markets. It combines macroeconomic drivers (US 10Y TIPS real yields, DXY, Crude Oil), institutional Smart Money Concepts (liquidity sweeps, order blocks, Fair Value Gaps), real-time Google News & FXStreet feeds, a 10-Agent AI Trading Council, and dynamic in-flight trade management.

---

## 🚀 One-Click Root Launchers

| Launcher | Description |
| :--- | :--- |
| **`START_TRAJEDOR_AI.bat`** | Launches the Autonomous Multi-Account AI Trading Council Engine directly with the isolated `.venv` environment. |
| **`LAUNCH_COCKPIT_UI.bat`** | Launches the Visual Web Cockpit Dashboard Server (Port 1111) and automatically opens `http://localhost:1111` in your browser. |
| **`RUN_ALL_IN_ONE.bat`** | Master launcher: Starts both the Trading Council Engine and the Visual Cockpit UI simultaneously in separate labeled consoles. |
| **`SYSTEM_STATUS_CHECK.bat`** | Runs a complete 360° top-down health check across all MT5 terminals, cross-asset feeds, and 9 timeframes. |

---

## 📁 Clean Repository Layout

```
trajedor/
│
├── START_TRAJEDOR_AI.bat          # Double-click launcher: Autonomous AI Engine
├── LAUNCH_COCKPIT_UI.bat          # Double-click launcher: Web Cockpit Dashboard
├── RUN_ALL_IN_ONE.bat             # Double-click launcher: AI Engine + Cockpit UI
├── SYSTEM_STATUS_CHECK.bat        # Diagnostic check: MT5, accounts & feeds
├── README.md                      # Executive system documentation
├── .env.example                   # Environment configuration template
│
├── Ai Trading ALGO/               # Active Trading Council Core Engine
│   ├── .venv/                     # Dedicated Python 3.12+ virtual environment
│   ├── main.py                    # Autonomous Trading Engine entry point
│   ├── launch_dashboard.py        # Web Cockpit server launcher
│   ├── config.py                  # Risk caps, symbol specifications & ports
│   │
│   ├── core/                      # Institutional Intelligence & Execution Engines
│   │   ├── macro_cross_asset_engine.py   # Live DXY, US10Y, Crude Oil, Google & FXStreet News
│   │   ├── market_research_terminal.py   # 360° 9-Timeframe Top-Down Dossier Generator
│   │   ├── humanoid_trader_mind.py       # Discretionary reasoning & metamorphosis
│   │   ├── pro_trade_manager.py          # 7-Sentries risk suite & M5 cognitive trailing SL
│   │   ├── risk_manager.py               # Dynamic lot sizing based on market regime
│   │   ├── data_engine.py                # Multi-terminal MetaTrader 5 interface
│   │   ├── news_engine.py                # Economic calendar & blackout guard
│   │   ├── ai_ledger.py                  # Pure AI trade history & missed entry tracker
│   │   └── dashboard_server.py           # Real-time HTTP REST API server
│   │
│   ├── agents/                    # 10 Institutional AI Council Personas
│   ├── data/                      # Admin configuration, research dossiers, memory DB
│   └── docs/                      # Web Cockpit HTML & Architecture diagrams
│       ├── dashboard.html         # Ultra-modern visual cockpit with Macro Radar
│       └── flow_diagram.html      # Interactive system workflow diagram
│
├── docs/                          # Master Institutional Knowledge Base
│   ├── BLUEPRINT.md               # System Architecture Blueprint
│   ├── TRADING_MANUAL.md          # 43 Candlestick Formations & Statistical Rules
│   └── TRAJEDOR_JARVIS_SPEC.md    # Multi-Agent Coordination Specification
│
└── archive/                       # Archived legacy components
    └── legacy_src/                # Preserved original scripts
```

---

## 🌍 Core System Capabilities

### 1. 360° Macro Intelligence & Cross-Asset Telemetry (No API Keys Required)
- **US Dollar Index (DXY)**: Live price and correlation vector via public chart feeds.
- **US 10-Year Treasury Yield (^TNX)**: Real yield opportunity cost proxy.
- **WTI Crude Oil (CL=F)**: Inflationary expectations and geopolitical escalation proxy.
- **Live Breaking News Stream**: Continuous RSS ingestion from Google News search (`Gold price XAUUSD or Federal Reserve`) and FXStreet breaking feeds.
- **Net Gold Macro Impact Score**: Quantified institutional pressure score (-100 to +100).

### 2. 9-Timeframe Top-Down Structural Matrix
Continuously evaluates price action across all 9 fractal horizons:
- **Secular (1-Year)**, **Semi-Annual (6-Month)**, **Monthly (1-Month)**, **Weekly (1-Week)**
- **Daily (D1)**, **4-Hour (H4)**, **1-Hour (H1)**, **15-Minute (M15)**, **5-Minute (M5)**

### 3. Dynamic In-Flight Trade Management
- **Trade Metamorphosis**: Seamlessly promotes high-momentum scalps into swing runners (`SCALP ➔ SWING`), or demotes swings to quick scalps if order flow slows (`SWING ➔ SCALP`).
- **Cognitive Structural Trailing Stop**: Ratchets SL behind completed M5 swing lows (BUYs) or swing highs (SELLs) rather than using arbitrary pip distances.
- **Dynamic Lot Multiplier**: Scales position size automatically to the current market regime:
  - `FULL_SWING_CLEARANCE` ➔ **1.00x** (e.g. 0.08 lots)
  - `PULLBACK_BUY_DIP` ➔ **0.75x** (e.g. 0.06 lots)
  - `TACTICAL_SCALP_ONLY` ➔ **0.40x** (e.g. 0.03 lots)
  - `TOTAL_STANDBY` ➔ **0.00x** (Capital preserved during high-impact news)
- **Strategic Zone Layering**: Safe institutional averaging at validated supply/demand zones (strictly anti-martingale).

### 4. Pure AI Algorithmic Ledger (Zero Manual Clutter)
- Re-initialized trade history database (`data/ai_trade_history.json` and `data/trajedor_memory.db`) that strictly isolates and audits pure AI-placed orders. Any manual discretionary trades in MetaTrader 5 are completely excluded from the algorithmic track record.
