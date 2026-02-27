"""tests_live/test_polygon_daily.py

Pull last 30 daily bars for AAPL from Polygon and validate fields and alignment.
"""
import time
from datetime import datetime, timedelta

from adapters.polygon_adapter import get_historical_bars
from adapters.alpaca_adapter import get_historical_bars as get_alpaca_bars


def validate_bar_schema(bar):
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    for f in required:
        if f not in bar:
            raise RuntimeError(f"Missing field {f}")


def main():
    symbol = "AAPL"
    print("Polygon daily bars test — symbol:", symbol)
    end = datetime.utcnow()
    start = end - timedelta(days=60)

    try:
        poly_bars = get_historical_bars(symbol, start, end, "D1")
    except Exception as e:
        print("Polygon fetch error:", e)
        return

    if not poly_bars:
        print("No polygon bars returned")
        return

    poly = poly_bars[-30:]
    print(f"Polygon bars retrieved: {len(poly)}")
    for b in poly:
        try:
            validate_bar_schema(b)
            print(b)
        except Exception as e:
            print("Polygon bar validation error:", e)

    # Fetch Alpaca daily bars for alignment
    try:
        a_start = start
        a_end = end
        alpaca = get_alpaca_bars(symbol, a_start, a_end, "day")
    except Exception as e:
        print("Alpaca daily fetch error:", e)
        alpaca = []

    # Basic alignment check by date for overlapping days
    print("Checking alignment between Alpaca and Polygon (close prices)")
    poly_map = {}
    for b in poly:
        ts = b.get("timestamp")
        if ts is None:
            continue
        date = datetime.utcfromtimestamp(int(ts)).date() if isinstance(ts, (int, float)) else ts
        poly_map[str(date)] = b.get("close")

    mismatches = 0
    for a in alpaca[-30:]:
        try:
            a_ts = a.get("timestamp_utc") or a.get("timestamp")
            if a_ts is None:
                continue
            a_date = datetime.utcfromtimestamp(int(a_ts)).date() if isinstance(a_ts, (int, float)) else a_ts
            p_close = poly_map.get(str(a_date))
            if p_close is None:
                continue
            diff = abs(float(a.get("close", 0)) - float(p_close))
            print(f"{a_date} | Alpaca close={a.get('close')} | Polygon close={p_close} | diff={diff}")
            if diff > 1e-6:
                mismatches += 1
        except Exception as e:
            print("Alignment error:", e)

    print(f"Alignment mismatches: {mismatches}")


if __name__ == '__main__':
    main()
