from enum import Enum
from datetime import datetime
from typing import List
from adapters.market_data_router import get_historical_bars_dual_feed
from adapters.mt5_adapter import get_historical_bars_mt5, UnifiedBar
from adapters.symbol_mapping import resolve_symbol_and_asset_class
from adapters.symbol_constants import AssetClass

class AssetClass(Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    INDEX_FUTURES = "index_futures"
    METALS = "metals"

def get_historical_bars_asset_routed(symbol: str, start: datetime, end: datetime, timeframe: str) -> List[UnifiedBar]:
    mapping = resolve_symbol_and_asset_class(symbol)
    if mapping.asset_class in {AssetClass.EQUITY, AssetClass.CRYPTO}:
        return get_historical_bars_dual_feed(mapping.canonical, start, end, timeframe)
    elif mapping.asset_class in {AssetClass.INDEX_FUTURES, AssetClass.METALS}:
        if not mapping.mt5_symbol:
            raise ValueError(f"No MT5 symbol mapping for {symbol}")
        return get_historical_bars_mt5(mapping.mt5_symbol, start, end, timeframe)
    else:
        raise ValueError(f"Unsupported asset class: {mapping.asset_class}")
