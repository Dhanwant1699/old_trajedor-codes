import sys
import MetaTrader5 as mt5

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if not mt5.initialize():
    print("MT5_ERROR: Failed to initialize MT5. Error:", mt5.last_error())
    sys.exit(1)

acc = mt5.account_info()
if acc is None:
    print("MT5_ERROR: Could not retrieve account info. Error:", mt5.last_error())
    mt5.shutdown()
    sys.exit(1)

trade_mode_map = {
    mt5.ACCOUNT_TRADE_MODE_DEMO: "DEMO",
    mt5.ACCOUNT_TRADE_MODE_CONTEST: "CONTEST",
    mt5.ACCOUNT_TRADE_MODE_REAL: "REAL / LIVE"
}

trade_mode = trade_mode_map.get(acc.trade_mode, f"UNKNOWN ({acc.trade_mode})")

print("=" * 60)
print("             METATRADER 5 LIVE ACCOUNT DETAILS             ")
print("=" * 60)
print(f"  Account Login / ID : {acc.login}")
print(f"  Account Name       : {acc.name}")
print(f"  Broker Server      : {acc.server}")
print(f"  Company / Broker   : {acc.company}")
print(f"  Account Type       : {trade_mode}")
print(f"  Account Currency   : {acc.currency}")
print(f"  Leverage           : 1:{acc.leverage}")
print("-" * 60)
print(f"  Balance            : ${acc.balance:,.2f} {acc.currency}")
print(f"  Equity             : ${acc.equity:,.2f} {acc.currency}")
print(f"  Floating Profit/Loss: ${acc.profit:,.2f} {acc.currency}")
print(f"  Margin Used        : ${acc.margin:,.2f} {acc.currency}")
print(f"  Free Margin        : ${acc.margin_free:,.2f} {acc.currency}")
print(f"  Margin Level       : {acc.margin_level:.2f}%" if acc.margin > 0 else "  Margin Level       : N/A (No open positions)")
print(f"  Algo Trading Allowed: {'YES ✅' if acc.trade_expert else 'NO ❌ (Enable in MT5 Options)'}")
print("=" * 60)

# Check Open Positions
positions = mt5.positions_get()
if positions:
    print(f"\n  Currently Open Positions: {len(positions)}")
    for p in positions:
        p_type = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
        print(f"    - Ticket #{p.ticket}: {p_type} {p.volume} lots {p.symbol} @ {p.price_open:.2f} | P/L: ${p.profit:,.2f}")
else:
    print("\n  Currently Open Positions: 0 (No active trades)")

mt5.shutdown()
