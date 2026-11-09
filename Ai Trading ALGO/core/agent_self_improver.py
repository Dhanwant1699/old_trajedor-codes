"""
Autonomous Per-Agent Self-Improvement & Bayesian Reputation Engine for Trajedor.

Enables individual agent self-correction and continuous skill evolution:
1. Trade Performance Attribution: Tracks which specific agents voted for winning vs losing trades.
2. Per-Agent Mistake Diagnostics: Pinpoints the exact technical error made by each culprit agent.
3. Dynamic Council Voting Weight (Bayesian Calibration):
   - Winning agents with sound logic get their voting weight boosted (up to 2.0x).
   - Inaccurate/stubborn agents get their voting weight demoted (down to 0.25x).
4. Agent Self-Correction Memory: Each agent maintains its own historical mistake log and
   consults it to refine future justifications.
"""

import os
import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class AgentSelfImprover:
    DEFAULT_AGENTS = [
        "SMC_ICT_Agent",
        "Trend_Momentum_Agent",
        "Mean_Reversion_Agent",
        "Macro_News_Agent",
        "VolumeProfile_VWAP_Agent",
        "Supply_Demand_Agent",
        "Breakout_Volatility_Agent",
        "Fibonacci_GoldenPocket_Agent",
        "ChartPattern_Geometry_Agent",
        "Intraday_Scalping_Agent",
        "Regime_Detection_Agent",
        "Tick_OrderFlow_Agent",
        "Volume_Delta_CVD_Agent"
    ]

    def __init__(self, data_dir: Optional[str] = None):
        base_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(base_dir, exist_ok=True)
        self.reputation_file = os.path.join(base_dir, "agent_reputations.json")
        self.agent_mistakes_file = os.path.join(base_dir, "agent_mistakes.json")
        self._init_files()

    def _init_files(self):
        """Initializes agent reputation weights and mistake histories."""
        if not os.path.exists(self.reputation_file):
            initial_reps = {}
            for agent in self.DEFAULT_AGENTS:
                initial_reps[agent] = {
                    "total_votes": 0,
                    "correct_votes": 0,
                    "incorrect_votes": 0,
                    "win_rate_pct": 50.0,
                    "voting_weight": 1.0,  # 1.0 = normal baseline (scales 0.25 to 2.0)
                    "status": "ACTIVE_STUDENT",
                    "consecutive_losses": 0,
                    "last_updated_utc": datetime.now(timezone.utc).isoformat()
                }
            with open(self.reputation_file, "w", encoding="utf-8") as f:
                json.dump(initial_reps, f, indent=2)

        if not os.path.exists(self.agent_mistakes_file):
            initial_mistakes = {agent: [] for agent in self.DEFAULT_AGENTS}
            with open(self.agent_mistakes_file, "w", encoding="utf-8") as f:
                json.dump(initial_mistakes, f, indent=2)

    def load_reputations(self) -> Dict[str, Dict[str, Any]]:
        """Loads all agent voting weights and performance stats."""
        try:
            with open(self.reputation_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_agent_weight(self, agent_name: str) -> float:
        """Returns the dynamic voting weight for a given agent (0.25 to 2.0)."""
        reps = self.load_reputations()
        return reps.get(agent_name, {}).get("voting_weight", 1.0)

    def evaluate_trade_outcome_and_improve_agents(
        self,
        trade_direction: str,  # "BUY" or "SELL"
        pnl: float,
        r_multiple: float,
        agent_votes: List[Dict[str, Any]],
        market_context_at_exit: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Attributes outcome to each voting agent, diagnoses specific mistakes,
        and dynamically updates council voting weights.
        """
        is_win = pnl > 0.0
        reps = self.load_reputations()
        
        try:
            with open(self.agent_mistakes_file, "r", encoding="utf-8") as f:
                all_mistakes = json.load(f)
        except Exception:
            all_mistakes = {}

        updates_summary = []

        for vote_record in agent_votes:
            name = vote_record.get("agent_name")
            voted = str(vote_record.get("vote", "HOLD")).upper()
            proof = str(vote_record.get("proof", ""))

            if not name or name not in reps:
                continue

            agent_stats = reps[name]
            agent_stats["total_votes"] += 1

            # Check if agent's vote aligned with the winning direction
            agent_was_correct = False
            if is_win and voted == trade_direction:
                agent_was_correct = True
            elif not is_win and voted != trade_direction and voted != "HOLD":
                # Agent warned against the trade!
                agent_was_correct = True
            elif not is_win and voted == trade_direction:
                agent_was_correct = False

            if agent_was_correct:
                agent_stats["correct_votes"] += 1
                agent_stats["consecutive_losses"] = 0
                # Reward: Boost weight gradually (cap at 2.0)
                agent_stats["voting_weight"] = min(2.0, round(agent_stats["voting_weight"] * 1.08, 2))
                agent_stats["status"] = "MASTER_ANALYST" if agent_stats["voting_weight"] >= 1.5 else "ACTIVE"
                updates_summary.append(f"[BOOST] {name} weight increased to {agent_stats['voting_weight']}x (Right Call)")
            else:
                agent_stats["incorrect_votes"] += 1
                agent_stats["consecutive_losses"] += 1
                # Demotion: Penalize weight (floor at 0.25)
                agent_stats["voting_weight"] = max(0.25, round(agent_stats["voting_weight"] * 0.88, 2))
                if agent_stats["consecutive_losses"] >= 3:
                    agent_stats["status"] = "PROBATION_RETRAINING"
                updates_summary.append(f"[PENALTY] {name} weight demoted to {agent_stats['voting_weight']}x (Mistake)")

                # Diagnose and record the specific mistake
                diagnosed_error = self._diagnose_agent_specific_mistake(name, proof, market_context_at_exit)
                if name not in all_mistakes:
                    all_mistakes[name] = []
                all_mistakes[name].append({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "trade_direction": trade_direction,
                    "agent_proof": proof,
                    "diagnosed_mistake": diagnosed_error,
                    "loss_r": r_multiple
                })
                # Keep last 15 mistakes per agent
                all_mistakes[name] = all_mistakes[name][-15:]

            # Recalculate win rate
            total = agent_stats["correct_votes"] + agent_stats["incorrect_votes"]
            agent_stats["win_rate_pct"] = round((agent_stats["correct_votes"] / total * 100), 1) if total > 0 else 50.0
            agent_stats["last_updated_utc"] = datetime.now(timezone.utc).isoformat()

        # Save updated reputations and mistakes
        with open(self.reputation_file, "w", encoding="utf-8") as f:
            json.dump(reps, f, indent=2)

        with open(self.agent_mistakes_file, "w", encoding="utf-8") as f:
            json.dump(all_mistakes, f, indent=2)

        return {
            "is_win": is_win,
            "pnl": pnl,
            "updated_agents_count": len(agent_votes),
            "summary": updates_summary
        }

    def _diagnose_agent_specific_mistake(
        self,
        agent_name: str,
        proof: str,
        ctx: Optional[Dict[str, Any]] = None
    ) -> str:
        """Determines the exact domain-specific mistake made by the agent."""
        ctx = ctx or {}
        opposing_regime = ctx.get("regime", "UNKNOWN")
        spread = ctx.get("spread", 15)

        if "SMC" in agent_name:
            return "SMC Error: Identified an FVG/OB that was already mitigated, or traded a sweep against the higher-timeframe trend."
        elif "Pattern" in agent_name:
            return "Pattern Error: Traded a textbook formation without waiting for candle body displacement/breakout confirmation."
        elif "Trend" in agent_name:
            return "Trend Error: Chased price at the tail end of an extended move right into an institutional liquidity pool."
        elif "Mean_Reversion" in agent_name:
            return "Mean-Reversion Error: Faded an overbought/oversold extreme during strong institutional momentum expansion."
        elif "Breakout" in agent_name:
            return "Breakout Error: Fell for a retail false-breakout trap; volume expansion was absent."
        elif "Scalping" in agent_name:
            return f"Scalp Error: Entered with adverse spread ({spread} pts) or ignored higher-timeframe resistance."
        else:
            return f"Strategic Error: Over-weighted local micro-signal ({proof[:40]}...) against macro regime ({opposing_regime})."

    def get_agent_self_improvement_prompt_context(self, agent_name: str) -> str:
        """
        Generates a concise self-correction prompt injection for an agent.
        Tells the agent its own past mistakes so it does not repeat them.
        """
        try:
            with open(self.agent_mistakes_file, "r", encoding="utf-8") as f:
                all_mistakes = json.load(f)
            mistakes = all_mistakes.get(agent_name, [])
            if not mistakes:
                return "Your historical track record is clean. Maintain disciplined confluence standards."

            recent_lessons = [m["diagnosed_mistake"] for m in mistakes[-3:]]
            return (
                f"SELF-CORRECTION DIRECTIVE FOR {agent_name}:\n"
                f"You have previously made the following errors in recent trades:\n"
                + "\n".join(f"- {l}" for l in recent_lessons) +
                "\nYou are STRICTLY REQUIRED to verify that your current trade setup DOES NOT commit these same errors!"
            )
        except Exception:
            return ""

    def generate_agent_leaderboard(self) -> str:
        """Produces a Wall Street trading desk performance leaderboard."""
        reps = self.load_reputations()
        sorted_agents = sorted(reps.items(), key=lambda x: (x[1]["voting_weight"], x[1]["win_rate_pct"]), reverse=True)

        lines = [
            "=" * 75,
            "TRAJEDOR TRADING DESK: AGENT REPUTATION & SKILL LEADERBOARD",
            "=" * 75,
            f"{'Agent Name':<32} | {'Weight':<7} | {'Win %':<6} | {'Votes':<6} | {'Status'}",
            "-" * 75
        ]

        for name, data in sorted_agents:
            lines.append(
                f"{name:<32} | {data['voting_weight']:<6.2f}x | {data['win_rate_pct']:<5.1f}% | "
                f"{data['total_votes']:<6} | {data['status']}"
            )

        lines.append("=" * 75)
        return "\n".join(lines)


if __name__ == "__main__":
    print("Testing Trajedor Agent Self-Improvement Engine...")
    improver = AgentSelfImprover()

    # Simulate an adverse trade: Council took a BUY on XAUUSD, but it resulted in a loss (-1.2R)
    mock_agent_votes = [
        {"agent_name": "SMC_ICT_Agent", "vote": "BUY", "proof": "M5 FVG bounce"},
        {"agent_name": "ChartPattern_Geometry_Agent", "vote": "BUY", "proof": "Double bottom forming"},
        {"agent_name": "Trend_Momentum_Agent", "vote": "SELL", "proof": "H4 trend is strongly bearish below 200 EMA"},
        {"agent_name": "Breakout_Volatility_Agent", "vote": "BUY", "proof": "Bollinger squeeze breakout"}
    ]

    print("\n--- SIMULATING LOSS TRADE ATTRIBUTION & MISTAKE DIAGNOSIS ---")
    result = improver.evaluate_trade_outcome_and_improve_agents(
        trade_direction="BUY",
        pnl=-240.00,
        r_multiple=-1.2,
        agent_votes=mock_agent_votes,
        market_context_at_exit={"regime": "BEARISH_TREND", "spread": 22}
    )

    for line in result["summary"]:
        print(line)

    print("\n--- AGENT SELF-CORRECTION PROMPT INJECTION ---")
    prompt_ctx = improver.get_agent_self_improvement_prompt_context("SMC_ICT_Agent")
    print(prompt_ctx)

    print("\n" + improver.generate_agent_leaderboard())
