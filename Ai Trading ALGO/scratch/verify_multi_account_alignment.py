import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.multi_account_risk_planner import MultiAccountRiskPlanner

print("=== 1. TEST XAUUSD (GOLD) MULTI-ACCOUNT ALIGNMENT ===")
plan_gold = MultiAccountRiskPlanner.plan_lot_sizes_for_all_accounts(
    symbol="XAUUSD",
    entry_price=4350.0,
    stop_loss=4340.0,
    consensus_score=85.0
)
for acc_id, alloc in plan_gold["account_allocations"].items():
    name = alloc["account_name"]
    curr = alloc["currency"]
    lots = alloc.get("planned_lots")
    max_cap = alloc.get("max_lot_cap")
    status = alloc.get("status")
    reason = alloc.get("reason", "Cleared for execution")
    print(f"• {name} [{curr}]: Planned={lots} Lots (Cap={max_cap}) | Status={status} | Note={reason}")

print("\n=== 2. TEST BTCUSD (BITCOIN) MULTI-ACCOUNT ALIGNMENT ===")
plan_btc = MultiAccountRiskPlanner.plan_lot_sizes_for_all_accounts(
    symbol="BTCUSD",
    entry_price=84000.0,
    stop_loss=83150.0,
    consensus_score=85.0
)
for acc_id, alloc in plan_btc["account_allocations"].items():
    name = alloc["account_name"]
    curr = alloc["currency"]
    lots = alloc.get("planned_lots")
    max_cap = alloc.get("max_lot_cap")
    status = alloc.get("status")
    reason = alloc.get("reason", "Cleared for execution")
    print(f"• {name} [{curr}]: Planned={lots} Lots (Cap={max_cap}) | Status={status} | Note={reason}")
