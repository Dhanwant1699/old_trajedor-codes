"""
Master Strategy Coordinator & Lead Arbitrator for the Top 10 Strategy Agents Council.
Orchestrates parallel execution of all 10 specialized trading agents, conducts the council debate,
evaluates the 10-agent voting matrix and quorum consensus, and routes cleared trades through the CRO.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
import anthropic

from config import CONFIG, get_model_api_kwargs
from agents.smc_agent import SMCAgent
from agents.trend_agent import TrendAgent
from agents.mean_reversion_agent import MeanReversionAgent
from agents.macro_agent import MacroAgent
from agents.orderflow_agent import OrderFlowAgent
from agents.supply_demand_agent import SupplyDemandAgent
from agents.breakout_agent import BreakoutAgent
from agents.fibonacci_agent import FibonacciAgent
from agents.pattern_agent import ChartPatternAgent
from agents.scalping_agent import ScalpingAgent
from agents.regime_agent import RegimeDetectionAgent
from agents.liquidity_agent import LiquidityExecutionAgent
from agents.tick_flow_agent import TickOrderFlowAgent
from agents.volume_delta_agent import VolumeDeltaAgent
from agents.risk_agent import ChiefRiskOfficerAgent


MASTER_COUNCIL_SYSTEM_PROMPT = """
You are the Lead Investment Arbitrator & Chief Strategy Coordinator presiding over the XAUUSD Top 14 Strategy Agents Council.
You receive simultaneous strategy proposals from 14 specialized institutional agents:
1. SMC & ICT Agent (Fair Value Gaps, Liquidity Sweeps, Order Blocks)
2. Trend & Momentum Agent (Multi-Timeframe Trend, EMA 50/200 Alignment)
3. Mean-Reversion Agent (RSI Exhaustion, Statistical Bands, Snapbacks)
4. Macro & News Agent (ForexFactory.com Calendar + Investing.com News)
5. Volume Profile & VWAP Agent (Intraday VWAP, Value Area Rejections)
6. Supply & Demand Zones Agent (Fresh Imbalance Origins, RBR/DBD Base Retests)
7. Breakout & Volatility Agent (Bollinger Squeeze, ATR Expansion, London Breakouts)
8. Fibonacci & Golden Pocket Agent (0.618-0.786 OTE Retracements & Extensions)
9. Chart Pattern & Geometry Agent (Double Tops/Bottoms, Head & Shoulders, Pinbars)
10. Intraday Scalping Agent (Fast EMA 9/21 Micro Thrusts)
11. Market Regime Detection Agent (Classifies Trending vs Ranging vs High Volatility Chop; filters strategy conflicts)
12. Liquidity & Execution Quality Agent (Live spread spike, slippage risk, and order book depth auditor)
13. Tick / Order Flow Aggressor Agent (Real-time Ask-Lifters vs Bid-Hitters leading flow imbalance)
14. Cumulative Volume Delta (CVD) Agent (Institutional buy/sell absorption and exhaustion divergences)

COUNCIL ARBITRATION RULES:
1. Regime Alignment Rule: Respect the Regime Detection Agent's classification. In TRENDING regimes, prioritize Trend/Breakout and gate counter-trend fades. In MEAN_REVERTING_RANGE, prioritize support/resistance reversals and veto breakout traps.
2. Microstructure Confirmation: High-conviction entries require alignment between higher-timeframe structure (SMC/Trend/Fibonacci) and leading microstructure (Tick Flow / CVD Delta).
3. Execution Quality Gate: If Liquidity & Execution Quality Agent flags a LIQUIDITY_BLACKOUT or severe spread blowout, output 'HOLD'.
4. Macro Blackout Veto: If the Macro Agent flags a News Blackout Veto, you MUST respect it and output 'HOLD'.
5. Synthesize optimal Entry, structural Stop Loss, and TP1 (1.75R) & TP2 (3.0R) targets.

Respond strictly using the `submit_master_trade_decision` tool call.
"""

MASTER_COUNCIL_TOOL = {
    "name": "submit_master_trade_decision",
    "description": "Submit final synthesized 14-Agent council consensus trade decision for XAUUSD.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["BUY", "SELL", "HOLD", "CLOSE_POSITION"],
                "description": "Final trade action."
            },
            "consensus_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Council consensus conviction score (0-100)."
            },
            "council_agreement_level": {
                "type": "string",
                "enum": ["UNANIMOUS_SUPERMAJORITY", "STRONG_CONSENSUS", "SPLIT_CONFLICTED", "NO_SETUP"],
                "description": "Agreement level across the 14 agents."
            },
            "market_bias": {
                "type": "string",
                "enum": ["BULLISH", "BEARISH", "NEUTRAL"],
                "description": "Unified council market bias."
            },
            "lead_strategies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top strategies driving this consensus setup"
            },
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "risk_percent": {"type": "number", "default": 1.0},
            "close_ticket": {"type": "integer"},
            "voting_summary": {
                "type": "object",
                "description": "Summary of agent votes (e.g. {'BUY': 9, 'SELL': 1, 'HOLD': 4})"
            },
            "council_debate_summary": {
                "type": "string",
                "description": "Comprehensive debate transcript explaining how the 14 agents deliberated, resolved conflicts, and reached consensus."
            }
        },
        "required": ["action", "consensus_score", "council_agreement_level", "market_bias", "council_debate_summary"]
    }
}


from agents.llm_client import UnifiedLLMClient


class MasterCoordinator:
    """
    Coordinates all 14 specialized strategy agents in parallel and acts as Lead Arbitrator.
    Supports Anthropic, NVIDIA NIM, Groq, and Ollama.
    """
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model
        self.provider = self.llm.provider

        # Instantiate all 14 specialized agents with unified provider settings
        self.smc_agent = SMCAgent(provider, model, api_key)
        self.trend_agent = TrendAgent()
        self.trend_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.mean_rev_agent = MeanReversionAgent()
        self.mean_rev_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.macro_agent = MacroAgent()
        self.macro_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.orderflow_agent = OrderFlowAgent()
        self.orderflow_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.supply_demand_agent = SupplyDemandAgent()
        self.supply_demand_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.breakout_agent = BreakoutAgent()
        self.breakout_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.fibonacci_agent = FibonacciAgent()
        self.fibonacci_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.pattern_agent = ChartPatternAgent()
        self.pattern_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.scalping_agent = ScalpingAgent()
        self.scalping_agent.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)

        # 4 New Institutional Specialist Agents
        self.regime_agent = RegimeDetectionAgent(provider, model, api_key)
        self.liquidity_agent = LiquidityExecutionAgent(provider, model, api_key)
        self.tick_flow_agent = TickOrderFlowAgent(provider, model, api_key)
        self.volume_delta_agent = VolumeDeltaAgent(provider, model, api_key)

        # Chief Risk Officer
        self.cro_agent = ChiefRiskOfficerAgent(symbol=CONFIG.SYMBOL)

    @staticmethod
    def _prepare_compact_agent_payload(market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a lean, high-fidelity market snapshot for fast, robust agent LLM inferences."""
        pricing = market_data.get("pricing", {})
        session = market_data.get("session", {})
        account = market_data.get("account", {})
        structures = market_data.get("market_structures", {})
        patterns = market_data.get("multi_tf_patterns", {})

        return {
            "symbol": market_data.get("symbol", "XAUUSD"),
            "pricing": {
                "bid": pricing.get("bid"),
                "ask": pricing.get("ask"),
                "spread_points": pricing.get("spread_points"),
            },
            "session": {
                "session_name": session.get("session_name"),
                "asian_range": session.get("asian_range"),
                "current_utc_time": session.get("current_utc_time"),
            },
            "account": {
                "equity": account.get("equity"),
                "balance": account.get("balance"),
            },
            "market_structures": structures,
            "multi_tf_patterns": {
                "harmony_bias": patterns.get("harmony_bias"),
                "harmony_score": patterns.get("harmony_score"),
                "harmony_description": patterns.get("harmony_description"),
            }
        }

    def run_council_deliberation(
        self,
        market_data: Dict[str, Any],
        news_data: Dict[str, Any],
        current_spread_points: float,
        open_positions_count: int,
        day_of_month: int
    ) -> Dict[str, Any]:
        """
        Executes parallel 14-agent analysis, conducts council debate, and obtains CRO clearance.
        """
        compact_payload = self._prepare_compact_agent_payload(market_data)

        # 1. Execute all 14 specialized agents in parallel
        with ThreadPoolExecutor(max_workers=14) as executor:
            f_smc = executor.submit(self.smc_agent.analyze, compact_payload)
            f_trend = executor.submit(self.trend_agent.analyze, compact_payload)
            f_mean_rev = executor.submit(self.mean_rev_agent.analyze, compact_payload)
            f_macro = executor.submit(self.macro_agent.analyze, news_data)
            f_orderflow = executor.submit(self.orderflow_agent.analyze, compact_payload)
            f_sd = executor.submit(self.supply_demand_agent.analyze, compact_payload)
            f_breakout = executor.submit(self.breakout_agent.analyze, compact_payload)
            f_fibo = executor.submit(self.fibonacci_agent.analyze, compact_payload)
            f_pattern = executor.submit(self.pattern_agent.analyze, compact_payload)
            f_scalp = executor.submit(self.scalping_agent.analyze, compact_payload)
            # 4 New Agents
            f_regime = executor.submit(self.regime_agent.analyze, compact_payload)
            f_liq = executor.submit(self.liquidity_agent.analyze, compact_payload)
            f_tick = executor.submit(self.tick_flow_agent.analyze, compact_payload)
            f_vdelta = executor.submit(self.volume_delta_agent.analyze, compact_payload)

            smc_res = f_smc.result()
            trend_res = f_trend.result()
            mean_rev_res = f_mean_rev.result()
            macro_res = f_macro.result()
            orderflow_res = f_orderflow.result()
            sd_res = f_sd.result()
            breakout_res = f_breakout.result()
            fibo_res = f_fibo.result()
            pattern_res = f_pattern.result()
            scalp_res = f_scalp.result()
            regime_res = f_regime.result()
            liq_res = f_liq.result()
            tick_res = f_tick.result()
            vdelta_res = f_vdelta.result()

        all_proposals = {
            "1_SMC_ICT": smc_res,
            "2_Trend_Momentum": trend_res,
            "3_Mean_Reversion": mean_rev_res,
            "4_Macro_News": macro_res,
            "5_OrderFlow_VWAP": orderflow_res,
            "6_Supply_Demand": sd_res,
            "7_Breakout_Volatility": breakout_res,
            "8_Fibonacci_OTE": fibo_res,
            "9_Chart_Pattern": pattern_res,
            "10_Intraday_Scalp": scalp_res,
            "11_Regime_Detection": regime_res,
            "12_Liquidity_Execution": liq_res,
            "13_Tick_OrderFlow": tick_res,
            "14_Volume_Delta_CVD": vdelta_res
        }

        # 2. Check for immediate Liquidity or Macro Blackout Veto
        if liq_res.get("execution_clearance") == "LIQUIDITY_BLACKOUT":
            return {
                "action": "HOLD",
                "consensus_score": 0,
                "council_agreement_level": "NO_SETUP",
                "market_bias": "NEUTRAL",
                "lead_strategies": ["Liquidity_Spread_Protection"],
                "council_debate_summary": f"Trading halted by Liquidity Agent Veto: {liq_res.get('reasoning', 'Severe spread blowout detected.')}",
                "agent_proposals": all_proposals,
                "cro_report": {"approved": True, "action": "HOLD", "calculated_lots": 0.0}
            }

        if macro_res.get("recommended_action") == "BLACKOUT_VETO" or news_data.get("news_blackout_active"):
            return {
                "action": "HOLD",
                "consensus_score": 0,
                "council_agreement_level": "NO_SETUP",
                "market_bias": macro_res.get("macro_bias", "NEUTRAL"),
                "lead_strategies": ["News_Blackout_Protection"],
                "council_debate_summary": f"Trading halted by Macro Agent Blackout Veto: {news_data.get('blackout_reason', 'High-impact USD event imminent.')}",
                "agent_proposals": all_proposals,
                "cro_report": {"approved": True, "action": "HOLD", "calculated_lots": 0.0}
            }

        # 3. Master Arbitrator Synthesis & Council Debate
        arbitration_payload = {
            "top_14_agent_proposals": all_proposals,
            "live_pricing": market_data.get("pricing", {}),
            "account_equity": market_data.get("account", {}).get("equity", 0.0),
            "regime_summary": regime_res.get("regime_type", "TRENDING_BULLISH"),
            "order_flow_summary": tick_res.get("flow_imbalance", "BALANCED_FLOW"),
            "cvd_summary": vdelta_res.get("cvd_pattern", "NEUTRAL_DELTA")
        }

        arbitration_prompt = f"""
You are presiding over the XAUUSD Top 14 Strategy Agents Council.
Here are the simultaneous proposals from all 14 specialized strategy agents:

{json.dumps(arbitration_payload, indent=2)}

Conduct the council arbitration:
1. Apply the Regime Detection Agent's rule: Filter out strategies that conflict with the regime (e.g. Breakout vetoed in Range; Counter-trend short vetoed in Bullish Trend).
2. Tabulate the 14-agent voting distribution (BUY, SELL, HOLD).
3. Confirm alignment between macro structure (SMC, Fibonacci, Trend) and leading microstructure (Tick Order Flow, CVD Delta).
4. If consensus is reached (>= 75 score), formulate the final Entry, Stop Loss, and TP1/TP2 targets.

Submit your ruling using the `submit_master_trade_decision` tool.
"""

        res = self.llm.call_structured(
            system_prompt=MASTER_COUNCIL_SYSTEM_PROMPT,
            user_prompt=arbitration_prompt,
            tool_definition=MASTER_COUNCIL_TOOL,
            max_tokens=500
        )

        if "error" in res or not res or not res.get("action"):
            master_decision = self._calculate_algorithmic_consensus(all_proposals, market_data)
        else:
            master_decision = res

        # 4. Mathematically calibrate Entry, SL, TP1 (1.75R), and TP2 (3.0R) to realistic intraday structure
        master_decision = self._sanitize_and_calibrate_decision(master_decision, market_data)

        # 5. Chief Risk Officer (CRO) Dynamic Lot Sizing & Safety Clearance
        cro_report = self.cro_agent.evaluate_and_size_trade(
            proposal=master_decision,
            account_info=market_data.get("account", {}),
            current_spread_points=current_spread_points,
            open_positions_count=open_positions_count,
            day_of_month=day_of_month
        )

        master_decision["cro_report"] = cro_report
        master_decision["agent_proposals"] = all_proposals

        if not cro_report.get("approved", False) and master_decision.get("action") in ["BUY", "SELL"]:
            master_decision["action"] = "HOLD"
            master_decision["council_debate_summary"] += f" | [CRO VETO]: {cro_report.get('reason')}"

        return master_decision

    def _sanitize_and_calibrate_decision(
        self,
        decision: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Guarantees that ANY council decision (from LLM or algorithmic fallback)
        has mathematically precise, strictly validated, institutional intraday SL, TP1, and TP2 targets.
        """
        action = str(decision.get("action", "HOLD")).upper()
        if action not in ["BUY", "SELL"]:
            return decision

        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4350.0)
        struct = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        atr = float(struct.get("atr_14", 8.0) or 8.0)

        sym = str(market_data.get("symbol", CONFIG.SYMBOL)).upper()
        is_gold = "XAU" in sym or "GOLD" in sym
        is_btc = "BTC" in sym and live_price > 1000.0

        # Calculate instrument-specific SL bounds
        if is_gold:
            min_sl = 6.50
            max_sl = 11.00
            default_sl = max(min_sl, min(max_sl, atr * 1.25))
            max_entry_drift = 3.50
        elif is_btc:
            min_sl = 350.0
            max_sl = 850.0
            default_sl = 500.0
            max_entry_drift = 100.0
        else:
            min_sl = live_price * 0.0025
            max_sl = live_price * 0.0080
            default_sl = live_price * 0.0040
            max_entry_drift = live_price * 0.0020

        # 1. Sanitize Entry Price (Anchor to realistic live pullback zone)
        raw_entry = float(decision.get("entry_price", 0.0) or 0.0)
        if raw_entry <= 0.0 or abs(raw_entry - live_price) > max_entry_drift:
            if action == "BUY":
                entry_p = round(live_price - (1.20 if is_gold else 25.0 if is_btc else live_price * 0.001), 2)
            else:
                entry_p = round(live_price + (1.20 if is_gold else 25.0 if is_btc else live_price * 0.001), 2)
        else:
            entry_p = round(raw_entry, 2)

        # 2. Sanitize and Clamp Stop Loss Distance
        raw_sl = float(decision.get("stop_loss", 0.0) or 0.0)
        if raw_sl > 0:
            raw_risk = abs(entry_p - raw_sl)
        else:
            raw_risk = default_sl

        risk = max(min_sl, min(max_sl, raw_risk))

        if action == "BUY":
            sl_p = round(entry_p - risk, 2)
            tp1_p = round(entry_p + (risk * 1.75), 2)
            tp2_p = round(entry_p + (risk * 3.00), 2)
            # Guarantee positive numbers and correct order
            if sl_p <= 0 or sl_p >= entry_p or tp1_p <= entry_p or tp2_p <= tp1_p:
                sl_p = round(entry_p - default_sl, 2)
                tp1_p = round(entry_p + (default_sl * 1.75), 2)
                tp2_p = round(entry_p + (default_sl * 3.00), 2)
        else:
            sl_p = round(entry_p + risk, 2)
            tp1_p = round(entry_p - (risk * 1.75), 2)
            tp2_p = round(entry_p - (risk * 3.00), 2)
            # Guarantee positive numbers and correct order
            if tp2_p <= 0 or tp1_p <= 0 or tp1_p >= entry_p or sl_p <= entry_p:
                sl_p = round(entry_p + default_sl, 2)
                tp1_p = round(entry_p - (default_sl * 1.75), 2)
                tp2_p = round(entry_p - (default_sl * 3.00), 2)

        rr_ratio = round(abs(tp1_p - entry_p) / max(0.01, abs(entry_p - sl_p)), 2)

        decision["entry_price"] = entry_p
        decision["stop_loss"] = sl_p
        decision["take_profit_1"] = tp1_p
        decision["take_profit_2"] = tp2_p
        decision["risk_reward_ratio"] = rr_ratio
        if not decision.get("invalidation_condition"):
            decision["invalidation_condition"] = f"M15 close beyond {sl_p:,.2f}"

        return decision

    def _calculate_algorithmic_consensus(
        self,
        proposals: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Algorithmic Institutional Consensus Aggregator (Deterministic Rule-Based Fallback).
        Guarantees that high-confluence 14-agent signals are NEVER lost to LLM network latency/timeouts.
        Incorporates Market Regime gating, Liquidity clearances, Tick Flow, and Volume Delta.
        """
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 4350.0)

        # 1. Extract Regime and Microstructure Context
        regime_prop = proposals.get("11_Regime_Detection", {})
        regime_type = str(regime_prop.get("regime_type", "TRENDING_BULLISH")).upper()
        
        tick_prop = proposals.get("13_Tick_OrderFlow", {})
        flow_imbalance = str(tick_prop.get("flow_imbalance", "BALANCED_FLOW")).upper()

        vdelta_prop = proposals.get("14_Volume_Delta_CVD", {})
        cvd_pattern = str(vdelta_prop.get("cvd_pattern", "NEUTRAL_DELTA")).upper()

        buy_votes = 0
        sell_votes = 0
        hold_votes = 0

        buy_confidences = []
        sell_confidences = []

        buy_entries = []
        buy_sls = []
        buy_tps = []

        sell_entries = []
        sell_sls = []
        sell_tps = []

        for k, prop in proposals.items():
            act = str(prop.get("action", prop.get("recommended_action", "HOLD"))).upper()
            conf = float(prop.get("confidence_score", prop.get("sentiment_score", 0)) or 0)
            entry = float(prop.get("entry_price", live_price) or live_price)
            sl = float(prop.get("stop_loss", 0.0) or 0.0)
            tp = float(prop.get("take_profit", prop.get("take_profit_1", 0.0)) or 0.0)

            # Regime Gating Rule:
            # If in strong trending regime, discount counter-trend mean reversion
            if "TRENDING_BULLISH" in regime_type and "Mean_Reversion" in k and "SELL" in act:
                act = "HOLD"
            elif "TRENDING_BEARISH" in regime_type and "Mean_Reversion" in k and "BUY" in act:
                act = "HOLD"
            elif "MEAN_REVERTING_RANGE" in regime_type and "Breakout" in k:
                # In ranges, breakout trades are often traps unless confirmed by CVD
                if "ABSORPTION" not in cvd_pattern and "DELTA_SURGE" not in cvd_pattern:
                    act = "HOLD"

            if "BUY" in act:
                buy_votes += 1
                buy_confidences.append(conf)
                if entry > 0: buy_entries.append(entry)
                if sl > 0: buy_sls.append(sl)
                if tp > 0: buy_tps.append(tp)
            elif "SELL" in act:
                sell_votes += 1
                sell_confidences.append(conf)
                if entry > 0: sell_entries.append(entry)
                if sl > 0: sell_sls.append(sl)
                if tp > 0: sell_tps.append(tp)
            else:
                hold_votes += 1

        voting_summary = {"BUY": buy_votes, "SELL": sell_votes, "HOLD": hold_votes}

        is_btc = "BTC" in str(market_data.get("symbol", "")).upper() and live_price > 1000.0
        is_gold = "XAU" in str(market_data.get("symbol", "")).upper() or "GOLD" in str(market_data.get("symbol", "")).upper()
        if is_gold:
            min_sl_dist = 6.50
            max_sl_dist = 11.00
            default_sl_dist = 8.50
        elif is_btc:
            min_sl_dist = 350.0
            max_sl_dist = 850.0
            default_sl_dist = 500.0
        else:
            min_sl_dist = max(0.10, live_price * 0.0025)
            max_sl_dist = max(0.50, live_price * 0.0080)
            default_sl_dist = max(0.25, live_price * 0.0040)

        # 14-Agent Consensus: >= 6 directional votes with dominant side
        total_agents = 14
        if buy_votes >= 5 and buy_votes > sell_votes:
            avg_conf = sum(buy_confidences) / max(1, len(buy_confidences))
            consensus_score = min(98, int((buy_votes / float(total_agents)) * 100 + (avg_conf * 0.15)))
            entry_p = round(sum(buy_entries) / len(buy_entries), 2) if buy_entries else round(live_price - 1.5, 2)
            
            # Clamp SL to realistic institutional intraday structure
            raw_sl = min(buy_sls) if buy_sls else (entry_p - default_sl_dist)
            raw_risk = abs(entry_p - raw_sl)
            risk = max(min_sl_dist, min(max_sl_dist, raw_risk))
            sl_p = round(entry_p - risk, 2)

            tp1_p = round(entry_p + (risk * 1.75), 2)
            tp2_p = round(entry_p + (risk * 3.00), 2)
            rr_ratio = round(abs(tp1_p - entry_p) / risk, 2)

            return {
                "action": "BUY",
                "consensus_score": consensus_score,
                "council_agreement_level": "UNANIMOUS_SUPERMAJORITY" if buy_votes >= 10 else "STRONG_CONSENSUS",
                "market_bias": "BULLISH",
                "lead_strategies": ["Multi-Agent Institutional Confluence", f"Regime_{regime_type}", f"Tick_{flow_imbalance}"],
                "entry_price": entry_p,
                "stop_loss": sl_p,
                "take_profit_1": tp1_p,
                "take_profit_2": tp2_p,
                "risk_reward_ratio": rr_ratio,
                "invalidation_condition": f"M15 close below structural support at {sl_p:,.2f}",
                "voting_summary": voting_summary,
                "council_debate_summary": f"14-Agent Consensus: {buy_votes}/14 agents voted BUY ({consensus_score}% score). Regime: {regime_type}, Flow: {flow_imbalance}. Target TP1 @ {tp1_p:,.2f} (1.75R) & TP2 @ {tp2_p:,.2f} (3.0R)."
            }

        elif sell_votes >= 5 and sell_votes > buy_votes:
            avg_conf = sum(sell_confidences) / max(1, len(sell_confidences))
            consensus_score = min(98, int((sell_votes / float(total_agents)) * 100 + (avg_conf * 0.15)))
            entry_p = round(sum(sell_entries) / len(sell_entries), 2) if sell_entries else round(live_price + 1.5, 2)
            
            # Clamp SL to realistic institutional intraday structure
            raw_sl = max(sell_sls) if sell_sls else (entry_p + default_sl_dist)
            raw_risk = abs(raw_sl - entry_p)
            risk = max(min_sl_dist, min(max_sl_dist, raw_risk))
            sl_p = round(entry_p + risk, 2)

            tp1_p = round(entry_p - (risk * 1.75), 2)
            tp2_p = round(entry_p - (risk * 3.00), 2)
            rr_ratio = round(abs(entry_p - tp1_p) / risk, 2)

            return {
                "action": "SELL",
                "consensus_score": consensus_score,
                "council_agreement_level": "UNANIMOUS_SUPERMAJORITY" if sell_votes >= 10 else "STRONG_CONSENSUS",
                "market_bias": "BEARISH",
                "lead_strategies": ["Multi-Agent Institutional Confluence", f"Regime_{regime_type}", f"Tick_{flow_imbalance}"],
                "entry_price": entry_p,
                "stop_loss": sl_p,
                "take_profit_1": tp1_p,
                "take_profit_2": tp2_p,
                "risk_reward_ratio": rr_ratio,
                "invalidation_condition": f"M15 close above structural resistance at {sl_p:,.2f}",
                "voting_summary": voting_summary,
                "council_debate_summary": f"14-Agent Consensus: {sell_votes}/14 agents voted SELL ({consensus_score}% score). Regime: {regime_type}, Flow: {flow_imbalance}. Target TP1 @ {tp1_p:,.2f} (1.75R) & TP2 @ {tp2_p:,.2f} (3.0R)."
            }

        else:
            return {
                "action": "HOLD",
                "consensus_score": 0,
                "council_agreement_level": "SPLIT_CONFLICTED",
                "market_bias": "NEUTRAL",
                "entry_price": live_price,
                "stop_loss": round(live_price - 10.0, 2),
                "take_profit_1": round(live_price + 15.0, 2),
                "take_profit_2": round(live_price + 28.0, 2),
                "voting_summary": voting_summary,
                "council_debate_summary": f"Sidelines: 14 Agents split ({buy_votes} Buy, {sell_votes} Sell, {hold_votes} Hold). Regime: {regime_type}. Waiting for clean directional breakout."
            }
