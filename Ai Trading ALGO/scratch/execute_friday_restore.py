import os
import shutil
import glob

workspace = r"D:\Ai Trading ALGO"
friday_src = r"D:\Ai Trading ALGO\scratch\friday_restore"
backup_dst = r"D:\Ai Trading ALGO\scratch\backup_saturday_monday"

print("Step 1: Creating backup of current repository...")
os.makedirs(backup_dst, exist_ok=True)
for item in ["agents", "core", "data", "docs", "tests", "main.py", "config.py", "launch_dashboard.py"]:
    src_path = os.path.join(workspace, item)
    dst_path = os.path.join(backup_dst, item)
    if os.path.isdir(src_path):
        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)
        shutil.copytree(src_path, dst_path)
    elif os.path.isfile(src_path):
        shutil.copy2(src_path, dst_path)
print("Backup created successfully.")

print("Step 2: Cleaning up Saturday/Sunday/Monday files...")
# Remove subdirectories that were introduced
items_to_remove = [
    r"agents\btcusd",
    r"agents\xauusd",
    r"core\compliance_monitor.py",
    r"core\multi_account_risk_planner.py",
    r"data\council_state_btcusd.json",
    r"data\council_state_xauusd.json",
    r"docs\dashboard.html.bak",
    r"docs\three.r128.min.js",
    r"launch_dashboard.py",
    r"AUTONOMOUS_TRADING_FIXES_COMPLETE.md",
    r"REQUIREMENTS_AND_TECH_STACK.md",
    r"TRADING_SYSTEM_FIXES_SUMMARY.md",
    r"tests\test_multi_asset_account_mgmt.py"
]

for rel in items_to_remove:
    p = os.path.join(workspace, rel)
    if os.path.isdir(p):
        shutil.rmtree(p)
        print(f"Removed dir: {rel}")
    elif os.path.isfile(p):
        os.remove(p)
        print(f"Removed file: {rel}")

print("Step 3: Restoring Friday files into workspace...")
clean_files = [
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

for rel in clean_files:
    src_file = os.path.join(friday_src, rel.replace("/", os.sep))
    dst_file = os.path.join(workspace, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
    shutil.copy2(src_file, dst_file)
    print(f"Restored: {rel}")

print("\nRestoration of Friday codebase complete!")
