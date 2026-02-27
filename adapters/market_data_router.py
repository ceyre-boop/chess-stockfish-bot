
from datetime import datetime
from typing import List, Dict
import logging
from adapters.polygon_adapter import get_historical_bars as get_polygon_bars
from adapters.alpaca_adapter import get_historical_bars as get_alpaca_bars

__all__ = [
    "get_unified_bars",
    "get_historical_bars_dual_feed",
]

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "timestamp_utc", "open", "high", "low", "close", "volume", "bid", "ask", "vwap"
]

def get_historical_bars_dual_feed(symbol: str, start: datetime, end: datetime, timeframe: str):
    """
    Alias for get_unified_bars for dual-feed (Polygon primary, Alpaca fallback).
    """
    return get_unified_bars(symbol, start, end, timeframe)

def validate_bar(bar: Dict) -> bool:
    for field in REQUIRED_FIELDS:
        if field not in bar or bar[field] is None:
            return False
    if not isinstance(bar["timestamp_utc"], (int, float)) or bar["timestamp_utc"] <= 0:
        return False
    if bar["volume"] is None or bar["volume"] == 0:
        return False
    if bar["bid"] is None or bar["ask"] is None:
        return False
    if bar["bid"] >= bar["ask"]:
        return False
    return True

def get_unified_bars(symbol: str, start: datetime, end: datetime, timeframe: str) -> List[Dict]:
    bars = get_polygon_bars(symbol, start, end, timeframe)
    valid_bars = [bar for bar in bars if validate_bar(bar)]
    if valid_bars:
        logger.info(f"Provider: Polygon | Bars: {len(valid_bars)}")
        return valid_bars
    # Fallback to Alpaca
    bars = get_alpaca_bars(symbol, start, end, timeframe)
    valid_bars = [bar for bar in bars if validate_bar(bar)]
    logger.info(f"Provider: Alpaca | Bars: {len(valid_bars)}")
    return valid_bars
from datetime import datetime
from datetime import datetime
from datetime import datetime
