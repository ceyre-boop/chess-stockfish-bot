import pytest

# Assume these are your actual class/module names; adjust as needed
from polygon_provider import PolygonProvider
from alpaca_provider import AlpacaProvider
from mt5_provider import MT5Provider
from triple_feed_router import TripleFeedRouter

@pytest.fixture
def providers():
    polygon = PolygonProvider()
    alpaca = AlpacaProvider()
    mt5 = MT5Provider()
    return polygon, alpaca, mt5

@pytest.fixture
def router(providers):
    polygon, alpaca, mt5 = providers
    # Priority: AAPL → Polygon > Alpaca, US500.cash → MT5 only
    routing_rules = {
        "AAPL": [polygon, alpaca],
        "US500.cash": [mt5]
    }
    return TripleFeedRouter(routing_rules)

def test_aapl_primary_and_fallback(router, providers, monkeypatch):
    polygon, alpaca, _ = providers

    # Simulate Polygon working
    bars = router.get_bars("AAPL", "1m", 5)
    for bar in bars:
        assert set(bar) == {"timestamp", "open", "high", "low", "close", "volume", "provider", "symbol"}
        assert bar["provider"] == "Polygon"
        assert bar["symbol"] == "AAPL"

    # Simulate Polygon failure, force fallback to Alpaca
    def fail_get_bars(*args, **kwargs):
        raise Exception("Simulated Polygon failure")
    monkeypatch.setattr(polygon, "get_bars", fail_get_bars)

    bars = router.get_bars("AAPL", "1m", 5)
    for bar in bars:
        assert bar["provider"] == "Alpaca"
        assert bar["symbol"] == "AAPL"

def test_us500_cash_mt5_only(router):
    bars = router.get_bars("US500.cash", "1m", 5)
    for bar in bars:
        assert set(bar) == {"timestamp", "open", "high", "low", "close", "volume", "provider", "symbol"}
        assert bar["provider"] == "MT5"
        assert bar["symbol"] == "US500.cash"
