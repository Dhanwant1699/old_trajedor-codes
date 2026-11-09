import sys

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from news_engine import ForexNewsEngine
from risk_manager import RiskManager
from data_engine import MT5DataEngine
from claude_trader import ClaudeTraderAgent
from config import CONFIG

def test_submodules():
    print("--- 1. Testing ForexFactory.com & Investing.com News Engine ---")
    news_engine = ForexNewsEngine()
    calendar = news_engine.fetch_forexfactory_calendar()
    print(f"Total ForexFactory Events Loaded: {len(calendar)}")
    
    investing_news = news_engine.fetch_investing_headlines()
    print(f"Total Investing.com Headlines Loaded: {len(investing_news)}")

    news_payload = news_engine.get_news_payload()
    print(f"Sources Configured: {news_payload['sources']}")
    print(f"News Blackout Active: {news_payload['news_blackout_active']}")
    print(f"Upcoming ForexFactory Events: {len(news_payload['forexfactory_upcoming_events'])}")
    print(f"Investing.com Headlines: {len(news_payload['investing_com_realtime_news'])}")
    for h in news_payload['investing_com_realtime_news'][:3]:
        print(f"  * {h}")

    print("\n--- 2. Testing Risk Manager ---")
    rm = RiskManager(symbol="XAUUSD")
    
    # Scenario: $10,000 account, 1% risk ($100 risk), Gold entry at 2720.00, SL at 2715.00 ($5 distance = 500 points)
    # 1.0 standard lot of Gold = 100 oz. $5 distance on 1 lot = $500 loss.
    # $100 risk / $500 = 0.20 lots.
    lot = rm.calculate_lot_size(account_equity=10000.0, entry_price=2720.0, stop_loss=2715.0, risk_pct=1.0)
    print(f"Calculated Lot Size ($10,000 equity, 1% risk, $5 SL distance): {lot} lots")
    assert lot == 0.20, f"Expected 0.20 lots, got {lot}"

    # Scenario: Trade Validation check
    decision_buy = {
        "action": "BUY",
        "confidence_score": 85,
        "entry_price": 2720.0,
        "stop_loss": 2715.0,
        "take_profit_1": 2730.0,
        "take_profit_2": 2740.0,
        "risk_percent": 1.0,
        "setup_name": "Asian_Low_Sweep_FVG"
    }
    is_valid, msg, params = rm.validate_trade_decision(
        decision=decision_buy,
        account_info={"equity": 10000.0, "balance": 10000.0},
        current_spread_points=15.0,
        open_positions_count=0,
        day_of_month=16
    )
    print(f"Trade Validation Result: Valid={is_valid} | Msg='{msg}' | Calculated Lots={params.get('calculated_lots')}")
    assert is_valid is True

    print("\n--- 3. Testing Claude Trader Module Schema ---")
    trader = ClaudeTraderAgent()
    print(f"Claude Trader initialized. Model: {CONFIG.CLAUDE_MODEL}")

    print("\n[SUCCESS] ALL SUBMODULE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_submodules()

