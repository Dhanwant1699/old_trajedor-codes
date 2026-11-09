import os
import py_compile
import json

friday_dir = r"D:\Ai Trading ALGO\scratch\friday_restore"

clean_files = [
    ".env",
    ".env.example",
    "config.py",
    "main.py",
    "requirements.txt",
    "README.md",
    "MULTI_ACCOUNT_ARCHITECTURE.md",
    "agents/__init__.py",
    "agents/breakout_agent.py",
    "agents/fibonacci_agent.py",
    "agents/liquidity_agent.py",
    "agents/llm_client.py",
    "agents/macro_agent.py",
    "agents/master_coordinator.py",
    "agents/mean_reversion_agent.py",
    "agents/orderflow_agent.py",
    "agents/pattern_agent.py",
    "agents/regime_agent.py",
    "agents/risk_agent.py",
    "agents/scalping_agent.py",
    "agents/smc_agent.py",
    "agents/supply_demand_agent.py",
    "agents/tick_flow_agent.py",
    "agents/trend_agent.py",
    "agents/voice_companion_agent.py",
    "agents/volume_delta_agent.py",
    "core/__init__.py",
    "core/ai_ledger.py",
    "core/council_state.py",
    "core/dashboard_server.py",
    "core/data_engine.py",
    "core/dual_account_manager.py",
    "core/execution_engine.py",
    "core/news_engine.py",
    "core/pattern_detector.py",
    "core/pro_trade_manager.py",
    "core/risk_manager.py",
    "data/admin_config.json",
    "data/council_state.json",
    "docs/dashboard.html",
    "docs/ARCHITECTURE_FLOW_DIAGRAM.md",
    "docs/HOW_AGENTS_WORK_AND_COST.md",
    "docs/flow_diagram.html",
    "tests/__init__.py",
    "tests/benchmark_models.py",
    "tests/check_btc_spec.py",
    "tests/check_live_gold_price.py",
    "tests/check_symbols.py",
    "tests/get_mt5_account_info.py",
    "tests/test_14_agents_council.py",
    "tests/test_account_disconnect_reconnect.py",
    "tests/test_engines.py",
    "tests/test_multi_agent.py",
    "tests/test_multi_symbol.py",
    "tests/test_nvidia_live.py",
    "tests/test_trade_lifecycle_sentries.py",
    "tests/test_voice_companion.py"
]

print(f"Checking {len(clean_files)} Friday target files...")

errors = 0
for f in clean_files:
    full_path = os.path.join(friday_dir, f.replace("/", os.sep))
    if not os.path.exists(full_path):
        print(f"[MISSING] {f}")
        errors += 1
        continue
    
    if f.endswith(".py"):
        try:
            py_compile.compile(full_path, doraise=True)
            print(f"[OK PY] {f}")
        except Exception as e:
            print(f"[FAIL PY] {f}: {e}")
            errors += 1
    elif f.endswith(".json"):
        try:
            with open(full_path, "r", encoding="utf-8") as jf:
                json.load(jf)
            print(f"[OK JSON] {f}")
        except Exception as e:
            print(f"[FAIL JSON] {f}: {e}")
            errors += 1
    else:
        print(f"[OK OTHER] {f} ({os.path.getsize(full_path)} bytes)")

print(f"\nVerification finished with {errors} errors.")
