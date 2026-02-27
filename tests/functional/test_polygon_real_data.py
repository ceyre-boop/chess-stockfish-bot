import os
import pytest
from dotenv import load_dotenv
from data.polygon_adapter import get_historical_bars, get_nbbo_quotes

load_dotenv()
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

@pytest.mark.skipif(not POLYGON_API_KEY, reason="No Polygon API key set")
def test_polygon_real_data():
    symbol = "AAPL"
    date = "2025-12-01"
    bars = get_historical_bars(symbol, date, timespan="minute")
    assert bars, "No bars returned from Polygon API"
    for bar in bars:
        assert "timestamp" in bar and bar["timestamp"] > 0, f"Invalid timestamp: {bar}"
        assert "volume" in bar and bar["volume"] > 0, f"Invalid volume: {bar}"
        assert "open" in bar and bar["open"] > 0, f"Invalid open: {bar}"
        assert "close" in bar and bar["close"] > 0, f"Invalid close: {bar}"
        assert "high" in bar and bar["high"] > 0, f"Invalid high: {bar}"
        assert "low" in bar and bar["low"] > 0, f"Invalid low: {bar}"
        # NBBO quote check
        quote = get_nbbo_quotes(symbol, bar["timestamp"])
        assert quote, f"No NBBO quote for {symbol} at {bar['timestamp']}"
        assert "bid" in quote and quote["bid"] > 0, f"Invalid bid: {quote}"
        assert "ask" in quote and quote["ask"] > 0, f"Invalid ask: {quote}"
        assert quote["ask"] > quote["bid"], f"Ask not greater than bid: {quote}"
        assert "timestamp" in quote and quote["timestamp"] > 0, f"Invalid quote timestamp: {quote}"
