from dataclasses import dataclass
from typing import Dict, Optional
from adapters.symbol_constants import AssetClass

@dataclass
class SymbolMapping:
    canonical: str
    asset_class: AssetClass
    polygon_symbol: Optional[str]
    alpaca_symbol: Optional[str]
    mt5_symbol: Optional[str]

_SYMBOL_MAP: Dict[str, SymbolMapping] = {
    "ES1!": SymbolMapping(
        canonical="ES1!",
        asset_class=AssetClass.INDEX_FUTURES,
        polygon_symbol=None,
        alpaca_symbol=None,
        mt5_symbol="US500.cash",
    ),
    "NQ": SymbolMapping(
        canonical="NQ",
        asset_class=AssetClass.INDEX_FUTURES,
        polygon_symbol=None,
        alpaca_symbol=None,
        mt5_symbol="NAS100",
    ),
    "XAUUSD": SymbolMapping(
        canonical="XAUUSD",
        asset_class=AssetClass.METALS,
        polygon_symbol=None,
        alpaca_symbol=None,
        mt5_symbol="XAUUSD",
    ),
    "XAGUSD": SymbolMapping(
        canonical="XAGUSD",
        asset_class=AssetClass.METALS,
        polygon_symbol=None,
        alpaca_symbol=None,
        mt5_symbol="XAGUSD",
    ),
    "AAPL": SymbolMapping(
        canonical="AAPL",
        asset_class=AssetClass.EQUITY,
        polygon_symbol="AAPL",
        alpaca_symbol="AAPL",
        mt5_symbol=None,
    ),
    "SPY": SymbolMapping(
        canonical="SPY",
        asset_class=AssetClass.EQUITY,
        polygon_symbol="SPY",
        alpaca_symbol="SPY",
        mt5_symbol=None,
    ),
    "BTCUSD": SymbolMapping(
        canonical="BTCUSD",
        asset_class=AssetClass.CRYPTO,
        polygon_symbol="X:BTCUSD",
        alpaca_symbol="BTCUSD",
        mt5_symbol=None,
    ),
}

def resolve_symbol_and_asset_class(canonical_symbol: str) -> SymbolMapping:
    mapping = _SYMBOL_MAP.get(canonical_symbol)
    if not mapping:
        raise ValueError(f"Unknown canonical symbol: {canonical_symbol}")
    return mapping
