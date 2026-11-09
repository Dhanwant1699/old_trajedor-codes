"""
Master Coordinator and Asset Dispatcher Router.
Routes deliberations cleanly to dedicated independent AI Traders:
- XAUUSD AI Trader (agents.xauusd.xauusd_ai_trader): Dedicated 16-agent Gold council.
- BTCUSD AI Trader (agents.btcusd.btcusd_ai_trader): Dedicated 16-agent Bitcoin council.
"""
from typing import Dict, Any, Optional
from config import CONFIG
from agents.xauusd.xauusd_ai_trader import GoldMasterCoordinator as XAUUSDAITrader
from agents.btcusd.btcusd_ai_trader import CryptoMasterCoordinator as BTCUSDAITrader

GoldMasterCoordinator = XAUUSDAITrader
CryptoMasterCoordinator = BTCUSDAITrader


def get_coordinator_for_symbol(symbol: str, provider: str = None, model: str = None, api_key: str = None):
    sym = str(symbol).upper()
    if "BTC" in sym or "BITCOIN" in sym or "CRYPTO" in sym:
        return BTCUSDAITrader(provider=provider, model=model, api_key=api_key)
    return XAUUSDAITrader(provider=provider, model=model, api_key=api_key)


class MasterCoordinator:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None, symbol: str = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.default_symbol = symbol or CONFIG.SYMBOL

        self.xauusd_ai_trader = XAUUSDAITrader(provider=provider, model=model, api_key=api_key)
        self.btcusd_ai_trader = BTCUSDAITrader(provider=provider, model=model, api_key=api_key)

        self.gold_coordinator = self.xauusd_ai_trader
        self.crypto_coordinator = self.btcusd_ai_trader

    def get_coordinator(self, symbol: str):
        sym = str(symbol).upper()
        if "BTC" in sym or "BITCOIN" in sym or "CRYPTO" in sym:
            return self.btcusd_ai_trader
        return self.xauusd_ai_trader

    def run_council_deliberation(
        self,
        market_data: Dict[str, Any],
        news_data: Dict[str, Any],
        current_spread_points: float,
        open_positions_count: int,
        day_of_month: int
    ) -> Dict[str, Any]:
        symbol = str(market_data.get("symbol", self.default_symbol)).upper()
        trader = self.get_coordinator(symbol)
        return trader.run_council_deliberation(
            market_data=market_data,
            news_data=news_data,
            current_spread_points=current_spread_points,
            open_positions_count=open_positions_count,
            day_of_month=day_of_month
        )
