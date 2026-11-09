"""
Master Strategy Coordinator & Lead Arbitrator for the Bitcoin (BTCUSD) AI Strategy Council.
Orchestrates parallel execution of all 14 specialized Bitcoin trading agents, conducts the crypto council debate,
evaluates the voting matrix and quorum consensus, and routes cleared trades through the Bitcoin CRO.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from config import CONFIG
from agents.llm_client import UnifiedLLMClient

from agents.btcusd.btcusd_smc_agent import CryptoSMCAgent
from agents.btcusd.btcusd_trend_agent import CryptoTrendAgent
from agents.btcusd.btcusd_mean_reversion_agent import CryptoMeanReversionAgent
from agents.btcusd.btcusd_macro_agent import CryptoMacroAgent
from agents.btcusd.btcusd_orderflow_agent import CryptoOrderFlowAgent
from agents.btcusd.btcusd_supply_demand_agent import CryptoSupplyDemandAgent
from agents.btcusd.btcusd_breakout_agent import CryptoBreakoutAgent
from agents.btcusd.btcusd_fibonacci_agent import CryptoFibonacciAgent
from agents.btcusd.btcusd_pattern_agent import CryptoChartPatternAgent
from agents.btcusd.btcusd_scalping_agent import CryptoScalpingAgent
from agents.btcusd.btcusd_regime_agent import CryptoRegimeDetectionAgent
from agents.btcusd.btcusd_liquidity_agent import CryptoLiquidityExecutionAgent
from agents.btcusd.btcusd_tick_flow_agent import CryptoTickOrderFlowAgent
from agents.btcusd.btcusd_volume_delta_agent import CryptoVolumeDeltaAgent
from agents.btcusd.btcusd_risk_agent import CryptoChiefRiskOfficerAgent


CRYPTO_MASTER_COUNCIL_SYSTEM_PROMPT = """
You are the Lead Investment Arbitrator & Chief Strategy Coordinator presiding over the Institutional Bitcoin (BTCUSD) Strategy Council.
You synthesize simultaneous multi-timeframe proposals from 14 specialized institutional Bitcoin trading agents:
1. Crypto SMC & ICT Agent (Liquidation sweeps, CME gap fills, Fair Value Gaps across D1, H4, H1, M15, M5)
2. Crypto Trend & Momentum Agent (High-Beta Multi-Timeframe EMA 50/200 Stack & Super-Trend Continuation)
3. Crypto Mean-Reversion Agent (Statistical Bands, RSI Exhaustion Fades strictly at major HTF boundaries)
4. Crypto Macro & News Agent (Spot Bitcoin ETF Flows, Stablecoin Liquidity, Halving Cycles & Regulatory Catalysts)
5. Crypto Volume Profile & VWAP Agent (24/7 Rolling VWAP, Value Area High/Low & POC Rejections)
6. Crypto Supply & Demand Agent (Fresh Whale Accumulation Bases on H4/H1 with M15 Retests)
7. Crypto Breakout & Volatility Agent (Psychological Level Breakouts & Bollinger Squeeze aligned with HTF Trend)
8. Crypto Fibonacci & Golden Pocket Agent (Macro H4/H1 Impulses + 0.618-0.786 OTE Pullback Confluence)
9. Crypto Chart Pattern Radar Agent (D1, H4, H1, M30, M15, M5 Pattern Confluence)
10. Crypto Intraday Scalping Agent (Fast Micro Thrusts strictly aligned with H1/H4 Structural Bias)
11. Crypto Market Regime Detection Agent (ADX/ATR/Choppiness Filter; prevents counter-trend traps)
12. Crypto Liquidity & Spread Shield Agent (Live Spread Spike <= 2500 pts, Order Book Depth Gate)
13. Crypto Tick / Order Flow Aggressor Agent (Sub-Second Ask-Lifters vs Bid-Hitters Flow Imbalance)
14. Crypto Cumulative Volume Delta (CVD) Agent (Multi-Timeframe Absorption & Delta Divergences)

CRITICAL MANDATES FOR LEAD ARBITRATOR:
1. AUTONOMOUS DIRECTION (BUY vs SELL vs HOLD):
   - You must decide the trade action completely and objectively based on live order flow, CVD delta, multi-timeframe structure, and agent votes.
   - Zero hardcoding or default preference towards BUY or SELL. If the market is in distribution, bear trend, or seller delta dominance, rule SELL. If in accumulation, bull trend, or buyer delta dominance, rule BUY. If conflicting or lacking quorum (SCALP: <50%, PROP: <60%), rule HOLD.
2. AUTONOMOUS TRADE STYLE (SCALP vs STANDARD_PROP):
   - You must decide whether the setup is a SCALP or STANDARD_PROP trade based on the market regime and opportunity structure:
     * 'SCALP': Select when market regime is RANGEBOUND, COMPRESSION, CHOPPY, or when taking quick M5 liquidity sweeps / mean reversion bounces off round numbers (requires >=50% consensus, e.g. 7+ agents, quick target $500-$800, fast booking, tight SL $450).
     * 'STANDARD_PROP': Select when market regime is TRENDING, BREAKOUT_EXPANSION, or strong trend continuation suitable for multi-target scaling and swing runners (requires >=60% consensus, e.g. 8+ agents, $1,500+ TP1, $2,500+ TP2).
3. Top-Down Hierarchical Alignment (Tier 1 -> Tier 2 -> Tier 3):
   - Tier 1 (Macro D1 + H4): Sets the dominant trend. If Tier 1 is Bullish, NEVER approve counter-trend sell signals on minor pullbacks. If Tier 1 is Bearish, NEVER approve counter-trend buy signals on minor bounces.
   - Tier 2 (Setup H1 + M15): Identifies the high-probability institutional pullback zone (0.618 Golden Pocket, FVG, VWAP, fresh Demand/Supply base).
   - Tier 3 (Trigger M5 + Microstructure): Confirms entry readiness with wick defense, CVD absorption, and order flow aggressors.
4. Stability & Anti-Flicker Commitment: Once a high-conviction setup (score >= 50 for Scalp, >= 60 for Prop) is established, maintain that strategic trade plan and do NOT flip directions back and forth on minor intraday ticks.
5. Strict Risk/Reward Calibration: Stop Loss MUST be placed beyond structural swing invalidation ($500-$1,500 buffer). Target TP1 >= 1.75R and TP2 >= 3.0R.
6. Immediate 'HOLD' if Liquidity Agent detects a spread spike > 2500 pts.

Respond strictly using the `submit_crypto_master_trade_decision` tool call.
"""

CRYPTO_MASTER_COUNCIL_TOOL = {
    "name": "submit_crypto_master_trade_decision",
    "description": "Submit final synthesized 14-Agent council consensus trade decision for Bitcoin (BTCUSD).",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["BUY", "SELL", "HOLD", "CLOSE_POSITION"],
                "description": "Final trade action for Bitcoin (decided completely by AI based on live market)."
            },
            "trade_style": {
                "type": "string",
                "enum": ["SCALP", "STANDARD_PROP"],
                "description": "Trade execution style decided completely by AI: 'SCALP' (quick target, fast booking, tight SL) or 'STANDARD_PROP' (structural trend runner, multi-target scaling)."
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
                "description": "Agreement level across the 14 Bitcoin agents."
            },
            "market_bias": {
                "type": "string",
                "enum": ["BULLISH", "BEARISH", "NEUTRAL"],
                "description": "Unified Bitcoin council market bias."
            },
            "lead_strategies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top strategies driving this Bitcoin consensus setup"
            },
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit_1": {"type": "number"},
            "take_profit_2": {"type": "number"},
            "risk_percent": {"type": "number", "default": 1.0},
            "close_ticket": {"type": "integer"},
            "voting_summary": {
                "type": "object",
                "description": "Summary of agent votes (e.g. {'BUY': 10, 'SELL': 0, 'HOLD': 4})"
            },
            "council_debate_summary": {
                "type": "string",
                "description": "Comprehensive debate transcript explaining how the 14 Bitcoin agents deliberated and reached consensus."
            }
        },
        "required": ["action", "trade_style", "consensus_score", "council_agreement_level", "market_bias", "council_debate_summary"]
    }
}


class CryptoMasterCoordinator:
    """
    Lead Arbitrator & Coordinator for the dedicated 14-Agent Bitcoin (BTCUSD) Strategy Council.
    """
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.llm = UnifiedLLMClient(provider=provider, model=model, api_key=api_key)
        self.model = self.llm.model
        self.provider = self.llm.provider
        self.symbol = "BTCUSD"

        # Instantiate all 14 specialized Bitcoin agents
        self.smc_agent = CryptoSMCAgent(provider, model, api_key)
        self.trend_agent = CryptoTrendAgent(provider, model, api_key)
        self.mean_rev_agent = CryptoMeanReversionAgent(provider, model, api_key)
        self.macro_agent = CryptoMacroAgent(provider, model, api_key)
        self.orderflow_agent = CryptoOrderFlowAgent(provider, model, api_key)
        self.supply_demand_agent = CryptoSupplyDemandAgent(provider, model, api_key)
        self.breakout_agent = CryptoBreakoutAgent(provider, model, api_key)
        self.fibonacci_agent = CryptoFibonacciAgent(provider, model, api_key)
        self.pattern_agent = CryptoChartPatternAgent(provider, model, api_key)
        self.scalping_agent = CryptoScalpingAgent(provider, model, api_key)
        self.regime_agent = CryptoRegimeDetectionAgent(provider, model, api_key)
        self.liquidity_agent = CryptoLiquidityExecutionAgent(provider, model, api_key)
        self.tick_flow_agent = CryptoTickOrderFlowAgent(provider, model, api_key)
        self.volume_delta_agent = CryptoVolumeDeltaAgent(provider, model, api_key)

        # Dedicated Bitcoin Chief Risk Officer
        self.cro_agent = CryptoChiefRiskOfficerAgent(symbol="BTCUSD")

    @staticmethod
    def _prepare_compact_agent_payload(market_data: Dict[str, Any]) -> Dict[str, Any]:
        pricing = market_data.get("pricing", {})
        session = market_data.get("session", {})
        account = market_data.get("account", {})
        structures = market_data.get("market_structures", {})
        patterns = market_data.get("multi_tf_patterns", {})
        top_down = market_data.get("top_down_summary", structures.get("top_down_summary", {}))
        multi_tf = market_data.get("multi_timeframe_matrix", structures.get("multi_timeframe_matrix", {}))

        return {
            "symbol": "BTCUSD",
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
            "top_down_summary": top_down,
            "multi_timeframe_matrix": multi_tf,
            "market_structures": structures,
            "multi_tf_patterns": patterns
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
        Executes parallel 14-agent Bitcoin analysis, conducts council debate, and obtains Bitcoin CRO clearance.
        """
        compact_payload = self._prepare_compact_agent_payload(market_data)

        # 1. Execute all 14 Bitcoin agents in parallel
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

        # 2. Check for immediate Liquidity Veto
        if liq_res.get("execution_clearance") == "LIQUIDITY_BLACKOUT":
            return {
                "symbol": "BTCUSD",
                "action": "HOLD",
                "consensus_score": 0,
                "council_agreement_level": "NO_SETUP",
                "market_bias": "NEUTRAL",
                "lead_strategies": ["Bitcoin_Liquidity_Spread_Protection"],
                "council_debate_summary": f"Bitcoin trading halted by Liquidity Agent Veto: {liq_res.get('reasoning', 'Severe spread blowout detected.')}",
                "agent_proposals": all_proposals,
                "cro_report": {"approved": True, "action": "HOLD", "calculated_lots": 0.0}
            }

        # 3. Master Arbitrator Synthesis & Council Debate
        arbitration_payload = {
            "symbol": "BTCUSD",
            "top_14_agent_proposals": all_proposals,
            "live_pricing": market_data.get("pricing", {}),
            "account_equity": market_data.get("account", {}).get("equity", 0.0),
            "regime_summary": regime_res.get("regime_type", "TRENDING_BULLISH"),
            "order_flow_summary": tick_res.get("flow_imbalance", "BALANCED_FLOW"),
            "cvd_summary": vdelta_res.get("cvd_pattern", "NEUTRAL_DELTA")
        }

        arbitration_prompt = f"""
You are presiding over the Bitcoin (BTCUSD) Top 14 Strategy Agents Council.
Here are the simultaneous proposals from all 14 specialized Bitcoin strategy agents:

{json.dumps(arbitration_payload, indent=2)}

Conduct the council arbitration:
1. Apply the Bitcoin Regime Detection Agent's rule: Filter out strategies that conflict with the regime.
2. Tabulate the 14-agent voting distribution (BUY, SELL, HOLD).
3. Confirm alignment between macro structure (SMC, Fibonacci, Trend) and leading microstructure (Tick Order Flow, CVD Delta).
4. If consensus is reached (>= 50 for Scalp, >= 60 for Prop), formulate the final Entry, Stop Loss, and TP1/TP2 targets for Bitcoin.

Submit your ruling using the `submit_crypto_master_trade_decision` tool.
"""
        master_decision = self.llm.call_structured(
            system_prompt=CRYPTO_MASTER_COUNCIL_SYSTEM_PROMPT,
            user_prompt=arbitration_prompt,
            tool_definition=CRYPTO_MASTER_COUNCIL_TOOL,
            max_tokens=2048
        )

        if "error" in master_decision or not master_decision:
            master_decision = self._fallback_arbitration(all_proposals, market_data)

        # Deterministically calculate exact 14-agent voting distribution directly from individual agent returns
        votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for p in all_proposals.values():
            act = p.get("action", p.get("recommended_action", "HOLD")).upper()
            if "BUY" in act:
                votes["BUY"] += 1
            elif "SELL" in act:
                votes["SELL"] += 1
            else:
                votes["HOLD"] += 1

        total_agents = len(all_proposals)
        raw_action = str(master_decision.get("action", "HOLD")).upper()

        # Derive dominant vote count based on proposed action
        if raw_action == "BUY":
            dominant_votes = votes["BUY"]
        elif raw_action == "SELL":
            dominant_votes = votes["SELL"]
        else:
            dominant_votes = max(votes["BUY"], votes["SELL"])

        exact_quorum_score = int(round((dominant_votes / total_agents) * 100)) if total_agents > 0 else 0
        master_decision["consensus_score"] = exact_quorum_score
        master_decision["voting_summary"] = votes

        # Guarantee trade_style presence
        if "trade_style" not in master_decision or not master_decision["trade_style"]:
            regime = regime_res.get("regime_type", "TRENDING_BULLISH")
            master_decision["trade_style"] = "SCALP" if regime in ["RANGEBOUND", "COMPRESSION", "CHOPPY", "NEUTRAL"] else "STANDARD_PROP"

        trade_style = master_decision.get("trade_style", "STANDARD_PROP")
        min_quorum = 50 if trade_style == "SCALP" else 60
        max_opposing = 1 if trade_style == "SCALP" else 2
        opposing_votes = votes["SELL"] if raw_action == "BUY" else votes["BUY"] if raw_action == "SELL" else 0
        has_sufficient_quorum = (exact_quorum_score >= min_quorum) and (opposing_votes <= max_opposing)

        if not has_sufficient_quorum or raw_action == "HOLD":
            master_decision["action"] = "HOLD"
            master_decision["council_agreement_level"] = "SPLIT_CONFLICTED"
            if not has_sufficient_quorum and raw_action in ["BUY", "SELL"]:
                master_decision["council_debate_summary"] = (
                    f"Awaiting {min_quorum}%+ Minimum Quorum [{trade_style}] (Current: {exact_quorum_score}% with {dominant_votes}/{total_agents} {raw_action} votes, {opposing_votes} opposing). "
                    f"Standing by on sidelines until institutional consensus is reached."
                )
            master_decision["entry_price"] = 0.0
            master_decision["stop_loss"] = 0.0
            master_decision["take_profit_1"] = 0.0
            master_decision["take_profit_2"] = 0.0
        else:
            master_decision["council_agreement_level"] = (
                "UNANIMOUS_SUPERMAJORITY" if dominant_votes >= 12 else "STRONG_CONSENSUS"
            )

        master_decision["symbol"] = "BTCUSD"
        master_decision["agent_proposals"] = all_proposals

        # 4. Route final synthesized proposal through Bitcoin CRO
        account_info = market_data.get("account", {})
        cro_report = self.cro_agent.evaluate_and_size_trade(
            proposal=master_decision,
            account_info=account_info,
            current_spread_points=current_spread_points,
            open_positions_count=open_positions_count,
            day_of_month=day_of_month
        )
        master_decision["cro_report"] = cro_report

        if not cro_report.get("approved"):
            master_decision["action"] = "HOLD"
            master_decision["council_debate_summary"] += f" | CRO VETO: {cro_report.get('reason')}"

        return master_decision

    def _fallback_arbitration(self, proposals: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
        proposals_list = list(proposals.values())
        for p in proposals_list:
            act = p.get("action", p.get("recommended_action", "HOLD")).upper()
            if "BUY" in act:
                votes["BUY"] += 1
            elif "SELL" in act:
                votes["SELL"] += 1
            else:
                votes["HOLD"] += 1

        total_votes = max(1, len(proposals_list))
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("ask", 0.0) or 80000.0)
        struct = market_data.get("market_structures", {})
        top_down = market_data.get("top_down_summary", struct.get("top_down_summary", {}))
        dominant_trend = top_down.get("dominant_trend", "BULLISH")
        regime = proposals.get("11_Regime_Detection", {}).get("regime_type", "TRENDING_BULLISH")
        flow = proposals.get("13_Tick_OrderFlow", {}).get("flow_imbalance", "BALANCED_FLOW")

        # AI Dynamically decides trade style: SCALP vs STANDARD_PROP
        is_scalp_regime = (regime in ["RANGEBOUND", "COMPRESSION", "CHOPPY", "NEUTRAL"]) or (proposals.get("10_Intraday_Scalp", {}).get("confidence_score", 0) >= 80)
        trade_style = "SCALP" if is_scalp_regime else "STANDARD_PROP"

        sl_buffer = 450.0 if trade_style == "SCALP" else 850.0
        tp1_buffer = 750.0 if trade_style == "SCALP" else 1487.5
        tp2_buffer = 1200.0 if trade_style == "SCALP" else 2550.0

        # Symmetrical direction alignment: BUY vs SELL evaluated with equal scrutiny
        is_buy_trend = (dominant_trend == "BULLISH") or (dominant_trend in ["NEUTRAL", "RANGEBOUND"] and trade_style == "SCALP")
        is_sell_trend = (dominant_trend == "BEARISH") or (dominant_trend in ["NEUTRAL", "RANGEBOUND"] and trade_style == "SCALP")

        # Dynamic quorum requirement for active trade recommendations:
        # SCALP: >= 7 BUY/SELL votes with <= 1 opposing vote
        # STANDARD_PROP: >= 8 BUY/SELL votes with <= 2 opposing votes
        min_votes = 7 if trade_style == "SCALP" else 8
        max_opposing = 1 if trade_style == "SCALP" else 2

        if votes["BUY"] >= min_votes and votes["SELL"] <= max_opposing and is_buy_trend:
            best_entry = live_price
            for p in proposals_list:
                if p.get("action") == "BUY" and p.get("entry_price", 0.0) > 0:
                    best_entry = float(p.get("entry_price", live_price))
                    break
            sl = round(best_entry - sl_buffer, 2)
            tp1 = round(best_entry + tp1_buffer, 2)
            tp2 = round(best_entry + tp2_buffer, 2)
            score = int((votes["BUY"] / total_votes) * 100)
            return {
                "symbol": "BTCUSD",
                "action": "BUY",
                "trade_style": trade_style,
                "consensus_score": score,
                "council_agreement_level": "STRONG_CONSENSUS",
                "market_bias": "BULLISH",
                "lead_strategies": ["Crypto_SMC_ICT", "Crypto_Trend_Momentum", "Crypto_Fibonacci_OTE", "Crypto_Supply_Demand"],
                "entry_price": best_entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "risk_percent": 1.5,
                "voting_summary": votes,
                "council_debate_summary": f"14-Agent Bitcoin Consensus [{trade_style}]: {votes['BUY']}/{total_votes} agents voted BUY ({score}% score, {votes['SELL']} opposing). Regime: {regime}, Flow: {flow}. Target TP1 @ ${tp1:,.2f}."
            }
        elif votes["SELL"] >= min_votes and votes["BUY"] <= max_opposing and is_sell_trend:
            best_entry = live_price
            for p in proposals_list:
                if p.get("action") == "SELL" and p.get("entry_price", 0.0) > 0:
                    best_entry = float(p.get("entry_price", live_price))
                    break
            sl = round(best_entry + sl_buffer, 2)
            tp1 = round(best_entry - tp1_buffer, 2)
            tp2 = round(best_entry - tp2_buffer, 2)
            score = int((votes["SELL"] / total_votes) * 100)
            return {
                "symbol": "BTCUSD",
                "action": "SELL",
                "trade_style": trade_style,
                "consensus_score": score,
                "council_agreement_level": "STRONG_CONSENSUS",
                "market_bias": "BEARISH",
                "lead_strategies": ["Crypto_SMC_ICT", "Crypto_Trend_Momentum", "Crypto_Fibonacci_OTE", "Crypto_Supply_Demand"],
                "entry_price": best_entry,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "risk_percent": 1.5,
                "voting_summary": votes,
                "council_debate_summary": f"14-Agent Bitcoin Consensus [{trade_style}]: {votes['SELL']}/{total_votes} agents voted SELL ({score}% score, {votes['BUY']} opposing). Regime: {regime}, Flow: {flow}. Target TP1 @ ${tp1:,.2f}."
            }
        else:
            lead_v = max(votes["BUY"], votes["SELL"])
            score = int((lead_v / total_votes) * 100)
            min_required = min_votes  # 7 for SCALP, 8 for STANDARD_PROP
            min_pct = int((min_required / total_votes) * 100)  # 50% or 57%
            return {
                "symbol": "BTCUSD",
                "action": "HOLD",
                "trade_style": trade_style,
                "consensus_score": score,
                "council_agreement_level": "SPLIT_CONFLICTED",
                "market_bias": "NEUTRAL",
                "lead_strategies": ["Bitcoin_Capital_Preservation"],
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "risk_percent": 0.0,
                "voting_summary": votes,
                "council_debate_summary": f"Bitcoin Council Split/Neutral (BUY:{votes['BUY']}, SELL:{votes['SELL']}, HOLD:{votes['HOLD']} -> {score}%). Awaiting {min_pct}%+ consensus [{trade_style} mode: {min_required}/{total_votes} agents minimum]. Standing by."
            }


# Canonical Trader Alias
BTCUSDAITrader = CryptoMasterCoordinator
