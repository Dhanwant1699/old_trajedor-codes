# 🤖 Autonomous Multi-Agent AI Trading Council (XAUUSD Gold)

An institutional-grade, multi-provider **Multi-Agent AI Trading System** for **MetaTrader 5 (MT5)**.

Instead of relying on a single trading strategy or a fragile monolithic prompt, this system deploys a **Council of 10 Specialized Market Strategy Agents** that analyze live charts in parallel, debate multi-timeframe setups, calculate mathematically deterministic position sizing via a **Chief Risk Officer (CRO)**, and execute high-probability consensus trades.

---

## 📁 Repository Structure & Directory Hierarchy

```text
Ai Trading ALGO/
├── agents/                      # 🏛️ Top 10 Strategy Agents Council + CRO + Master Arbitrator
│   ├── __init__.py
│   ├── llm_client.py            # Unified Client (NVIDIA NIM, Claude, Groq, Ollama)
│   ├── smc_agent.py             # 1. ICT & Smart Money Concepts (BOS, CHoCH, FVGs, Liquidity Sweeps)
│   ├── trend_agent.py           # 2. Multi-Timeframe Trend & EMA 50/200 Alignment
│   ├── mean_reversion_agent.py  # 3. RSI Extremes (>70/<30) & EMA Exhaustion Snap-backs
│   ├── macro_agent.py           # 4. ForexFactory Calendar & Investing.com Sentiment Feeds
│   ├── orderflow_agent.py       # 5. Intraday VWAP, Point of Control (POC) & Volume Profile
│   ├── supply_demand_agent.py   # 6. Institutional Imbalance Zones (RBR, DBD, Base Retests)
│   ├── breakout_agent.py        # 7. Bollinger Band Squeeze & Volatility Expansion
│   ├── fibonacci_agent.py       # 8. Golden Pocket (0.618-0.786) OTE & Extension Projections
│   ├── pattern_agent.py         # 9. Classical Geometry (Double Tops/Bottoms, Flags, Pinbars)
│   ├── scalping_agent.py        # 10. M5/M15 Fast Momentum & EMA 9/21 Micro Thrusts
│   ├── risk_agent.py            # 11. Chief Risk Officer (CRO) Gatekeeper & Dynamic Lot Sizing
│   └── master_coordinator.py    # 12. Lead Arbitrator (10-Agent Parallel Threading & Voting Matrix)
│
├── core/                        # ⚙️ Real-time Trading & Market Infrastructure Engines
│   ├── __init__.py
│   ├── data_engine.py           # MT5 Memory Bridge (M5/M15/H1/H4 Candles & Indicator Computations)
│   ├── news_engine.py           # ForexFactory JSON & Investing.com RSS News Shield (15-Min Blackout)
│   ├── execution_engine.py      # MT5 Order Placement, Magic Numbers, Breakeven & Trailing Stops
│   └── risk_manager.py          # Exact Mathematical Lot Sizing & Daily Drawdown Guardrails
│
├── docs/                        # 📚 Documentation & Visual Interactive Diagrams
│   ├── ARCHITECTURE_FLOW_DIAGRAM.md  # Complete Markdown Architecture & Flowcharts
│   ├── HOW_AGENTS_WORK_AND_COST.md   # Decision Mechanics & Monthly Running Cost Breakdown
│   └── flow_diagram.html             # Interactive Glassmorphism Flow Diagram
│
├── tests/                       # 🧪 Automated Verification & Benchmark Suites
│   ├── __init__.py
│   ├── test_multi_agent.py      # Council Deliberation & Governance Verification
│   ├── test_engines.py          # MT5 Data, News, and Risk Manager Verification
│   ├── test_nvidia_live.py      # Live NVIDIA NIM API Key Verification
│   └── benchmark_models.py      # Multi-Model Latency & Throughput Benchmark
│
├── logs/                        # 📝 Trade Audit Trails & Session Execution Logs
│   └── .gitkeep
│
├── .env                         # Active Configuration & API Keys
├── .env.example                 # Environment Variable Template
├── config.py                    # Centralized Configuration & Hyperparameters
├── main.py                      # Production Trading Engine Entrypoint
├── requirements.txt             # Python Dependencies
└── README.md                    # System Documentation
```

---

## 🏛️ Architecture: Why Native Multi-Agent vs. LangChain / LangGraph / LlamaIndex / MCP?

| Framework | Design Target | Why We Use Native Concurrent Council for Live Trading |
|---|---|---|
| **LangChain** | Generalized sequential text chains | Introduces 500ms–2000ms abstraction overhead and loose schemas unsuited for real-time tick execution. |
| **LangGraph** | Cyclical state graphs | Great for sequential review loops, but slower than our **native parallel thread pool** which evaluates all 10 agents concurrently in **< 2.5 seconds**. |
| **LlamaIndex** | RAG / Static Vector Document Search | Built for indexing PDFs/text docs, whereas our trading system consumes **live streaming MT5 binary tick memory and real-time economic calendars**. |
| **Anthropic MCP** | Model Context Protocol for external tools | Our engines (`data_engine`, `news_engine`, `execution_engine`) act as native high-speed function callers. MCP can wrap these if exposing to external IDEs. |
| **Our Native Council** | **Institutional Low-Latency Quant AI** | **Zero framework overhead**, strict Pydantic JSON schemas, 10-thread parallel voting matrix, and 100% mathematically deterministic **Chief Risk Officer** lot sizing. |

---

## 🚀 Quickstart Guide

### 1. Configure `.env`
Choose either **NVIDIA NIM (100% Free)** or **Anthropic Claude**:

```ini
# --- AI Provider (nvidia | anthropic | groq | ollama) ---
AI_PROVIDER=nvidia

# --- NVIDIA NIM Cloud (100% FREE) ---
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL=nvidia/nemotron-3-super-120b-a12b  # or deepseek-ai/deepseek-v4-flash-0731

# --- Anthropic Claude ---
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
CLAUDE_MODEL=claude-sonnet-5

# --- Trading & Risk Parameters ---
TRADING_SYMBOL=XAUUSD
EXECUTION_TIMEFRAME=M15
MAX_RISK_PER_TRADE_PCT=1.0
MIN_RISK_REWARD_RATIO=1.5
MAX_DAILY_DRAWDOWN_PCT=3.0
```

### 2. Enable Algo Trading in MetaTrader 5
In MT5: `Tools` ➡️ `Options` ➡️ `Expert Advisors` ➡️ Check **"Allow Algo Trading"**.

### 3. Run Automated Tests
```powershell
.\.venv\Scripts\python tests/test_multi_agent.py
.\.venv\Scripts\python tests/test_engines.py
```

### 4. Start Autonomous 24/5 Trading Engine
```powershell
.\.venv\Scripts\python main.py
```
