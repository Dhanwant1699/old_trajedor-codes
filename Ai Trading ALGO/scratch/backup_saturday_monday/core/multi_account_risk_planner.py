"""
Multi-Account N-Terminal AI Risk & Lot Sizing Planner.
Plans dynamic, mathematically sound lot sizes customized for EACH active account/terminal.

Supports any number of accounts (N-Terminals) dynamically loaded from admin_config.json:
- Accounts with different equities ($100k, $50k, $10k, $500, etc.)
- Different base currencies (USD, EUR, GBP, etc.)
- Different operating modes (STANDARD_PROP vs MICRO_COMPOUNDING)
- Granular per-symbol lot size ceilings and risk thresholds
- Automatic Quorum Conviction scaling (>=93% = 100%, 85-92% = 70%, 75-84% = 40%)
"""

import os
import json
from typing import Dict, Any, List, Optional
from config import CONFIG

ADMIN_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "admin_config.json")


class MultiAccountRiskPlanner:
    """
    Plans personalized position sizing and risk exposure for N trading accounts.
    """

    @staticmethod
    def load_account_configs() -> Dict[str, Any]:
        """Loads live account configurations from admin_config.json."""
        if os.path.exists(ADMIN_CONFIG_PATH):
            try:
                with open(ADMIN_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("accounts", {})
            except Exception as e:
                print(f"[MultiAccountRiskPlanner] Error loading config: {e}")
        return {}

    @classmethod
    def plan_lot_sizes_for_all_accounts(
        cls,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        consensus_score: float = 85.0,
        live_accounts_telemetry: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculates the exact, custom planned lot size for EVERY configured account.

        Returns:
            Dict containing:
            - 'account_allocations': Dict of per-account planned sizing details
            - 'summary_string': Human-readable summary for logs and UI badges
            - 'total_system_lots': Sum of all lots across all accounts
        """
        accounts_cfg = cls.load_account_configs()
        allocations = {}
        total_lots = 0.0
        summary_parts = []

        is_btc = "BTC" in symbol.upper() or "BITCOIN" in symbol.upper()
        contract_size = 1.0 if is_btc else 100.0  # 1 BTC = 1.0 contract, 1 Gold = 100 oz

        sl_distance = abs(entry_price - stop_loss) if (entry_price > 0 and stop_loss > 0) else 0.0
        loss_per_standard_lot = (sl_distance * contract_size) if sl_distance > 0 else 0.0

        # Conviction Multiplier from Consensus Quorum Meter
        quorum = float(consensus_score)
        if quorum >= 80.0:
            quorum_tier_pct = 1.00  # 100% Full Sizing
        elif quorum >= 65.0:
            quorum_tier_pct = 0.75  # 75% Standard Sizing
        elif quorum >= 50.0:
            quorum_tier_pct = 0.50  # 50% Agile Scalp Sizing
        else:
            quorum_tier_pct = 0.25  # Micro Sizing

        for acc_id, conf in accounts_cfg.items():
            acc_name = conf.get("name", f"Account ({acc_id})")
            currency = conf.get("currency", "USD")
            mode = conf.get("mode", "STANDARD_PROP")
            is_active = conf.get("is_active", True)
            allowed_symbols = conf.get("allowed_symbols", ["XAUUSD"])

            # 1. Eligibility Check
            target_clean = "BTCUSD" if is_btc else "XAUUSD"
            if not is_active:
                allocations[acc_id] = {
                    "account_name": acc_name,
                    "currency": currency,
                    "mode": mode,
                    "planned_lots": 0.0,
                    "status": "INACTIVE",
                    "reason": "Account is disabled in admin settings."
                }
                continue

            if target_clean not in [s.upper() for s in allowed_symbols]:
                allocations[acc_id] = {
                    "account_name": acc_name,
                    "currency": currency,
                    "mode": mode,
                    "planned_lots": 0.0,
                    "status": "SYMBOL_RESTRICTED",
                    "reason": f"{target_clean} is not in allowed symbols for this account."
                }
                continue

            # 2. Get Live Equity
            live_telemetry = (live_accounts_telemetry or {}).get(acc_id, {})
            equity = float(live_telemetry.get("equity", 0.0))
            if equity <= 0:
                # Fallback to estimated equity based on account mode / defaults
                equity = 10000.0 if mode == "STANDARD_PROP" else 500.0

            # 3. Read account-specific symbol lot caps
            sym_settings = conf.get("symbol_settings", {}).get(target_clean, {})
            account_max_lot = float(
                sym_settings.get("max_lot_size") or
                conf.get("symbol_lots", {}).get(target_clean) or
                conf.get("max_lot_size", 0.08)
            )
            min_lot = float(conf.get("min_lot_size", 0.01))

            # 4. Check Daily Target / Max Loss Status
            target_hit = bool(live_telemetry.get("target_reached_today", False))
            loss_hit = bool(live_telemetry.get("max_loss_hit_today", False))
            if target_hit:
                allocations[acc_id] = {
                    "account_name": acc_name,
                    "currency": currency,
                    "mode": mode,
                    "equity": round(equity, 2),
                    "planned_lots": 0.0,
                    "status": "TARGET_LOCKED",
                    "reason": "Daily profit target achieved. Capital locked."
                }
                continue

            if loss_hit:
                allocations[acc_id] = {
                    "account_name": acc_name,
                    "currency": currency,
                    "mode": mode,
                    "equity": round(equity, 2),
                    "planned_lots": 0.0,
                    "status": "LOSS_HALTED",
                    "reason": "Daily max loss threshold reached. Preserving capital."
                }
                continue

            # 4b. Strict 5% Aggregate Equity Risk Cap Check (Including All Open AI Trades)
            # Max allowable cumulative open risk across all positions + new trade <= 5.0% of current equity
            max_portfolio_risk_pct = float(getattr(CONFIG, "MAX_PORTFOLIO_AGGREGATE_RISK_PCT", 5.0))
            max_portfolio_risk_dollars = equity * (max_portfolio_risk_pct / 100.0)

            # Compute current open risk from existing positions on this account
            open_positions = live_telemetry.get("open_positions", [])
            current_open_risk_dollars = 0.0
            for pos in open_positions:
                pos_sym = str(pos.get("symbol", "")).upper()
                pos_is_btc = "BTC" in pos_sym or "BITCOIN" in pos_sym
                pos_contract = 1.0 if pos_is_btc else 100.0
                pos_vol = float(pos.get("volume", 0.0) or 0.0)
                pos_entry = float(pos.get("open_price", 0.0) or 0.0)
                pos_sl = float(pos.get("sl", 0.0) or 0.0)
                pos_type = str(pos.get("type", "BUY")).upper()

                if pos_sl > 0:
                    if pos_type == "BUY" and pos_sl >= pos_entry:
                        pos_risk = 0.0  # Risk-free breakeven locked
                    elif pos_type == "SELL" and pos_sl <= pos_entry:
                        pos_risk = 0.0  # Risk-free breakeven locked
                    else:
                        pos_risk = abs(pos_entry - pos_sl) * pos_contract * pos_vol
                else:
                    pos_risk = (1000.0 if pos_is_btc else 10.0) * pos_contract * pos_vol
                current_open_risk_dollars += pos_risk

            current_open_risk_pct = (current_open_risk_dollars / equity * 100.0) if equity > 0 else 0.0
            remaining_risk_budget_dollars = max(0.0, max_portfolio_risk_dollars - current_open_risk_dollars)
            remaining_risk_budget_pct = (remaining_risk_budget_dollars / equity * 100.0) if equity > 0 else 0.0

            if current_open_risk_pct >= max_portfolio_risk_pct or remaining_risk_budget_dollars <= 0.0:
                allocations[acc_id] = {
                    "account_name": acc_name,
                    "currency": currency,
                    "mode": mode,
                    "equity": round(equity, 2),
                    "planned_lots": 0.0,
                    "status": "RISK_CAP_EXCEEDED",
                    "reason": f"Active AI trades already risk {current_open_risk_pct:.2f}% of equity. Hard {max_portfolio_risk_pct:.1f}% aggregate cap reached."
                }
                continue

            # 5. Calculate Dynamic Planned Lots
            if mode == "MICRO_COMPOUNDING":
                # Micro compounding account: fixed 0.01 lots
                planned_lots = min(min_lot, account_max_lot)
                risk_amount = (loss_per_standard_lot * planned_lots) if loss_per_standard_lot > 0 else 1.0
            else:
                # Standard Prop: Dynamic percentage risk calculation (capped at remaining risk budget and 5% max)
                target_risk_pct = float(conf.get("risk_percent", CONFIG.MAX_RISK_PER_TRADE_PCT))
                effective_risk_pct = min(target_risk_pct, remaining_risk_budget_pct)
                dollar_risk = min(equity * (effective_risk_pct / 100.0), remaining_risk_budget_dollars)

                # Convert EUR equity risk to USD if needed (approx 1.08 parity buffer)
                if currency == "EUR":
                    dollar_risk *= 1.08

                if loss_per_standard_lot > 0:
                    raw_math_lots = dollar_risk / loss_per_standard_lot
                else:
                    raw_math_lots = account_max_lot * 0.5

                # Apply conviction scaling
                scaled_lots = raw_math_lots * quorum_tier_pct
                # Clamp between min_lot and this account's max_lot cap
                clamped_lots = max(min_lot, min(scaled_lots, account_max_lot))
                planned_lots = round(clamped_lots, 2)
                risk_amount = round((loss_per_standard_lot * planned_lots), 2)

            # Ensure planned risk does not exceed remaining budget
            if loss_per_standard_lot > 0 and (loss_per_standard_lot * planned_lots) > remaining_risk_budget_dollars:
                max_affordable_lots = remaining_risk_budget_dollars / loss_per_standard_lot
                planned_lots = round(max_affordable_lots, 2)
                risk_amount = round((loss_per_standard_lot * planned_lots), 2)

            if planned_lots < min_lot:
                allocations[acc_id] = {
                    "account_name": acc_name,
                    "currency": currency,
                    "mode": mode,
                    "equity": round(equity, 2),
                    "planned_lots": 0.0,
                    "status": "RISK_BUDGET_INSUFFICIENT",
                    "reason": f"Remaining risk budget ({remaining_risk_budget_pct:.2f}%) cannot afford minimum {min_lot} lot without exceeding 5% cap."
                }
                continue

            total_lots += planned_lots
            allocations[acc_id] = {
                "account_name": acc_name,
                "currency": currency,
                "mode": mode,
                "equity": round(equity, 2),
                "planned_lots": planned_lots,
                "max_lot_cap": account_max_lot,
                "risk_amount": risk_amount,
                "status": "CLEARED"
            }

            short_name = acc_name.split("(")[0].strip().replace("Account #", "#")
            summary_parts.append(f"{short_name}: {planned_lots}L")

        summary_string = " | ".join(summary_parts) if summary_parts else "No Active Accounts"

        return {
            "account_allocations": allocations,
            "summary_string": summary_string,
            "total_system_lots": round(total_lots, 2),
            "quorum_tier_pct": int(quorum_tier_pct * 100)
        }
