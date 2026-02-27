import os
from datetime import datetime, timedelta
from adapters.market_data_router import get_unified_bars

def test_dual_feed_market_data(monkeypatch, caplog):
    # Simulate Polygon returning malformed bars
    def fake_polygon_bars(symbol, start, end, timeframe):
        return [{"timestamp_utc": None, "open": None, "high": None, "low": None, "close": None, "volume": None, "bid": None, "ask": None, "vwap": None}]
    # Simulate Alpaca returning valid bars
    def fake_alpaca_bars(symbol, start, end, timeframe):
        return [{
            "timestamp_utc": 1234567890,
            "open": 100.0,
            "high": 110.0,
            "low": 90.0,
            "close": 105.0,
            "volume": 1000,
            "bid": 104.5,
            "ask": 105.5,
            "vwap": 104.9
        }]
    monkeypatch.setattr("adapters.polygon_adapter.get_historical_bars", fake_polygon_bars)
    monkeypatch.setattr("adapters.alpaca_adapter.get_historical_bars", fake_alpaca_bars)
    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow()
    bars = get_unified_bars("AAPL", start, end, "minute")
    assert bars
    bar = bars[0]
    assert all(field in bar for field in ["timestamp_utc", "open", "high", "low", "close", "volume", "bid", "ask", "vwap"])
    assert bar["bid"] < bar["ask"]
    assert bar["volume"] > 0
    # Check provider log
    assert any("Provider: Alpaca" in r for r in caplog.messages)
    # Ensure no secrets in logs
    for msg in caplog.messages:
        assert "AK4BMTQTHQAIPFZDBAI55LTRUY" not in msg
        assert "FWd2pJFJJPYPLPSwMDe2kKD9wDHw9sfRsFXGPEU8VYPH" not in msg
        assert "7w3DiF3U5v4RTJfoplVpamaFOfbSG8Jm" not in msg
