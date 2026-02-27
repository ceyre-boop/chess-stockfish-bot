import os
import time
import pytest
from adapters.market_data_router import get_unified_bars
from adapters.mt5_adapter import UnifiedBar
from engine.decision_loop import run_decision_loop

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

@pytest.mark.functional
@pytest.mark.parametrize("symbol,mt5_symbol", list(SYMBOL_MAP.items()))
def test_futures_metals_functional_real_data(symbol, mt5_symbol):
    # Initialize router (credentials loaded from .env internally)
    # Request last 5 minutes of bars via router function
    end_time = time.time()
    start_time = end_time - 5 * 60
    from datetime import datetime
    bars1 = get_unified_bars(
        symbol,
        datetime.utcfromtimestamp(start_time),
        datetime.utcfromtimestamp(end_time),
        "M1"
    )
    assert isinstance(bars1, list) and len(bars1) > 0, f"No bars returned for {symbol}"
    for bar in bars1:
        assert_unified_bar_schema(bar)

    # Determinism: repeat call and compare
    bars2 = get_unified_bars(
        symbol,
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

    # Build DecisionFrame and run engine pipeline
    frame = {
        "symbol": symbol,
        "bars": bars1,
        "timestamp": bars1[-1].timestamp_utc,
    }
    action1, metadata1 = run_decision_loop(frame)
    assert action1 is not None, "No action returned"
    for key in [
        "regime_cluster",
        "participant_likelihoods",
        "ev_features",
        "search_weights",
        "risk_envelope",
    ]:
        assert key in metadata1, f"Missing {key} in metadata"

    # Determinism: repeat engine call
    action2, metadata2 = run_decision_loop(frame)
    assert action1 == action2, "Non-deterministic action"
    assert metadata1 == metadata2, "Non-deterministic metadata"

    # Debug print (no secrets)
    print(f"Symbol: {symbol}, bars: {len(bars1)}")
