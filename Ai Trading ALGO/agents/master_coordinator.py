"""
Master Strategy Coordinator & Lead Arbitrator for the Top 10 Strategy Agents Council.
Orchestrates parallel execution of all 10 specialized trading agents, conducts the council debate,
evaluates the 10-agent voting matrix and quorum consensus, and routes cleared trades through the CRO.
"""

import json
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
import anthropic

from config import CONFIG, get_model_api_kwargs
from core.gatekeeper import Gatekeeper, build_snapshot_from_payload
from core.trade_plan import DailyPlan, TradePlan, GateResult, KeyLevel, BlackoutWindow, TradeBias, TradeDirection, VoteChoice
from core.vote_validator import validate_agent_output
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
from core.market_research_terminal import MarketResearchTerminal


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
6. In-Trade Position Health Surveillance: If active open trades exist, evaluate whether the original trade thesis is still HEALTHY, DEGRADING, or INVALIDATED. If market structure breaks against the trade (e.g. broken neckline, opposing M1/M5 momentum burst, CVD divergence), declare 'INVALIDATED' and recommended_management 'EARLY_CUT' with action 'CLOSE_POSITION' so losses are cut small (-0.30R to -0.50R) instead of letting them hit full Stop Loss!

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
            "trade_health": {
                "type": "string",
                "enum": ["HEALTHY", "DEGRADING", "INVALIDATED", "FLAT"],
                "description": "Surveillance health verdict for active trade."
            },
            "recommended_management": {
                "type": "string",
                "enum": ["HOLD_FOR_TARGET", "TIGHTEN_TRAIL", "EARLY_CUT", "NONE"],
                "description": "Active management recommendation."
            },
            "dynamic_sl_target": {
                "type": "number",
                "description": "Recommended trailing stop price based on M1/M5 swing structure."
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
        # Phase 2 Staged Institutional Pipeline State
        self.gatekeeper = Gatekeeper()
        self.research_terminal = MarketResearchTerminal(symbol=CONFIG.SYMBOL)
        self.current_daily_plan: Optional[DailyPlan] = None
        self.daily_plan_updated_at: float = 0.0
        self.last_loss_utc: str = "" 

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
        Master decision router:
        - If PIPELINE_MODE == 'staged': runs deterministic sequential staged pipeline.
        - If PIPELINE_MODE == 'legacy': runs parallel 14-agent quorum consensus.
        """
        # Autonomous 360-degree Top-Down Market Research (1Y to 5M charts, Global News Shocks)
        try:
            pricing = market_data.get("pricing", {})
            current_price = float(pricing.get("bid", 0.0) or pricing.get("price", 0.0) or 0.0)
            dossier = self.research_terminal.conduct_complete_research(live_price=current_price)
            dossier_dict = {
                "shock_threat_level": dossier.shock_report.shock_threat_level,
                "global_shock_score": dossier.shock_report.global_shock_score,
                "gold_macro_bias": dossier.shock_report.gold_macro_bias,
                "blackout_active": dossier.shock_report.blackout_active,
                "blackout_reason": dossier.shock_report.blackout_reason,
                "active_shocks": dossier.shock_report.active_shocks_detected,
                "fractal_alignment_pct": dossier.fractal_alignment_pct,
                "institutional_action_clearance": dossier.institutional_action_clearance,
                "dominant_market_regime": dossier.dominant_market_regime,
                "multi_tf_matrix": [
                    {"tf": tf.timeframe, "trend": tf.trend_bias, "change_pct": tf.change_pct, "summary": tf.narrative_summary}
                    for tf in dossier.multi_tf_analysis
                ],
                "executive_narrative": dossier.executive_narrative
            }
            market_data["market_research_dossier"] = dossier_dict
            news_data["research_dossier"] = dossier_dict
            if dossier.shock_report.blackout_active:
                news_data["news_blackout_active"] = True
                news_data["blackout_reason"] = dossier.shock_report.blackout_reason
        except Exception as e:
            print(f"[MasterCoordinator] Research terminal scan note: {e}")

        mode = getattr(CONFIG, "PIPELINE_MODE", "staged").lower()
        if mode == "staged":
            return self._run_staged_pipeline(
                market_data=market_data,
                news_data=news_data,
                current_spread_points=current_spread_points,
                open_positions_count=open_positions_count,
                day_of_month=day_of_month
            )
        else:
            return self._run_legacy_pipeline(
                market_data=market_data,
                news_data=news_data,
                current_spread_points=current_spread_points,
                open_positions_count=open_positions_count,
                day_of_month=day_of_month
            )

    def _get_or_update_daily_plan(self, market_data: Dict[str, Any], news_data: Dict[str, Any]) -> DailyPlan:
        """
        Stage 0: Daily/Session Briefing (refreshed every 4 hours or new session).
        Extracts D1/H4 trends, H4 regime, mapped key levels (3 above, 3 below),
        premium/discount calculation, and blackout windows.
        """
        now_ts = time.time()
        if self.current_daily_plan and (now_ts - self.daily_plan_updated_at < 14400):
            return self.current_daily_plan

        radar = market_data.get("multi_tf_patterns", {})
        tfs = radar.get("timeframes", {})
        d1_trend = str(tfs.get("D1", {}).get("bias", "NEUTRAL")).upper()
        h4_trend = str(tfs.get("H4", {}).get("bias", "NEUTRAL")).upper()
        regime_ctx = market_data.get("regime_analysis", {})
        h4_regime = str(regime_ctx.get("h4_regime") or regime_ctx.get("regime", "UNKNOWN")).upper()

        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("price", 0.0) or 0.0)
        d1_meta = tfs.get("D1", {}).get("institutional_meta", {})
        range_high = float(d1_meta.get("range_high", live_price + 50.0) or (live_price + 50.0))
        range_low = float(d1_meta.get("range_low", max(1.0, live_price - 50.0)) or max(1.0, live_price - 50.0))

        if range_high > range_low:
            premium_discount_pct = round(((live_price - range_low) / (range_high - range_low)) * 100.0, 1)
        else:
            premium_discount_pct = 50.0

        # Extract Key Levels (S&D zones + Fibonacci)
        sd_data = market_data.get("market_structures", {}).get("supply_demand_zones", {})
        key_levels: List[KeyLevel] = []

        for z in sd_data.get("supply_zones", [])[:3]:
            p = float(z.get("high", z.get("mid", 0.0)) or 0.0)
            if p > 0:
                key_levels.append(KeyLevel(price=p, level_type="SUPPLY", source="S&D Box", strength=85))
        for z in sd_data.get("demand_zones", [])[:3]:
            p = float(z.get("low", z.get("mid", 0.0)) or 0.0)
            if p > 0:
                key_levels.append(KeyLevel(price=p, level_type="DEMAND", source="S&D Box", strength=85))

        fibo_data = market_data.get("market_structures", {}).get("fibonacci_levels", {})
        for lvl_name in ["golden_0_618", "ote_0_705", "reversal_0_786"]:
            fp = float(fibo_data.get(lvl_name, 0.0) or 0.0)
            if fp > 0:
                key_levels.append(KeyLevel(price=fp, level_type="FIBO", source=lvl_name, strength=80))

        unique_levels = {}
        for kl in key_levels:
            r_p = round(kl.price, 1)
            if r_p not in unique_levels:
                unique_levels[r_p] = kl
        sorted_levels = sorted(unique_levels.values(), key=lambda x: x.price)

        blackout_windows: List[BlackoutWindow] = []
        for ev in news_data.get("upcoming_events", []):
            if str(ev.get("impact", "")).upper() in ["HIGH", "RED"]:
                blackout_windows.append(BlackoutWindow(
                    start_utc=str(ev.get("start_utc", "")),
                    end_utc=str(ev.get("end_utc", "")),
                    event=str(ev.get("event", "High Impact News")),
                    impact="HIGH"
                ))

        # Macro Bias Rule: D1 and H4 conflict -> NO_TRADE
        if d1_trend == "BEARISH" and h4_trend == "BEARISH":
            bias = TradeBias.SELL_RALLIES
        elif d1_trend == "BULLISH" and h4_trend == "BULLISH":
            bias = TradeBias.BUY_DIPS
        else:
            bias = TradeBias.NO_TRADE

        daily_plan = DailyPlan(
            bias=bias,
            d1_trend=d1_trend,
            h4_trend=h4_trend,
            h4_regime=h4_regime,
            premium_discount_pct=premium_discount_pct,
            key_levels=sorted_levels,
            blackout_windows=blackout_windows,
            session=market_data.get("session", "LONDON_NY_OVERLAP"),
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            notes=f"D1={d1_trend} | H4={h4_trend} | H4_Regime={h4_regime} | Prem/Disc={premium_discount_pct}%"
        )
        self.current_daily_plan = daily_plan
        self.daily_plan_updated_at = now_ts
        return daily_plan

    def _build_standby_decision(
        self,
        action: str,
        reason: str,
        market_data: Dict[str, Any],
        daily_plan: Optional[DailyPlan] = None,
        gate_result: Optional[GateResult] = None,
        trade_plan: Optional[TradePlan] = None
    ) -> Dict[str, Any]:
        """Builds a standardized HOLD/STANDBY decision matching UI and execution contracts."""
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("price", 0.0) or 0.0)

        # Audit log decision to AI Ledger
        stage_num = 0
        failed_gate_name = gate_result.failed_gate if gate_result is not None else None
        if gate_result is not None:
            if failed_gate_name == "MACRO_HARMONY" and "STAGE 0" in reason:
                stage_num = 0
            elif failed_gate_name in ["NEWS_BLACKOUT", "LIQUIDITY", "SPREAD", "H4_REGIME", "ACCOUNT_SAFETY"]:
                stage_num = 1
            elif failed_gate_name in ["LOCATION_PROXIMITY", "PREMIUM_DISCOUNT"]:
                stage_num = 2
            elif failed_gate_name in ["ORDER_FLOW_TRIGGER", "NO_CHASE", "CLOSED_M5_CANDLE"]:
                stage_num = 3
            else:
                stage_num = 1

        try:
            from core.ai_ledger import AITradeLedger
            AITradeLedger.record_staged_decision(
                symbol=getattr(self, "symbol", "XAUUSD"),
                stage_reached=stage_num,
                status="VETOED",
                failed_gate=failed_gate_name,
                reason=reason,
                daily_plan=daily_plan.__dict__ if daily_plan is not None else None,
                trade_plan=trade_plan.to_dict() if trade_plan is not None else None,
                cro_report={"approved": False, "reason": reason, "position_size_lots": 0.0},
                live_price=live_price,
            )
        except Exception:
            pass

        return {
            "action": action,
            "confidence": 0,
            "consensus_score": 0,
            "council_agreement_level": "STAGE_GATED_STANDBY",
            "council_debate_summary": reason,
            "entry_price": trade_plan.entry_price if trade_plan is not None else live_price,
            "stop_loss": trade_plan.stop_price if trade_plan is not None else 0.0,
            "take_profit_1": trade_plan.target_1 if trade_plan is not None else 0.0,
            "take_profit_2": trade_plan.target_2 if trade_plan is not None else 0.0,
            "risk_reward_ratio": trade_plan.rr if trade_plan is not None else 0.0,
            "daily_plan": daily_plan.__dict__ if daily_plan is not None else None,
            "gate_result": gate_result.__dict__ if gate_result is not None else None,
            "trade_plan": trade_plan.to_dict() if trade_plan else None,
            "cro_report": {"approved": False, "reason": reason, "position_size_lots": 0.0},
            "agent_proposals": {},
            "pipeline_mode": "staged"
        }

    def _run_staged_pipeline(
        self,
        market_data: Dict[str, Any],
        news_data: Dict[str, Any],
        current_spread_points: float,
        open_positions_count: int,
        day_of_month: int
    ) -> Dict[str, Any]:
        """
        Executes the human pro trader sequential pipeline:
        Stage 0: Daily/Session Briefing (Macro Bias & Key Levels)
        Stage 1: Pure Deterministic Permission Gates (News, Liquidity, Regime, Harmony, Account)
        Stage 2: Location Gate (Key Level proximity & Premium/Discount)
        Stage 3: Trigger Gate (Candle close & Order Flow Imbalance)
        Stage 4: Risk Gate (CRO Sizing & TradePlan assembly)
        """
        # --- Stage 0: Daily Plan ---
        daily_plan = self._get_or_update_daily_plan(market_data, news_data)

        if daily_plan.bias == TradeBias.NO_TRADE:
            reason = f"[STAGE 0 VETO]: Macro Disagreement — D1 ({daily_plan.d1_trend}) opposes H4 ({daily_plan.h4_trend}). Standing aside."
            return self._build_standby_decision(
                action="HOLD",
                reason=reason,
                market_data=market_data,
                daily_plan=daily_plan,
                gate_result=GateResult(passed=False, failed_gate="MACRO_HARMONY", reason=reason)
            )

        target_direction = "BUY" if daily_plan.bias == TradeBias.BUY_DIPS else "SELL"

        # --- Stage 1: Permission Gates (Pure code, no LLM) ---
        account_info = market_data.get("account", {})
        balance = float(account_info.get("balance", 1000.0) or 1000.0)
        equity = float(account_info.get("equity", balance) or balance)
        daily_dd_pct = max(0.0, (balance - equity) / max(balance, 1.0) * 100.0)

        snapshot = build_snapshot_from_payload(
            market_payload=market_data,
            news_payload=news_data,
            daily_plan=daily_plan,
            open_positions_count=open_positions_count,
            daily_dd_pct=daily_dd_pct,
            last_loss_utc=self.last_loss_utc
        )
        gate_res = self.gatekeeper.check_all(snapshot, target_direction)
        if not gate_res.passed:
            reason = f"[STAGE 1 GATE VETO - {gate_res.failed_gate}]: {gate_res.reason}"
            return self._build_standby_decision(
                action="HOLD",
                reason=reason,
                market_data=market_data,
                daily_plan=daily_plan,
                gate_result=gate_res
            )

        # --- Stage 2: Location Gate (Key Level Proximity & Premium/Discount) ---
        pricing = market_data.get("pricing", {})
        live_price = float(pricing.get("bid", 0.0) or pricing.get("price", 0.0) or 0.0)
        struct_m15 = market_data.get("market_structures", {}).get("m15_execution_structure", {})
        atr = float(struct_m15.get("atr_14", 6.50) or 6.50)
        max_level_dist = float(getattr(CONFIG, "ATR_ZONE_DISTANCE_MULTIPLIER", 1.0)) * atr

        nearest_lvl = daily_plan.nearest_level(live_price)
        dist_to_lvl = daily_plan.distance_to_nearest_level(live_price)

        if dist_to_lvl > max_level_dist:
            lvl_p_str = f"{nearest_lvl.price:.2f}" if nearest_lvl else "None"
            reason = f"[STAGE 2 LOCATION]: Live price {live_price:.2f} is mid-range ({dist_to_lvl:.1f} pts from nearest key level {lvl_p_str}, allowed {max_level_dist:.1f} pts). Standing by."
            return self._build_standby_decision(
                action="HOLD",
                reason=reason,
                market_data=market_data,
                daily_plan=daily_plan,
                gate_result=GateResult(passed=False, failed_gate="LOCATION_PROXIMITY", reason=reason)
            )

        # Premium / Discount Rule
        if target_direction == "BUY" and daily_plan.in_premium_zone():
            reason = f"[STAGE 2 VETO]: Buying forbidden in Premium zone ({daily_plan.premium_discount_pct:.1f}% > 50%)."
            return self._build_standby_decision(
                action="HOLD",
                reason=reason,
                market_data=market_data,
                daily_plan=daily_plan,
                gate_result=GateResult(passed=False, failed_gate="PREMIUM_DISCOUNT", reason=reason)
            )
        if target_direction == "SELL" and daily_plan.in_discount_zone():
            reason = f"[STAGE 2 VETO]: Selling forbidden in Discount zone ({daily_plan.premium_discount_pct:.1f}% < 50%)."
            return self._build_standby_decision(
                action="HOLD",
                reason=reason,
                market_data=market_data,
                daily_plan=daily_plan,
                gate_result=GateResult(passed=False, failed_gate="PREMIUM_DISCOUNT", reason=reason)
            )

        # --- Stage 3: Trigger & Microstructure Check ---
        tick_flow_data = market_data.get("market_structures", {}).get("tick_order_flow", {})
        lifters_pct = float(tick_flow_data.get("ask_lifters_pct", 50.0) or 50.0)
        hitters_pct = float(tick_flow_data.get("bid_hitters_pct", 50.0) or 50.0)

        min_lifters = float(getattr(CONFIG, "MIN_ORDERFLOW_LIFTERS_PCT", 55.0))
        min_hitters = float(getattr(CONFIG, "MIN_ORDERFLOW_HITTERS_PCT", 55.0))

        if target_direction == "BUY" and lifters_pct < min_lifters:
            reason = f"[STAGE 3 VETO]: Order flow ask-lifters ({lifters_pct:.1f}%) < minimum required ({min_lifters:.1f}%)."
            return self._build_standby_decision(
                action="HOLD",
                reason=reason,
                market_data=market_data,
                daily_plan=daily_plan,
                gate_result=GateResult(passed=False, failed_gate="ORDER_FLOW_TRIGGER", reason=reason)
            )
        if target_direction == "SELL" and hitters_pct < min_hitters:
            reason = f"[STAGE 3 VETO]: Order flow bid-hitters ({hitters_pct:.1f}%) < minimum required ({min_hitters:.1f}%)."
            return self._build_standby_decision(
                action="HOLD",
                reason=reason,
                market_data=market_data,
                daily_plan=daily_plan,
                gate_result=GateResult(passed=False, failed_gate="ORDER_FLOW_TRIGGER", reason=reason)
            )

        # Construct single candidate TradePlan anchored to the nearest key level
        lvl_p = nearest_lvl.price if nearest_lvl else live_price
        entry_p = live_price
        sl_dist = max(4.5, min(7.0, atr * 0.9))

        if target_direction == "BUY":
            stop_p = round(entry_p - sl_dist, 2)
            tp1_p = round(entry_p + (sl_dist * 1.75), 2)
            tp2_p = round(entry_p + (sl_dist * 3.0), 2)
            trade_dir = TradeDirection.BUY
        else:
            stop_p = round(entry_p + sl_dist, 2)
            tp1_p = round(entry_p - (sl_dist * 1.75), 2)
            tp2_p = round(entry_p - (sl_dist * 3.0), 2)
            trade_dir = TradeDirection.SELL

        rr = round(abs(tp1_p - entry_p) / max(0.01, abs(entry_p - stop_p)), 2)

        trade_plan = TradePlan(
            direction=trade_dir,
            entry_zone_low=round(min(entry_p - 1.0, lvl_p - 1.0), 2),
            entry_zone_high=round(max(entry_p + 1.0, lvl_p + 1.0), 2),
            entry_price=round(entry_p, 2),
            stop_price=stop_p,
            target_1=tp1_p,
            target_2=tp2_p,
            rr=rr,
            invalidation_reason=f"Break of structural level @ {stop_p:.2f}",
            source_setup=f"{nearest_lvl.source if nearest_lvl else 'Key_Level'}_{target_direction}",
            atr_at_signal=atr,
            key_level_touched=nearest_lvl
        )

        # --- Stage 4: Risk Evaluation via Chief Risk Officer (CRO) ---
        cro_report = self.cro_agent.evaluate_and_size_trade(
            proposal={
                "action": target_direction,
                "entry_price": trade_plan.entry_price,
                "stop_loss": trade_plan.stop_price,
                "take_profit_1": trade_plan.target_1,
                "take_profit_2": trade_plan.target_2,
                "risk_reward_ratio": trade_plan.rr,
                "confidence_score": 88
            },
            account_info=account_info,
            current_spread_points=current_spread_points,
            open_positions_count=open_positions_count,
            day_of_month=day_of_month
        )

        final_action = target_direction if cro_report.get("approved", False) else "HOLD"
        summary = f"[STAGED PIPELINE APPROVED]: All gates & stages passed. Direction={target_direction} @ {trade_plan.entry_price:.2f}, SL={trade_plan.stop_price:.2f}, TP1={trade_plan.target_1:.2f} ({trade_plan.rr}R)."
        if final_action == "HOLD":
            summary = f"[CRO VETO]: {cro_report.get('reason')}"

        try:
            from core.ai_ledger import AITradeLedger
            AITradeLedger.record_staged_decision(
                symbol=self.symbol,
                stage_reached=4,
                status="EXECUTED" if final_action != "HOLD" else "VETOED",
                failed_gate=None if final_action != "HOLD" else "CRO_RISK",
                reason=summary,
                daily_plan=daily_plan.__dict__ if daily_plan else None,
                trade_plan=trade_plan.to_dict(),
                cro_report=cro_report,
                live_price=trade_plan.entry_price,
            )
        except Exception:
            pass

        return {
            "action": final_action,
            "confidence": 88 if final_action != "HOLD" else 0,
            "consensus_score": 88 if final_action != "HOLD" else 0,
            "council_agreement_level": "STAGED_DETERMINISTIC_GATES_PASSED" if final_action != "HOLD" else "CRO_VETOED",
            "council_debate_summary": summary,
            "entry_price": trade_plan.entry_price,
            "stop_loss": trade_plan.stop_price,
            "take_profit_1": trade_plan.target_1,
            "take_profit_2": trade_plan.target_2,
            "risk_reward_ratio": trade_plan.rr,
            "trade_plan": trade_plan.to_dict(),
            "daily_plan": daily_plan.__dict__,
            "cro_report": cro_report,
            "gate_result": gate_res.__dict__,
            "agent_proposals": {},
            "pipeline_mode": "staged"
        }

    def _run_legacy_pipeline(
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
            "active_open_positions": market_data.get("open_positions", []),
            "micro_structures": market_data.get("market_structures", {}).get("micro_structures", {}),
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
4. If no position is open and consensus is reached (>= 75 score), formulate the final Entry, Stop Loss, and TP1/TP2 targets.
5. If an active position is currently open, perform an In-Trade Position Health Audit:
   - Output `trade_health` (HEALTHY, DEGRADING, INVALIDATED).
   - If thesis is broken on M1/M5, set `recommended_management: EARLY_CUT` and `action: CLOSE_POSITION` to cut losses small (-0.30R to -0.50R) rather than taking full Stop Loss!
   - If thesis is winning, output `recommended_management: TIGHTEN_TRAIL` with `dynamic_sl_target` trailing behind M1/M5 micro swing lows.

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
            tp1_p = round(entry_p + (risk * 2.00), 2)
            tp2_p = round(entry_p + (risk * 3.50), 2)
            # Guarantee positive numbers and correct order
            if sl_p <= 0 or sl_p >= entry_p or tp1_p <= entry_p or tp2_p <= tp1_p:
                sl_p = round(entry_p - default_sl, 2)
                tp1_p = round(entry_p + (default_sl * 1.75), 2)
                tp2_p = round(entry_p + (default_sl * 3.00), 2)
        else:
            sl_p = round(entry_p + risk, 2)
            tp1_p = round(entry_p - (risk * 2.00), 2)
            tp2_p = round(entry_p - (risk * 3.50), 2)
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

        # 1. Extract Regime, Equilibrium, and Microstructure Context
        regime_prop = proposals.get("11_Regime_Detection", {})
        regime_type = str(regime_prop.get("regime_type", "TRENDING_BULLISH")).upper()
        
        tick_prop = proposals.get("13_Tick_OrderFlow", {})
        flow_imbalance = str(tick_prop.get("flow_imbalance", "BALANCED_FLOW")).upper()
        bid_pct = float(tick_prop.get("bid_hitters_pct", 50.0) or 50.0)
        ask_pct = float(tick_prop.get("ask_lifters_pct", 50.0) or 50.0)

        vdelta_prop = proposals.get("14_Volume_Delta_CVD", {})
        cvd_pattern = str(vdelta_prop.get("cvd_pattern", "NEUTRAL_DELTA")).upper()

        eq_data = market_data.get("institutional_equilibrium", {}) or market_data.get("market_structures", {}).get("institutional_equilibrium", {})
        zone_name = eq_data.get("zone", "EQUILIBRIUM")
        buying_permitted = eq_data.get("buying_permitted", True)
        selling_permitted = eq_data.get("selling_permitted", True)

        m5_struct = market_data.get("market_structures", {}).get("m5_micro_momentum", {})
        m5_cross = m5_struct.get("fast_cross", "BULLISH")

        total_agents = max(1, len(proposals))
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

            # Institutional Regime Gating Rules (HARD VETO)
            if "TRENDING_BEARISH" in regime_type and "BUY" in act:
                act = "HOLD"  # Hard veto: buying in a confirmed bearish trend is suicidal
            elif "TRENDING_BULLISH" in regime_type and "SELL" in act:
                act = "HOLD"  # Hard veto: shorting in a confirmed bullish trend is suicidal
            elif "MEAN_REVERTING_RANGE" in regime_type and "Breakout" in k:
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
            min_sl_dist = 4.50
            max_sl_dist = 7.00
            default_sl_dist = 5.50
        elif is_btc:
            min_sl_dist = 350.0
            max_sl_dist = 850.0
            default_sl_dist = 500.0
        else:
            min_sl_dist = max(0.10, live_price * 0.0025)
            max_sl_dist = max(0.50, live_price * 0.0080)
            default_sl_dist = max(0.25, live_price * 0.0040)

        # Active position health surveillance
        open_pos = market_data.get("open_positions", [])
        trade_health = "FLAT"
        rec_management = "NONE"
        dynamic_sl_target = 0.0

        if open_pos:
            p0 = open_pos[0]
            p_type = p0.get("type", "BUY").upper()
            p_open = float(p0.get("open_price", live_price) or live_price)
            micro = market_data.get("market_structures", {}).get("micro_structures", {})
            p_gain = (live_price - p_open) if p_type == "BUY" else (p_open - live_price)

            if p_type == "BUY":
                if sell_votes >= 6 and p_gain < -2.0:
                    trade_health = "INVALIDATED"
                    rec_management = "EARLY_CUT"
                elif sell_votes >= 4:
                    trade_health = "DEGRADING"
                    rec_management = "TIGHTEN_TRAIL"
                    dynamic_sl_target = micro.get("last_m5_low", live_price - 2.50)
                else:
                    trade_health = "HEALTHY"
                    rec_management = "HOLD_FOR_TARGET"
                    dynamic_sl_target = micro.get("last_m5_low", live_price - 2.80)
            else: # SELL
                if buy_votes >= 6 and p_gain < -2.0:
                    trade_health = "INVALIDATED"
                    rec_management = "EARLY_CUT"
                elif buy_votes >= 4:
                    trade_health = "DEGRADING"
                    rec_management = "TIGHTEN_TRAIL"
                    dynamic_sl_target = micro.get("last_m5_high", live_price + 2.50)
                else:
                    trade_health = "HEALTHY"
                    rec_management = "HOLD_FOR_TARGET"
                    dynamic_sl_target = micro.get("last_m5_high", live_price + 2.80)

        # 2. Institutional Pullback Entry Formulation & Consensus Resolution
        # A. Bullish Confluence
        if buy_votes >= 4 and buy_votes >= int(sell_votes * 1.5):
            avg_conf = sum(buy_confidences) / max(1, len(buy_confidences))
            consensus_score = min(98, max(75, int((buy_votes / float(total_agents)) * 100 + (avg_conf * 0.15))))

            if not buying_permitted:
                # Live price is in Premium (Whale distribution area). Do NOT market buy at highs!
                # Anchor planned entry to discount equilibrium pullback zone
                eq_price = float(eq_data.get("equilibrium_price") or eq_data.get("equilibrium") or (live_price - 2.5))
                entry_p = round(min(eq_price, live_price - 1.20), 2)
                raw_sl = min(buy_sls) if buy_sls else (entry_p - default_sl_dist)
                risk = max(min_sl_dist, min(max_sl_dist, abs(entry_p - raw_sl)))
                sl_p = round(entry_p - risk, 2)
                tp1_p = round(entry_p + (risk * 2.00), 2)
                tp2_p = round(entry_p + (risk * 3.50), 2)
                rr_ratio = round(abs(tp1_p - entry_p) / risk, 2)

                return {
                    "action": "BUY",
                    "consensus_score": consensus_score,
                    "council_agreement_level": "HUNTING_DISCOUNT_PULLBACK",
                    "market_bias": "BULLISH",
                    "trade_health": trade_health,
                    "recommended_management": rec_management,
                    "dynamic_sl_target": dynamic_sl_target,
                    "lead_strategies": ["Institutional Pullback Hunting", f"Regime_{regime_type}", f"Zone_{zone_name}"],
                    "entry_price": entry_p,
                    "stop_loss": sl_p,
                    "take_profit_1": tp1_p,
                    "take_profit_2": tp2_p,
                    "risk_reward_ratio": rr_ratio,
                    "invalidation_condition": f"M15 close below structural support at {sl_p:,.2f}",
                    "voting_summary": voting_summary,
                    "council_debate_summary": f"🏛️ Institutional Auction Planning: Council is BULLISH ({buy_votes} Buy votes, {consensus_score}% score). Live price is at {zone_name} ({eq_data.get('zone_pct', 80):.0f}% of range). Direct market buy prohibited (whale distribution area). Planned Entry anchored to Discount Pullback @ ${entry_p:,.2f} | SL: ${sl_p:,.2f} | TP1: ${tp1_p:,.2f}. 5-Min Sniper Watcher active to confirm pullback entry."
                }
            elif m5_cross == "BEARISH" and bid_pct >= 62.0:
                # Waterfall Dump Veto: heavy seller delta
                return {
                    "action": "HOLD",
                    "consensus_score": 35,
                    "council_agreement_level": "WATERFALL_DUMP_VETO",
                    "market_bias": "NEUTRAL",
                    "trade_health": trade_health,
                    "recommended_management": rec_management,
                    "dynamic_sl_target": dynamic_sl_target,
                    "entry_price": live_price,
                    "stop_loss": 0.0,
                    "take_profit_1": 0.0,
                    "take_profit_2": 0.0,
                    "risk_reward_ratio": 0.0,
                    "voting_summary": voting_summary,
                    "council_debate_summary": f"🛡️ Falling Knife Veto: {buy_votes} agents voted BUY, but M5 EMA 9 < 21 with heavy seller delta ({bid_pct:.0f}% Bid Hitters). Entry blocked until seller absorption completes."
                }
            else:
                # Direct Buy Signal (in Discount / Equilibrium)
                entry_p = round(sum(buy_entries) / len(buy_entries), 2) if buy_entries else round(live_price - 0.50, 2)
                raw_sl = min(buy_sls) if buy_sls else (entry_p - default_sl_dist)
                risk = max(min_sl_dist, min(max_sl_dist, abs(entry_p - raw_sl)))
                sl_p = round(entry_p - risk, 2)
                tp1_p = round(entry_p + (risk * 2.00), 2)
                tp2_p = round(entry_p + (risk * 3.50), 2)
                rr_ratio = round(abs(tp1_p - entry_p) / risk, 2)

                return {
                    "action": "BUY",
                    "consensus_score": consensus_score,
                    "council_agreement_level": "UNANIMOUS_SUPERMAJORITY" if buy_votes >= 8 else "STRONG_CONSENSUS",
                    "market_bias": "BULLISH",
                    "trade_health": trade_health,
                    "recommended_management": rec_management,
                    "dynamic_sl_target": dynamic_sl_target,
                    "lead_strategies": ["Multi-Agent Institutional Confluence", f"Regime_{regime_type}", f"Zone_{zone_name}"],
                    "entry_price": entry_p,
                    "stop_loss": sl_p,
                    "take_profit_1": tp1_p,
                    "take_profit_2": tp2_p,
                    "risk_reward_ratio": rr_ratio,
                    "invalidation_condition": f"M15 close below structural support at {sl_p:,.2f}",
                    "voting_summary": voting_summary,
                    "council_debate_summary": f"14-Agent Consensus: {buy_votes}/14 agents voted BUY ({consensus_score}% score). Zone: {zone_name}, Regime: {regime_type}. Target TP1 @ {tp1_p:,.2f} (1.75R) & TP2 @ {tp2_p:,.2f} (3.0R)."
                }

        # B. Bearish Confluence
        elif sell_votes >= 4 and sell_votes >= int(buy_votes * 1.5):
            avg_conf = sum(sell_confidences) / max(1, len(sell_confidences))
            consensus_score = min(98, max(75, int((sell_votes / float(total_agents)) * 100 + (avg_conf * 0.15))))

            if not selling_permitted:
                # Live price is in Discount (Whale accumulation area). Do NOT market short at lows!
                # Anchor planned entry to premium equilibrium pullback zone
                eq_price = float(eq_data.get("equilibrium_price") or eq_data.get("equilibrium") or (live_price + 2.5))
                entry_p = round(max(eq_price, live_price + 1.20), 2)
                raw_sl = max(sell_sls) if sell_sls else (entry_p + default_sl_dist)
                risk = max(min_sl_dist, min(max_sl_dist, abs(raw_sl - entry_p)))
                sl_p = round(entry_p + risk, 2)
                tp1_p = round(entry_p - (risk * 2.00), 2)
                tp2_p = round(entry_p - (risk * 3.50), 2)
                rr_ratio = round(abs(entry_p - tp1_p) / risk, 2)

                return {
                    "action": "SELL",
                    "consensus_score": consensus_score,
                    "council_agreement_level": "HUNTING_PREMIUM_PULLBACK",
                    "market_bias": "BEARISH",
                    "trade_health": trade_health,
                    "recommended_management": rec_management,
                    "dynamic_sl_target": dynamic_sl_target,
                    "lead_strategies": ["Institutional Pullback Hunting", f"Regime_{regime_type}", f"Zone_{zone_name}"],
                    "entry_price": entry_p,
                    "stop_loss": sl_p,
                    "take_profit_1": tp1_p,
                    "take_profit_2": tp2_p,
                    "risk_reward_ratio": rr_ratio,
                    "invalidation_condition": f"M15 close above structural resistance at {sl_p:,.2f}",
                    "voting_summary": voting_summary,
                    "council_debate_summary": f"🏛️ Institutional Auction Planning: Council is BEARISH ({sell_votes} Sell votes, {consensus_score}% score). Live price is at {zone_name} ({eq_data.get('zone_pct', 20):.0f}% of range). Direct market sell prohibited (whale accumulation area). Planned Entry anchored to Premium Pullback @ ${entry_p:,.2f} | SL: ${sl_p:,.2f} | TP1: ${tp1_p:,.2f}. 5-Min Sniper Watcher active to confirm pullback entry."
                }
            elif m5_cross == "BULLISH" and ask_pct >= 62.0:
                # Rocket Pump Veto: heavy buyer delta
                return {
                    "action": "HOLD",
                    "consensus_score": 35,
                    "council_agreement_level": "ROCKET_PUMP_VETO",
                    "market_bias": "NEUTRAL",
                    "trade_health": trade_health,
                    "recommended_management": rec_management,
                    "dynamic_sl_target": dynamic_sl_target,
                    "entry_price": live_price,
                    "stop_loss": 0.0,
                    "take_profit_1": 0.0,
                    "take_profit_2": 0.0,
                    "risk_reward_ratio": 0.0,
                    "voting_summary": voting_summary,
                    "council_debate_summary": f"🛡️ Freight Train Veto: {sell_votes} agents voted SELL, but M5 EMA 9 > 21 with heavy buyer delta ({ask_pct:.0f}% Ask Lifters). Entry blocked until buyer exhaustion completes."
                }
            else:
                # Direct Sell Signal (in Premium / Equilibrium)
                entry_p = round(sum(sell_entries) / len(sell_entries), 2) if sell_entries else round(live_price + 0.50, 2)
                raw_sl = max(sell_sls) if sell_sls else (entry_p + default_sl_dist)
                risk = max(min_sl_dist, min(max_sl_dist, abs(raw_sl - entry_p)))
                sl_p = round(entry_p + risk, 2)
                tp1_p = round(entry_p - (risk * 2.00), 2)
                tp2_p = round(entry_p - (risk * 3.50), 2)
                rr_ratio = round(abs(entry_p - tp1_p) / risk, 2)

                return {
                    "action": "SELL",
                    "consensus_score": consensus_score,
                    "council_agreement_level": "UNANIMOUS_SUPERMAJORITY" if sell_votes >= 8 else "STRONG_CONSENSUS",
                    "market_bias": "BEARISH",
                    "trade_health": trade_health,
                    "recommended_management": rec_management,
                    "dynamic_sl_target": dynamic_sl_target,
                    "lead_strategies": ["Multi-Agent Institutional Confluence", f"Regime_{regime_type}", f"Zone_{zone_name}"],
                    "entry_price": entry_p,
                    "stop_loss": sl_p,
                    "take_profit_1": tp1_p,
                    "take_profit_2": tp2_p,
                    "risk_reward_ratio": rr_ratio,
                    "invalidation_condition": f"M15 close above structural resistance at {sl_p:,.2f}",
                    "voting_summary": voting_summary,
                    "council_debate_summary": f"14-Agent Consensus: {sell_votes}/14 agents voted SELL ({consensus_score}% score). Zone: {zone_name}, Regime: {regime_type}. Target TP1 @ {tp1_p:,.2f} (1.75R) & TP2 @ {tp2_p:,.2f} (3.0R)."
                }

        # C. Sidelines / Conflicted
        else:
            return {
                "action": "HOLD",
                "consensus_score": 0,
                "council_agreement_level": "SPLIT_CONFLICTED",
                "market_bias": "NEUTRAL",
                "trade_health": trade_health,
                "recommended_management": rec_management,
                "dynamic_sl_target": dynamic_sl_target,
                "entry_price": live_price,
                "stop_loss": 0.0,
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "risk_reward_ratio": 0.0,
                "voting_summary": voting_summary,
                "council_debate_summary": f"Sidelines: 14 Agents split ({buy_votes} Buy, {sell_votes} Sell, {hold_votes} Hold). Regime: {regime_type}. Standing by for clean directional confluence."
            }
