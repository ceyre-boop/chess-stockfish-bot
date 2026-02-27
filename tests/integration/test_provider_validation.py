import os
import time
import pytest
from datetime import datetime, timedelta
from adapters.polygon_adapter import get_historical_bars as get_polygon_bars
from adapters.alpaca_adapter import get_historical_bars as get_alpaca_bars
from adapters.mt5_adapter import get_historical_bars_mt5, UnifiedBar, init_mt5_from_env

REQUIRED_FIELDS = [
    "timestamp_utc",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "bid",
    "ask",
    "vwap",
]

def assert_unified_schema(bar):
    for field in REQUIRED_FIELDS:
        assert field in bar if isinstance(bar, dict) else hasattr(bar, field), f"Missing field: {field}"
        value = bar[field] if isinstance(bar, dict) else getattr(bar, field)
        assert value is not None, f"Field {field} is None"
        if isinstance(value, float):
            assert not (value != value), f"Field {field} is NaN"

@pytest.mark.integration
def test_polygon_provider_direct():
    symbol = "X:BTCUSD"
    end = datetime.utcnow()
    start = end - timedelta(minutes=5)
    bars1 = get_polygon_bars(symbol, start, end, "minute")
    bars2 = get_polygon_bars(symbol, start, end, "minute")
    assert isinstance(bars1, list) and len(bars1) > 0, "No bars returned from Polygon"
    assert len(bars1) == len(bars2), "Bar count mismatch on repeated Polygon call"
    for b1, b2 in zip(bars1, bars2):
        for field in REQUIRED_FIELDS:
            v1 = b1[field]
            v2 = b2[field]
            assert v1 == v2, f"Non-deterministic value for {field}"
        assert_unified_schema(b1)
    print(f"[TEST] Provider: Polygon | Symbol: {symbol} | Bars: {len(bars1)}")

@pytest.mark.integration
def test_alpaca_provider_direct():
    symbol = "AAPL"
    end = datetime.utcnow()
    start = end - timedelta(minutes=5)
    bars1 = get_alpaca_bars(symbol, start, end, "1Min")
    bars2 = get_alpaca_bars(symbol, start, end, "1Min")
    assert isinstance(bars1, list) and len(bars1) > 0, "No bars returned from Alpaca"
    assert len(bars1) == len(bars2), "Bar count mismatch on repeated Alpaca call"
    for b1, b2 in zip(bars1, bars2):
        for field in REQUIRED_FIELDS:
            v1 = b1[field]
            v2 = b2[field]
            assert v1 == v2, f"Non-deterministic value for {field}"
        assert_unified_schema(b1)
    print(f"[TEST] Provider: Alpaca | Symbol: {symbol} | Bars: {len(bars1)}")

@pytest.mark.integration
@pytest.mark.parametrize("symbol", ["US500.cash", "NAS100", "XAUUSD", "XAGUSD"])
def test_mt5_provider_direct(symbol):
    init_mt5_from_env()
    end = datetime.utcnow()
    start = end - timedelta(minutes=5)
    bars1 = get_historical_bars_mt5(symbol, start, end, "M1")
    bars2 = get_historical_bars_mt5(symbol, start, end, "M1")
    assert isinstance(bars1, list) and len(bars1) > 0, f"No bars returned from MT5 for {symbol}"
    assert len(bars1) == len(bars2), f"Bar count mismatch on repeated MT5 call for {symbol}"
    for b1, b2 in zip(bars1, bars2):
        for field in REQUIRED_FIELDS:
            v1 = getattr(b1, field)
            v2 = getattr(b2, field)
            assert v1 == v2, f"Non-deterministic value for {field} in {symbol}"
        assert_unified_schema(b1)
    print(f"[TEST] Provider: MT5 | Symbol: {symbol} | Bars: {len(bars1)}")
