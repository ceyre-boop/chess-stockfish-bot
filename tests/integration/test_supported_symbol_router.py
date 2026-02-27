import os
from datetime import datetime, timedelta
import pytest
from adapters.market_data_router import get_unified_bars
from adapters.mt5_adapter import UnifiedBar
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_SYMBOLS = ["AAPL", "MSFT", "SPY", "BTCUSD"]

REQUIRED_FIELDS = [
    "timestamp_utc", "open", "high", "low", "close", "volume", "bid", "ask", "vwap"
]

def assert_unified_bar_schema(bar):
    for field in REQUIRED_FIELDS:
        assert field in bar, f"Missing field: {field}"
        assert bar[field] is not None, f"Field {field} is None"
        if isinstance(bar[field], float):
            assert not (bar[field] != bar[field]), f"Field {field} is NaN"
    assert isinstance(bar["timestamp_utc"], str)
    assert isinstance(bar["open"], float)
    assert isinstance(bar["high"], float)
    assert isinstance(bar["low"], float)
    assert isinstance(bar["close"], float)
    assert isinstance(bar["volume"], (float, int))

@pytest.mark.parametrize("symbol", SUPPORTED_SYMBOLS)
def test_triple_feed_router_supported_symbols(symbol, caplog):
    end = datetime.utcnow()
    start = end - timedelta(minutes=5)
    bars = get_unified_bars(symbol, start, end, "minute")
    assert bars, f"No bars returned for {symbol}"
    for bar in bars:
        assert_unified_bar_schema(bar)
    # Determinism: repeated call returns same bars
    bars2 = get_unified_bars(symbol, start, end, "minute")
    assert bars == bars2, f"Non-deterministic results for {symbol}"
    # Provider log check
    provider_logs = [msg for msg in caplog.messages if "Provider:" in msg]
    assert provider_logs, "No provider logs found"
    for msg in provider_logs:
        assert "AK4BMTQTHQAIPFZDBAI55LTRUY" not in msg
        assert "FWd2pJFJJPYPLPSwMDe2kKD9wDHw9sfRsFXGPEU8VYPH" not in msg
        assert "POLYGON_API_KEY" not in msg
        assert "MT5_PASSWORD" not in msg
    # Print provider and bar count for debugging
    print(f"Provider log: {provider_logs[-1] if provider_logs else 'N/A'}")
    print(f"Bars returned: {len(bars)}")
