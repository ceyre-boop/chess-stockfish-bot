from datetime import datetime, timezone
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import requests
import time
import logging

load_dotenv()

BASE_URL = "https://api.polygon.io/v3"

log = logging.getLogger(__name__)

class PolygonAPIError(Exception):
    pass

# Adapter-level monotonic timestamp guard (per-symbol)
_last_tick_ts_by_symbol: Dict[str, float] = {}
# Adapter-level monotonic snapshot tracker
_last_snapshot_by_symbol: Dict[str, Dict] = {}

def _get_api_key() -> str:
    key = os.getenv("POLYGON_API_KEY")
    if not key:
        raise PolygonAPIError("POLYGON_API_KEY not set in environment or .env")
    return key

def _parse_ts_seconds(val) -> Optional[float]:
    """Parse Polygon timestamp formats to float seconds since epoch UTC.

    Accepts nanosecond/millisecond/second epoch values and ISO strings.
    Returns None for missing/invalid values. Never fabricates.
    """
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            v = float(val)
            # Polygon may return epoch nanoseconds or milliseconds
            if v > 1e15:  # nanoseconds
                return v / 1_000_000_000.0
            if v > 1e12:  # milliseconds
                return v / 1000.0
            return v

        s = str(val).strip()
        if s.isdigit():
            v = float(s)
            if len(s) >= 16:
                return v / 1_000_000_000.0
            if len(s) >= 13:
                return v / 1000.0
            return v

        if "T" in s or "-" in s:
            try:
                s2 = s.replace("Z", "+00:00")
                dt = datetime.fromisoformat(s2)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return float(dt.timestamp())
            except Exception:
                return None

        return None
    except Exception:
        return None

def get_historical_bars(symbol: str, start: datetime, end: datetime, timeframe: str) -> List[Dict]:
    global _last_tick_ts_by_symbol
    api_key = _get_api_key()
    # Map timeframe
    multiplier = 1
    timespan = "minute"
    if timeframe in ["M1", "1Min"]:
        multiplier = 1
        timespan = "minute"
    # Construct endpoint and params
    url = f"{BASE_URL}/bars/{symbol}"
    params = {
        "multiplier": multiplier,
        "timespan": timespan,
        "limit": 50,
        "sort": "asc",
        "apiKey": api_key,
    }
    log.info("[POLYGON] Provider: Polygon | Endpoint: %s | Symbol: %s", url, symbol)
    resp = requests.get(url, params=params)
    if resp.status_code == 403:
        raise PolygonAPIError("403 Forbidden: Check your API key and permissions.")
    # If Polygon returns a 404 or empty, don't fabricate synthetic ticks; return empty list
    if resp.status_code == 404:
        log.warning("[POLYGON] 404 from Polygon bars endpoint for %s; returning empty result.", symbol)
        return []
    resp.raise_for_status()
    data = resp.json()
    bars = []
    for bar in data.get("results", []):
        raw_ts = bar.get("t") or bar.get("timestamp")
        ts = _parse_ts_seconds(raw_ts)
        if ts is None:
            log.warning("[POLYGON] Dropping bar for %s due to missing/invalid timestamp: %s", symbol, raw_ts)
            continue

        # Per-symbol monotonicity check (do not fabricate)
        last_ts = _last_tick_ts_by_symbol.get(symbol)
        if last_ts is not None and ts <= last_ts:
            log.warning("[POLYGON] Dropping non-monotonic bar for %s: %s <= %s", symbol, ts, last_ts)
            continue
        _last_tick_ts_by_symbol[symbol] = ts

        # Normalize prices; Polygon bars typically don't include bid/ask, use close as fallback
        try:
            close_ = float(bar.get("c")) if bar.get("c") is not None else None
        except Exception:
            close_ = None

        if close_ is None:
            log.warning("[POLYGON] Dropping bar for %s due to missing close price", symbol)
            continue

        bid = close_
        ask = close_
        volume = float(bar.get("v") or 0.0)

        canonical = {
            "symbol": symbol,
            "timestamp": float(ts),
            "bid": float(bid),
            "ask": float(ask),
            "last": float(close_),
            "volume": volume,
            "source": "polygon",
        }

        bars.append(canonical)
    log.info("[POLYGON] Bars returned: %d", len(bars))
    return bars


def get_latest_snapshot(symbol: str) -> Optional[Dict]:
    """Fetch latest Polygon bar and convert to canonical snapshot.

    Polygon typically provides bars; we map the latest bar close to a snapshot.
    """
    from data import canonical_schema as cs
    DEBUG = bool(os.getenv('DEBUG', ''))

    api_key = _get_api_key()
    url = f"{BASE_URL}/bars/{symbol}/latest"
    params = {"apiKey": api_key}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        bar = data.get('ticks') or data.get('results') or data.get('bar') or data.get('results', [])
        # normalize structure: if list-like, take last
        if isinstance(bar, list) and bar:
            bar = bar[-1]
    except Exception:
        return None

    # Attempt to extract close/time/volume
    raw_ts = None
    close_ = None
    volume = None
    try:
        if isinstance(bar, dict):
            raw_ts = bar.get('t') or bar.get('timestamp') or bar.get('close_time')
            close_ = bar.get('c') or bar.get('close')
            volume = bar.get('v') or bar.get('volume')
    except Exception:
        return None

    ts = _parse_ts_seconds(raw_ts)
    if ts is None or close_ is None:
        return None

    try:
        price = float(close_)
    except Exception:
        return None

    bid = None
    ask = None
    spread = None

    stale = (time.time() - float(ts)) > 5.0
    partial = True

    snapshot = {
        'symbol': symbol,
        'provider': 'polygon',
        'timestamp': float(ts),
        'price': price,
        'bid': bid,
        'ask': ask,
        'spread': spread,
        'volume': float(volume) if volume is not None else None,
        'bar': {'open': None, 'high': None, 'low': None, 'close': price, 'volume': float(volume) if volume is not None else None, 'tf': None},
        'quality': {'stale': stale, 'synthetic': False, 'partial': partial},
    }

    # monotonicity
    prev = _last_snapshot_by_symbol.get(symbol)
    if prev is not None:
        prev_ts = prev.get('timestamp')
        if prev_ts is not None:
            if snapshot['timestamp'] < prev_ts:
                return None
            if snapshot['timestamp'] == prev_ts and snapshot.get('price') == prev.get('price'):
                return None

    # validate
    snapshot = cs.canonicalize_missing_fields(snapshot)
    ok = cs.validate_snapshot(snapshot)
    if not ok:
        log.warning('Polygon adapter: produced snapshot failed validation for %s', symbol)
        if DEBUG:
            cs.assert_snapshot(snapshot)
        return None

    _last_snapshot_by_symbol[symbol] = snapshot
    return snapshot
