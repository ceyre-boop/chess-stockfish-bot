"""tests_live/test_mt5_ticks_and_candles.py

Connects to MT5, pulls last 20 ticks for US500.cash and last 10 1-minute candles.
Prints bid/ask, spread, tick cadence and volatility. Runs for ~30 seconds.
"""
import time
import math
from datetime import datetime, timedelta

try:
    import MetaTrader5 as mt5
except Exception as e:
    mt5 = None

from adapters.mt5_adapter import init_mt5_from_env, get_historical_bars_mt5


def safe_print(*args, **kwargs):
    print(*args, **kwargs)


def get_recent_ticks(symbol, count=20):
    if mt5 is None:
        raise RuntimeError("MetaTrader5 package not available")
    # copy_ticks_from may not exist in all environments; fall back to symbol_info_tick
    try:
        now = datetime.utcnow()
        from datetime import timezone
        utc_to = now.replace(tzinfo=timezone.utc)
        utc_from = utc_to - timedelta(seconds=60)
        ticks = mt5.copy_ticks_range(symbol, utc_from, utc_to, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            t = mt5.symbol_info_tick(symbol)
            raw = [t] if t is not None else []
        else:
            raw = list(ticks[-count:])

        # Convert SDK objects / structured entries into canonical primitive dicts
        out = []
        for t in raw:
            try:
                # Prefer time_msc if available
                ts = None
                if hasattr(t, "time_msc") and getattr(t, "time_msc"):
                    try:
                        ts = float(getattr(t, "time_msc")) / 1000.0
                    except Exception:
                        ts = None
                if ts is None and hasattr(t, "time"):
                    try:
                        ts = float(getattr(t, "time"))
                    except Exception:
                        ts = None

                # For structured arrays / dict-like entries, also support item access
                def _get(k, default=None):
                    try:
                        if isinstance(t, dict):
                            return t.get(k, default)
                        return getattr(t, k, default)
                    except Exception:
                        try:
                            return t[k]
                        except Exception:
                            return default

                bid = float(_get("bid", 0.0) or 0.0)
                ask = float(_get("ask", 0.0) or 0.0)
                last = float(_get("last", 0.0) or 0.0)
                volume = float(_get("volume", 0) or 0)

                canonical = {
                    "symbol": symbol,
                    "timestamp": ts,
                    "bid": bid,
                    "ask": ask,
                    "last": last,
                    "volume": volume,
                    "source": "mt5",
                }
                out.append(canonical)
            except Exception:
                continue
        return out
    except Exception as e:
        raise


def compute_tick_frequency(ticks):
    if not ticks:
        return 0.0
    times = [t.time for t in ticks if hasattr(t, 'time')]
    if len(times) < 2:
        return 0.0
    intervals = [t2 - t1 for t1, t2 in zip(times[:-1], times[1:])]
    return sum(intervals) / len(intervals)


def compute_volatility_from_candles(candles):
    if not candles:
        return 0.0
    highs = [c.close if hasattr(c, 'high') is False else c.high for c in candles]
    lows = [c.close if hasattr(c, 'low') is False else c.low for c in candles]
    # crude volatility: average(high-low)
    vals = []
    for c in candles:
        try:
            h = getattr(c, 'high', None) or getattr(c, 'close', None)
            l = getattr(c, 'low', None) or getattr(c, 'close', None)
            vals.append(abs(h - l))
        except Exception:
            continue
    return sum(vals) / len(vals) if vals else 0.0


def main():
    symbol = "US500.cash"
    print("MT5 ticks & candles test — symbol:", symbol)
    try:
        init_mt5_from_env()
    except Exception as e:
        print("MT5 init failed:", e)
        return

    # Pull initial candles
    end = datetime.utcnow()
    start = end - timedelta(minutes=20)
    try:
        candles = get_historical_bars_mt5(symbol, start, end, "M1")
    except Exception as e:
        print("MT5 candle fetch error:", e)
        candles = []

    # Print last 10 candles
    print("Last candles (up to 10):")
    for c in (candles[-10:] if candles else []):
        print(vars(c) if hasattr(c, '__dict__') else c)

    # Run short tick loop (~30s)
    start_t = time.time()
    while time.time() - start_t < 30:
        try:
            ticks = get_recent_ticks(symbol, count=20)
            freq = compute_tick_frequency(ticks)
            vol = compute_volatility_from_candles(candles[-10:] if candles else [])

            # Print summary
            print(f"Ticks fetched: {len(ticks)} | Avg interval: {freq:.3f}s | Volatility(candles): {vol:.6f}")
            # Show top 3 ticks
            for t in ticks[:3]:
                try:
                    print(f"tick timestamp={t.get('timestamp',None)} bid={t.get('bid',None)} ask={t.get('ask',None)}")
                except Exception:
                    print("tick print error")
        except Exception as e:
            print("Tick loop error:", e)
        time.sleep(1)

    try:
        mt5.shutdown()
    except Exception:
        pass


if __name__ == '__main__':
    main()
