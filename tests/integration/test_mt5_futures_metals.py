import os
import time
import pytest
from adapters.mt5_adapter import init_mt5_from_env, get_historical_bars_mt5, UnifiedBar

SYMBOL_MAP = {
    "ES1!": "US500.cash",
    "NQ": "NAS100",
    "XAUUSD": "XAUUSD",
    "XAGUSD": "XAGUSD",
}

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

def assert_unified_bar_schema(bar):
    assert isinstance(bar, UnifiedBar), "Bar is not UnifiedBar instance"
    for field in REQUIRED_FIELDS:
        value = getattr(bar, field, None)
        assert value is not None, f"Missing value for {field}"
        if isinstance(value, float):
            assert not (value != value), f"NaN detected in {field}"

@pytest.mark.integration
@pytest.mark.parametrize("symbol,mt5_symbol", list(SYMBOL_MAP.items()))
def test_mt5_futures_metals_real_data(symbol, mt5_symbol):
    # Initialize MT5 from environment
    init_mt5_from_env()

    # Request last 5 minutes of bars (M1 timeframe)
    end_time = time.time()
    start_time = end_time - 5 * 60
    from datetime import datetime
    bars1 = get_historical_bars_mt5(
        mt5_symbol,
        datetime.utcfromtimestamp(start_time),
        datetime.utcfromtimestamp(end_time),
        "M1"
    )
    assert isinstance(bars1, list) and len(bars1) > 0, f"No bars returned for {mt5_symbol}"
    for bar in bars1:
        assert_unified_bar_schema(bar)

    # Determinism: repeat call and compare
    bars2 = get_historical_bars_mt5(
        mt5_symbol,
        datetime.utcfromtimestamp(start_time),
        datetime.utcfromtimestamp(end_time),
        "M1"
    )
    assert len(bars1) == len(bars2), "Bar count mismatch on repeated call"
    for b1, b2 in zip(bars1, bars2):
        for field in REQUIRED_FIELDS:
            v1 = getattr(b1, field)
            v2 = getattr(b2, field)
            assert v1 == v2, f"Non-deterministic value for {field}"

    # Debug print (no secrets)
    print(f"MT5 symbol: {mt5_symbol}, bars returned: {len(bars1)}")
