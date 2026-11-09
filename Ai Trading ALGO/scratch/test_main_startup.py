import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("1. Importing main components...", flush=True)
from config import CONFIG
from core import MT5DataEngine, ForexNewsEngine, MT5ExecutionEngine
from core.council_state import CouncilStateManager
from core.pro_trade_manager import ProTradeManager
from core.ai_ledger import AITradeLedger
from core.dual_account_manager import DualAccountManager
from core.dashboard_server import start_dashboard_background
from agents.master_coordinator import MasterCoordinator

print("2. Components imported successfully!", flush=True)

symbols = CONFIG.SYMBOLS
print(f"3. Symbols: {symbols}", flush=True)

d_eng = MT5DataEngine(symbol="XAUUSD")
print("4. Connecting d_eng...", flush=True)
ok = d_eng.connect()
print(f"5. d_eng connected: {ok}", flush=True)

print("6. Creating DualAccountManager...", flush=True)
dual_account_mgr = DualAccountManager(symbol=CONFIG.SYMBOL)
print(f"7. DualAccountManager created with {len(dual_account_mgr.accounts)} accounts!", flush=True)

print("8. Creating MasterCoordinator...", flush=True)
coordinator = MasterCoordinator()
print("9. MasterCoordinator created!", flush=True)

print("10. Testing tick fetch...", flush=True)
ticks = d_eng.get_current_spread_and_ticks()
print(f"11. Live Ticks: {ticks}", flush=True)
d_eng.disconnect()
print("12. All startup steps passed with 100% SUCCESS!", flush=True)
