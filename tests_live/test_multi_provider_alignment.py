"""tests_live/test_multi_provider_alignment.py

Pull last 10 Alpaca 1-minute bars and last 10 Polygon daily bars for AAPL.
Align by date and print timestamp | Alpaca close | Polygon close | diff
"""
from datetime import datetime, timedelta

from adapters.alpaca_adapter import get_historical_bars as get_alpaca_bars
from adapters.polygon_adapter import get_historical_bars as get_polygon_bars


def ts_to_date(ts):
    try:
        # polygon returns epoch ms or s; alpaca returns t or iso
        if isinstance(ts, (int, float)):
            # Heuristic: >1e12 => ms
            if ts > 1e12:
                return datetime.utcfromtimestamp(ts/1000).date()
            return datetime.utcfromtimestamp(ts).date()
        if isinstance(ts, str):
            return datetime.fromisoformat(ts).date()
    except Exception:
        return None


def main():
    symbol = "AAPL"
    print("Multi-provider alignment test —", symbol)
    now = datetime.utcnow()
    start = now - timedelta(days=60)

    try:
        alpaca = get_alpaca_bars(symbol, now - timedelta(minutes=20), now, "1Min")
    except Exception as e:
        print("Alpaca fetch error:", e)
        alpaca = []

    try:
        polygon = get_polygon_bars(symbol, start, now, "D1")
    except Exception as e:
        print("Polygon fetch error:", e)
        polygon = []

    alpaca_recent = alpaca[-10:]
    polygon_recent = polygon[-10:]

    poly_map = {}
    for p in polygon_recent:
        d = ts_to_date(p.get('timestamp'))
        if d:
            poly_map[str(d)] = p.get('close')

    print("timestamp | Alpaca close | Polygon close | diff")
    for a in alpaca_recent:
        a_ts = a.get('timestamp_utc') or a.get('timestamp')
        a_date = ts_to_date(a_ts)
        a_close = a.get('close')
        p_close = poly_map.get(str(a_date))
        diff = None
        if p_close is not None and a_close is not None:
            try:
                diff = float(a_close) - float(p_close)
            except Exception:
                diff = None
        print(f"{a_date} | {a_close} | {p_close} | {diff}")


if __name__ == '__main__':
    main()
