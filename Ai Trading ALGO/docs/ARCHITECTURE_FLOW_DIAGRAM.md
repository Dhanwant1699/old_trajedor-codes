# 🏛️ Complete Architecture & Decision Flow Diagrams

This document contains the complete visual flowcharts, sequence diagrams, and mathematical pipelines for the **Claude Top 10 Strategy Agents AI Trading Council (XAUUSD Gold)**.

> [!TIP]
> You can also view the interactive visual dashboard version by opening **[flow_diagram.html](file:///d:/Ai%20Trading%20ALGO/flow_diagram.html)** in your browser!

---

## 1. Complete End-to-End 24/5 System Lifecycle Flowchart

```mermaid
flowchart TD
    Start([⏱️ 24/5 Async Clock Loop]) --> CheckCandle{New M15 Candle\nClosed?}
    
    CheckCandle -- No --> MonitorOpen[Monitor Open Positions:\nCheck 50% TP1 for Breakeven Shift]
    MonitorOpen --> Sleep[Sleep 30s] --> Start
    
    CheckCandle -- Yes --> Ingest[Extract Live MT5 Data & News]
    
    subgraph Data & News Ingestion
        Ingest --> DE[MT5 Data Engine:\nCompute EMAs, FVGs, Fibo, VWAP, S/D, BB]
        Ingest --> NE[News Engine:\nForexFactory Calendar + Investing.com Feeds]
    end
    
    DE & NE --> ParallelDispatch[⚡ Parallel Multi-Agent Worker Threads\nThreadPoolExecutor max_workers=10]
    
    subgraph Parallel Top 10 Strategy Council
        ParallelDispatch --> A1[1. SMC & ICT Agent]
        ParallelDispatch --> A2[2. Trend & Momentum Agent]
        ParallelDispatch --> A3[3. Mean-Reversion Agent]
        ParallelDispatch --> A4[4. Macro & News Agent]
        ParallelDispatch --> A5[5. Volume & VWAP Agent]
        ParallelDispatch --> A6[6. Supply & Demand Agent]
        ParallelDispatch --> A7[7. Breakout & Volatility Agent]
        ParallelDispatch --> A8[8. Fibonacci & Golden Pocket Agent]
        ParallelDispatch --> A9[9. Chart Pattern Geometry Agent]
        ParallelDispatch --> A10[10. Intraday Scalping Agent]
    end
    
    A1 & A2 & A3 & A4 & A5 & A6 & A7 & A8 & A9 & A10 --> Collect[Collect 10 Structured Strategy Proposals]
    
    Collect --> MacroVetoCheck{Macro Blackout\nActive?}
    MacroVetoCheck -- Yes --> VetoLog[⚠️ News Blackout Veto: Action = HOLD] --> Sleep
    
    MacroVetoCheck -- No --> Arbitrator[⚖️ Master Strategy Arbitrator\nCouncil Consensus Debate & Voting Matrix]
    
    subgraph Lead Arbitrator Debate
        Arbitrator --> QuorumCheck{Consensus Score >= 75%\n& Multi-Paradigm Agreement?}
    end
    
    QuorumCheck -- No --> HoldDecision[Hold Position / Wait for Better Confluence] --> Sleep
    QuorumCheck -- Yes --> CRO[🛡️ Chief Risk Officer - CRO Agent]
    
    subgraph CRO Capital Gatekeeper
        CRO --> CRO_Check{CRO Safety Clearance:\n1. Spread < 35 pts?\n2. DD < 3.0%?\n3. RR >= 1:1.5?\n4. SL Logical?}
    end
    
    CRO_Check -- Fails --> CRO_Veto[🛡️ CRO Veto: Block Trade & Log Reason] --> Sleep
    CRO_Check -- Passes --> DynamicSizing[Dynamic Lot Sizing Formula:\nLots = Dollar_Risk / SL_Dist x 100]
    
    DynamicSizing --> Exec[🚀 MetaTrader 5 Execution Engine]
    Exec --> OrderSend[Send Market Order with Magic Number,\nHard Stop Loss & Take Profit]
    OrderSend --> Sleep
```

---

## 2. 10-Agent Voting Matrix & Consensus Flow

```mermaid
flowchart LR
    subgraph Strategy Inputs
        A1[1. SMC / ICT] -->|BUY 85%| Matrix
        A2[2. Trend Momentum] -->|BUY 80%| Matrix
        A3[3. Mean Reversion] -->|HOLD 20%| Matrix
        A4[4. Macro News] -->|BULLISH +65%| Matrix
        A5[5. Volume / VWAP] -->|BUY 82%| Matrix
        A6[6. Supply / Demand] -->|BUY 80%| Matrix
        A7[7. Breakout Squeeze] -->|HOLD 40%| Matrix
        A8[8. Fibonacci OTE] -->|BUY 88%| Matrix
        A9[9. Chart Patterns] -->|BUY 75%| Matrix
        A10[10. Scalping Fast] -->|BUY 85%| Matrix
    end

    subgraph Council Arbitration Engine
        Matrix[10-Agent Voting Matrix\nBUY: 7 | HOLD: 3 | SELL: 0] --> WeightEngine[Confluence Synthesizer:\nSMC + Fibonacci 0.618 + VWAP + Trend]
        WeightEngine --> ConflictResolver{Strategic Conflict\nDetected?}
        ConflictResolver -- No Conflict --> ScoreCalc[Consensus Score: 88%\nAgreement: UNANIMOUS SUPERMAJORITY]
        ConflictResolver -- Conflict Present --> Resolution[Arbitrate Conflict:\nFavor Trend / Structural Invalidation] --> ScoreCalc
    end

    subgraph Final Action
        ScoreCalc --> Ruling[Master Ruling: BUY\nEntry: 2724.50 | SL: 2719.50 | TP1: 2734.50]
    end
```

---

## 3. Chief Risk Officer (CRO) Dynamic Lot Sizing Flow

```mermaid
flowchart TD
    Input[Consensus Trade Proposal: BUY @ 2724.50 | SL: 2719.50] --> Equity[Get Live Account Equity\ne.g. $50,000]
    
    Equity --> RiskUSD[Calculate Target Risk Amount:\nRisk USD = $50,000 x 1.0% = $500.00]
    
    Input --> SL_Dist[Calculate Price Distance to SL:\nSL Distance = 2724.50 - 2719.50 = $5.00]
    
    RiskUSD & SL_Dist --> Formula[Mathematical Lot Sizing Formula:\nLots = Risk_USD / SL_Distance x Contract_Size_100\nLots = $500 / $5.00 x 100 = 1.00 Lot]
    
    Formula --> StepRounding[Step Rounding & Min/Max Constraints:\nVolume Step: 0.01 | Min: 0.01 | Max: 100.0]
    
    StepRounding --> ClearedLots[Final Cleared Volume: 1.00 Standard Lot]
```

---

## 4. Active Trade Life-Cycle & Breakeven Trailing

```mermaid
stateDiagram-v2
    [*] --> PendingSignal
    PendingSignal --> OrderPlaced: Master Consensus Approved & Cleared by CRO
    OrderPlaced --> Monitoring: Live MT5 Deal Filled with Hard SL & TP
    
    state Monitoring {
        [*] --> OpenInProfit
        OpenInProfit --> ThresholdCheck: Price Moves Towards TP1
        ThresholdCheck --> MoveBreakeven: Price Reaches 50% Distance to TP1
        MoveBreakeven --> RiskFreeTrade: SL Shifted to Entry + 5 Points Buffer
    }
    
    RiskFreeTrade --> TakeProfitHit: Price Hits TP1 / TP2 (Max Gain)
    RiskFreeTrade --> BreakevenHit: Price Reverses (Zero Loss Guaranteed)
    OpenInProfit --> StopLossHit: Price Hits Initial SL (Controlled 1% Loss)
    
    TakeProfitHit --> [*]
    BreakevenHit --> [*]
    StopLossHit --> [*]
```
