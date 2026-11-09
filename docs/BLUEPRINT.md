# TRAJEDOR: The Autonomous Quantitative AI Architecture for XAU/USD

---

## 1. Deep Mechanics of XAU/USD (Gold vs. US Dollar)

### 1.1 What is XAU/USD?
* **Instrument:** Spot Gold quoted in United States Dollars per Troy Ounce (1 Troy Ounce $\approx$ 31.1035 grams).
* **Tick Size & Point Value:**
  * 1 Pip in Gold = **$0.10** price movement (e.g., $2,650.00 to $2,650.10).
  * 1 Point (Micro-tick) = **$0.01** price movement.
  * Standard Lot (1.00 lot) = **100 Troy Ounces**. A $1.00 move in gold price = **$100.00 profit/loss**.
  * Mini Lot (0.10 lot) = 10 Troy Ounces ($1.00 move = $10.00).
  * Micro Lot (0.01 lot) = 1 Troy Ounce ($1.00 move = $1.00).

---

### 1.2 The Primary Drivers of Gold Price (Fundamental & Macro)

Gold does not generate yield, dividends, or cash flow. Its price is dictated by its relationship to fiat currencies, interest rates, inflation, and global systemic risk:

| Factor | Mechanism / Correlation | Metric to Monitor |
| :--- | :--- | :--- |
| **US Real Yields (TIPS)** | **Strongest Inverse Driver.** When real yields (10-year US Treasury yield minus inflation expectation) rise, holding zero-yield gold has a high opportunity cost. When real yields fall or turn negative, gold surges. | 10-Year TIPS Yield (DFII10 on FRED) |
| **US Dollar Index (DXY)** | **Inverse Correlation.** Gold is priced in USD globally. When USD strengthens, gold becomes more expensive for foreign buyers; when USD weakens, gold demand expands. | DXY / EURUSD / USDJPY |
| **Inflation (CPI, PPI, PCE)** | **Store of Value.** High and persistent inflation erodes purchasing power of fiat currencies, driving capital into physical gold. | Core CPI, US Core PCE Index |
| **Central Bank Purchases** | **Structural Demand Floor.** Sovereign nations (e.g., PBOC China, RBI India, Turkey, Russia) accumulate physical gold to de-dollarize and diversify foreign exchange reserves. | World Gold Council (WGC) quarterly reports, IMF FX Reserve filings |
| **Geopolitical Risk & Wars** | **Safe-Haven Premium.** Conflict, maritime blockades, banking crises, or debt-ceiling standoffs trigger instantaneous institutional flight to safety. | Geopolitical Risk Index (GPR), VIX |
| **COT Report (Commitment of Traders)** | **Positioning of Smart Money.** Published weekly by the CFTC, revealing whether Commercial institutions (Hedgers) or Non-Commercials (Large Speculators/Hedge Funds) are net long or short. | CFTC Disaggregated Gold Commitments |
| **Physical Demand & Seasonality** | Physical jewelry and festival demand (e.g., Diwali in India, Chinese Lunar New Year, wedding seasons) create seasonal demand floors (historically Q4 through Q1). | Shanghai Gold Exchange (SGE) premium vs. London spot |

---

### 1.3 How Price Actually Moves: Liquidity & Session Dynamics

Gold is one of the most volatile and liquid instruments in the financial markets, with distinct session characteristics:

```
[ Asian Session (Tokyo/Sydney/Singapore) ] ──► Tight consolidation / Range formation / Asian High & Low
                      │
                      ▼
[ London Session (08:00 - 16:30 GMT) ]    ──► Heavy institutional volume / London Open Judas Swing / Trend initialization
                      │
                      ▼
[ NY Overlap (13:00 - 17:00 GMT) ]         ──► Peak liquidity & volatility / Major US Macro News releases (CPI/NFP/FOMC)
                      │
                      ▼
[ NY Afternoon & Asian Handover ]          ──► Volume taper / Profit taking / Mean-reversion
```

* **The London Judas Swing:** Institutional market makers frequently push price past the Asian session high or low during the first 60–90 minutes of the London open to trigger retail stop losses (liquidity run) before driving the real trend in the opposite direction.
* **The New York Overlap (13:00 to 17:00 GMT / 8:00 AM to 12:00 PM EST):** Both London and New York are open. Gold experiences 65%+ of its daily range during this 4-hour window.
* **High-Impact News Events:**
  * **FOMC (Interest Rate & Press Conference):** Determines global dollar liquidity trajectories.
  * **US CPI / PPI:** Shifts expectations of Fed rate cuts or hikes.
  * **NFP (Non-Farm Payrolls):** First Friday of every month; triggers massive algorithmic repricing within 500 milliseconds.

---

## 2. Institutional Technical Frameworks for Gold

Gold responds poorly to lagging indicators (like standard moving average crossovers or standard MACD) because it is engineered by market makers to sweep predictable retail levels. Top gold desks rely on **Microstructure, Order Flow, and Institutional Liquidity Concepts**:

### A. Liquidity Sweeps & Stop Hunts (BSL & SSL)
* **Buy-Side Liquidity (BSL):** Clustered above equal highs, swing highs, and previous day highs (PDH) where retail traders place stop-losses for short positions.
* **Sell-Side Liquidity (SSL):** Clustered below equal lows, swing lows, and previous day lows (PDL) where buyers set stops.
* *Market behavior:* Gold will viciously pierce these levels with long wicks, absorb the liquidity, and reverse sharply.

### B. Fair Value Gaps (FVG) / Imbalances (BISI & SIBI)
* Rapid 3-candle displacement where buying or selling was so aggressive that one side was completely bypassed. Price acts like a vacuum, seeking to return and rebalance the FVG before continuing the macro direction.

### C. Order Blocks & Mitigation
* The last opposite candle prior to an aggressive institutional displacement. Represents institutional buy or sell limits awaiting mitigation.

---

## 3. "TRAJEDOR" Architecture: The Massive Multi-Agent AI Brain

Trajedor cannot be a simple single machine learning script. It must be designed as a **Hierarchical Multi-Agent Mixture-of-Experts (MoE)** system.

```mermaid
flowchart TD
    subgraph Data_Layer ["1. Data Ingestion & Microstructure Layer"]
        D1[Real-time L2/L3 Orderbook & Ticks]
        D2[Macro & Rates: DXY, US10Y, TIPS, Oil]
        D3[Economic Calendar & High-Impact Events]
        D4[Live News Feeds & Social Sentiment NLP]
        D5[CFTC COT Positioning & Central Bank Flows]
    end

    subgraph Feature_Engine ["2. Feature Engineering & State Detection"]
        F1[Volatility & Regime Classifier\n(Trending, Ranging, Expansion, News Shock)]
        F2[Liquidity Map: BSL, SSL, FVGs, Key Sessions]
        F3[Multi-timeframe Momentum & Order Flow Delta]
    end

    subgraph Multi_Agent_MoE ["3. Specialized Expert Brains (Sub-Agents)"]
        A1[Agent 1: Macro & Intermarket Bias]
        A2[Agent 2: Institutional Liquidity & SMC]
        A3[Agent 3: Microstructure & Order Flow Scalper]
        A4[Agent 4: NLP News Shock & Speech Sentiment]
    end

    subgraph Arbiter_Layer ["4. The Trajedor Central Executive (Meta-Arbiter)"]
        CE[Gated Attentional Decision Arbiter\nEvaluates Sub-Agent Confidence vs. Current Regime]
    end

    subgraph Risk_Guardian ["5. Mathematical Risk & Capital Engine"]
        R1[Dynamic Kelly Criterion Sizing]
        R2[Volatility-Adjusted ATR Stop Engine]
        R3[Hard Circuit Breakers: Max Daily Loss / Slippage Gate]
    end

    subgraph Execution ["6. Low-Latency Execution"]
        EX[Institutional FIX API / MT5 Bridge]
    end

    Data_Layer --> Feature_Engine
    Feature_Engine --> Multi_Agent_MoE
    Multi_Agent_MoE --> Arbiter_Layer
    Arbiter_Layer --> Risk_Guardian
    Risk_Guardian --> Execution
```

---

### Detailed Sub-Agent Specifications

#### Agent 1: Macro & Intermarket Brain (Macro-Mind)
* **Goal:** Determine the high-level directional bias (Bullish, Bearish, or Neutral) on a 4H to Weekly horizon.
* **Inputs:**
  * Real yields (US 10Y TIPS: inverse correlation threshold -0.82)
  * DXY momentum and yield curve slope (2Y vs 10Y spread)
  * Crude Oil (inflation proxy) and Global Risk VIX
* **Model Type:** Gradient-boosted decision trees (XGBoost/LightGBM) trained on macro regime transitions.

#### Agent 2: Institutional Liquidity & Technical Brain (SMC-Mind)
* **Goal:** Pinpoint exact entry, stop-loss, and take-profit zones using algorithmic order flow logic.
* **Inputs:**
  * Automated detection of Prev Day High/Low, Asian Range High/Low
  * Fair Value Gaps (FVG) and Order Blocks (OB) on M5, M15, and H1
  * Market Structure Shifts (MSS) with displacement volume
* **Model Type:** Graph Neural Networks (GNN) and Spatial Temporal Transformers recognizing structural chart patterns and liquidity pools.

#### Agent 3: Microstructure & Volume Profile Scalper (Tape-Mind)
* **Goal:** Read the live order book, tick velocity, and cumulative volume delta (CVD) at key reaction levels.
* **Inputs:**
  * Footprint chart / Volume Profile / POC (Point of Control)
  * Bid-Ask imbalance and absorption patterns (limit orders soaking market orders)
* **Model Type:** Deep Reinforcement Learning (PPO/SAC) with millisecond-resolution state representations.

#### Agent 4: NLP News & Sentiment Brain (News-Mind)
* **Goal:** Parse breaking news headlines, geopolitical alerts, and Fed speech transcripts in real-time.
* **Inputs:**
  * Financial news APIs (Bloomberg, Reuters, ForexFactory, Twitter/X institutional feeds)
  * Speech-to-text transcripts of live Fed press conferences
* **Model Type:** Fine-tuned transformer (LLM) classifying immediate sentiment shock (-1.0 to +1.0) and market volatility projection.
* **Special Rule:** Capable of triggering the **"Blackout Mode"** (halting new positions 15 minutes before and after CPI/FOMC/NFP).

---

## 4. The Real Secret: The Risk & Capital Management Engine

A trading system fails not because of bad signals, but because of improper mathematical capital allocation. Trajedor incorporates institutional risk parameters:

1. **Fractional Kelly Criterion:**
   $$f^* = \frac{p \cdot b - q}{b} \times \text{Safety Factor (0.25)}$$
   Where $p$ is win rate, $q = 1 - p$, and $b$ is the reward-to-risk ratio. A conservative quarter-Kelly ensures steady geometric growth while eliminating the risk of ruin.
2. **Fixed Risk Per Trade:**
   Maximum risk per trade strictly limited to **0.5% – 1.0%** of total account equity.
3. **Volatility-Normalized Sizing:**
   Lot size is never arbitrary; it is inversely proportional to current ATR (Average True Range):
   $$\text{Position Size (Lots)} = \frac{\text{Account Balance} \times \text{Risk \%}}{\text{Stop Loss in Pips} \times \text{Pip Value per Lot}}$$
4. **Hard Circuit Breaker:**
   * If daily account drawdown reaches **-2.5%**, all trades are liquidated, and trading is locked for 24 hours.
   * If weekly drawdown hits **-5.0%**, the system automatically steps down to paper-trading simulation until regime retraining passes.

---

## 5. Technology Stack & Implementation Roadmap

| Component | Recommended Technology / Tools |
| :--- | :--- |
| **Programming Core** | Python (3.11+) for ML/Pipelines, C++ or Rust for low-latency execution bridges. |
| **Data Ingestion** | Polygon.io, Interactive Brokers API, MetaTrader 5 (MT5 Python API), Tickmill / Pepperstone FIX API, FRED API for macro data. |
| **Data Storage** | TimescaleDB / ClickHouse for high-frequency tick data, Redis for real-time feature caching. |
| **Machine Learning / AI** | PyTorch, Hugging Face Transformers (NLP), LightGBM, Backtrader / VectorBT PRO. |
| **Execution Gateway** | FIX Protocol (4.4) or MetaTrader 5 ZeroMQ/Socket interface running on a low-latency VPS (London/New York Equinix LD4/NY4). |

---

## 6. Development Phases

* **Phase 1: Data Pipeline & Warehouse:** Connect MT5/Broker APIs, download 10 years of M1/Tick Gold data, plus economic indicators (DXY, US10Y, CPI).
* **Phase 2: Feature & Market Regime Engine:** Code the mathematical detection of Asian Session ranges, Liquidity Sweeps, and Trend Regimes.
* **Phase 3: Sub-Agent Prototype:** Develop and backtest Agent 1 (Macro) and Agent 2 (Liquidity) independently on historical walk-forward windows.
* **Phase 4: Risk Arbiter & Paper Execution:** Connect the central executive to a paper-trading demo account to measure real-world slippage, latency, and drawdown behavior.
