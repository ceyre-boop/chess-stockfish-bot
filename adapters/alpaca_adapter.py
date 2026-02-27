from datetime import datetime, timezone
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import requests
import time
import logging

load_dotenv()

BASE_URL = "https://api.alpaca.markets"

log = logging.getLogger(__name__)

class AlpacaAPIError(Exception):
    pass

# Adapter-level monotonic timestamp guard (per-symbol)
_last_tick_ts_by_symbol: Dict[str, float] = {}
# Adapter-level monotonic snapshot tracker
_last_snapshot_by_symbol: Dict[str, Dict] = {}

def _get_api_keys() -> Dict[str, str]:
    key_id = os.getenv("ALPACA_API_KEY_ID")
    secret_key = os.getenv("ALPACA_API_SECRET_KEY")
    if not key_id or not secret_key:
        raise AlpacaAPIError("ALPACA_API_KEY_ID or ALPACA_API_SECRET_KEY not set in environment or .env")
    return {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret_key,
    }

def _parse_ts_seconds(val) -> Optional[float]:
    """Parse various timestamp formats to float seconds since epoch UTC.

    Returns None if the value is missing or cannot be parsed. Never fabricates.
    """
    if val is None:
        return None
    try:
        # numeric
        if isinstance(val, (int, float)):
            v = float(val)
            # milliseconds vs seconds heuristic
            if v > 1e12:
                return v / 1000.0
            if v > 1e9:
                return v
            return v

        s = str(val).strip()
        # numeric string
        if s.isdigit():
            v = float(s)
            if len(s) >= 13:
                return v / 1000.0
            return v

        # ISO8601
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
    keys = _get_api_keys()
    headers = {
        "APCA-API-KEY-ID": keys["APCA-API-KEY-ID"],
        "APCA-API-SECRET-KEY": keys["APCA-API-SECRET-KEY"],
    }
    url = f"{BASE_URL}/v2/stocks/{symbol}/bars"
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timeframe": timeframe,
        "limit": 10000
    }
    log.info("[ALPACA] Provider: Alpaca | Endpoint: %s | Symbol: %s", url, symbol)
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 403:
        raise AlpacaAPIError("403 Forbidden: Check your API key and permissions.")
    resp.raise_for_status()
    data = resp.json()
    bars = []
    for bar in data.get("bars", []):
        raw_ts = bar.get("t") or bar.get("timestamp") or bar.get("timestamp_utc")
        ts = _parse_ts_seconds(raw_ts)
        if ts is None:
            log.warning("[ALPACA] Dropping bar for %s due to missing/invalid timestamp: %s", symbol, raw_ts)
            continue

        # Per-symbol monotonic check (do not fabricate)
        last_ts = _last_tick_ts_by_symbol.get(symbol)
        if last_ts is not None and ts <= last_ts:
            log.warning("[ALPACA] Dropping non-monotonic bar for %s: %s <= %s", symbol, ts, last_ts)
            continue
        _last_tick_ts_by_symbol[symbol] = ts

        bid = bar.get("bp") if bar.get("bp") is not None else bar.get("bid") if bar.get("bid") is not None else 0.0
        ask = bar.get("ap") if bar.get("ap") is not None else bar.get("ask") if bar.get("ask") is not None else 0.0
        try:
            bid = float(bid)
        except Exception:
            bid = 0.0
        try:
            ask = float(ask)
        except Exception:
            ask = 0.0

        # Determine last price
        last_price = None
        try:
            if bar.get("c") is not None:
                last_price = float(bar.get("c"))
            elif bid > 0 and ask > 0:
                last_price = (bid + ask) / 2.0
            else:
                last_price = None
        except Exception:
            last_price = None

        if last_price is None:
            log.warning("[ALPACA] Dropping bar for %s due to missing last/close and bid/ask", symbol)
            continue

        # Build canonical dict
        canonical = {
            "symbol": symbol,
            "timestamp": float(ts),
            "bid": float(bid),
            "ask": float(ask),
            "last": float(last_price),
            "volume": float(bar.get("v") or 0.0),
            "source": "alpaca",
        }

        bars.append(canonical)
    log.info("[ALPACA] Bars returned: %d", len(bars))
    return bars


def get_latest_snapshot(symbol: str) -> Optional[Dict]:
    """Fetch latest Alpaca trade/quote and return a canonical snapshot or None.

    Uses the trades/latest and quotes/latest endpoints where available, falls
    back to recent bars. Enforces monotonicity and schema validation.
    """
    from data import canonical_schema as cs
    DEBUG = bool(os.getenv('DEBUG', ''))

    keys = _get_api_keys()
    headers = {
        "APCA-API-KEY-ID": keys["APCA-API-KEY-ID"],
        "APCA-API-SECRET-KEY": keys["APCA-API-SECRET-KEY"],
    }

    # Try latest trade
    trade = None
    try:
        url = f"{BASE_URL}/v2/stocks/{symbol}/trades/latest"
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            trade = data.get('trade') or data.get('last')
    except Exception:
        trade = None

    # Try latest quote if trade missing
    quote = None
    try:
        urlq = f"{BASE_URL}/v2/stocks/{symbol}/quotes/latest"
        respq = requests.get(urlq, headers=headers, timeout=5)
        if respq.status_code == 200:
            qd = respq.json()
            quote = qd.get('quote')
    except Exception:
        quote = None

    # Fallback: last 1-minute bar
    bar = None
    if trade is None and quote is None:
        try:
            urlb = f"{BASE_URL}/v2/stocks/{symbol}/bars"
            params = {"timeframe": "1Min", "limit": 1}
            respb = requests.get(urlb, headers=headers, params=params, timeout=5)
            if respb.status_code == 200:
                bd = respb.json()
                bars = bd.get('bars') or []
                if bars:
                    bar = bars[-1]
        except Exception:
            bar = None

    # Build snapshot candidate
    ts = None
    price = None
    bid = None
    ask = None
    vol = None

    if trade:
        ts = _parse_ts_seconds(trade.get('t') or trade.get('timestamp') or trade.get('timestamp_utc'))
        price = trade.get('p') or trade.get('price')
        vol = trade.get('s') or trade.get('size') or trade.get('v')
    if quote and ts is None:
        ts = _parse_ts_seconds(quote.get('t') or quote.get('timestamp') or quote.get('timestamp_utc'))
    if quote:
        bid = quote.get('bp') or quote.get('b') or quote.get('bid')
        ask = quote.get('ap') or quote.get('a') or quote.get('ask')

    if bar and ts is None:
        ts = _parse_ts_seconds(bar.get('t') or bar.get('timestamp'))
        price = price or bar.get('c')
        vol = vol or bar.get('v')

    ts = _parse_ts_seconds(ts) if ts is not None else None
    try:
        price = None if price is None else float(price)
    except Exception:
        price = None
    try:
        bid = None if bid is None else float(bid)
    except Exception:
        bid = None
    try:
        ask = None if ask is None else float(ask)
    except Exception:
        ask = None
    try:
        vol = None if vol is None else float(vol)
    except Exception:
        vol = None

    if ts is None:
        return None

    # price fallback: use mid if last missing
    if price is None and bid is not None and ask is not None:
        price = (bid + ask) / 2.0

    spread = None
    if bid is not None and ask is not None:
        spread = ask - bid

    # quality
    now = time.time()
    stale = (now - ts) > 2.0
    partial = any(x is None for x in (bid, ask, price))

    snapshot = {
        'symbol': symbol,
        'provider': 'alpaca',
        'timestamp': float(ts),
        'price': price,
        'bid': bid,
        'ask': ask,
        'spread': spread,
        'volume': vol,
        'bar': {'open': None, 'high': None, 'low': None, 'close': None, 'volume': None, 'tf': None},
        'quality': {'stale': stale, 'synthetic': False, 'partial': partial},
    }

    # Monotonicity
    prev = _last_snapshot_by_symbol.get(symbol)
    if prev is not None:
        prev_ts = prev.get('timestamp')
        if prev_ts is not None:
            if snapshot['timestamp'] < prev_ts:
                log.info('Alpaca adapter: dropping older snapshot for %s (%s < %s)', symbol, snapshot['timestamp'], prev_ts)
                return None
            if snapshot['timestamp'] == prev_ts and (snapshot.get('price'), snapshot.get('bid'), snapshot.get('ask'), snapshot.get('volume')) == (prev.get('price'), prev.get('bid'), prev.get('ask'), prev.get('volume')):
                return None

    # Validate
    snapshot = cs.canonicalize_missing_fields(snapshot)
    ok = cs.validate_snapshot(snapshot)
    if not ok:
        log.warning('Alpaca adapter: produced snapshot failed validation for %s', symbol)
        if DEBUG:
            cs.assert_snapshot(snapshot)
        return None

    _last_snapshot_by_symbol[symbol] = snapshot
    return snapshot
