from datetime import datetime, timedelta
from adapters.asset_class_router import get_historical_bars_asset_routed
from adapters.symbol_mapping import resolve_symbol_and_asset_class

CORE_SYMBOLS = ["ES1!", "NQ", "XAUUSD", "XAGUSD"]


def _recent_window():
    end = datetime.now(datetime.timezone.utc)
    start = end - timedelta(days=3)
    return start, end


def test_core_assets_mt5_backed_bars_present():
    start, end = _recent_window()
    for symbol in CORE_SYMBOLS:
        bars = get_historical_bars_asset_routed(symbol, start, end, timeframe="M5")
        assert len(bars) > 0, f"No bars for {symbol}"
        for bar in bars:
            assert bar.timestamp_utc
            assert bar.open is not None
            assert bar.high is not None
            assert bar.low is not None
            assert bar.close is not None


def test_core_assets_no_secrets_in_logs(caplog):
    """Run a fetch and ensure logs do not contain keys or passwords"""
    start, end = _recent_window()
    for symbol in CORE_SYMBOLS:
        _ = get_historical_bars_asset_routed(symbol, start, end, timeframe="M5")
    log_text = caplog.text
    assert "AK4BMTQTHQAIPFZDBAI55LTRUY" not in log_text
    assert "FWd2pJFJJPYPLPSwMDe2kKD9wDHw9sfRsFXGPEU8VYPH" not in log_text
    assert "POLYGON_API_KEY" not in log_text
    assert "MT5_PASSWORD" not in log_text
