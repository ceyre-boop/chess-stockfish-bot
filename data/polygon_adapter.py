"""
Polygon adapter for historical and live data.
Normalizes outputs to canonical tick format used by Trading Stockfish.
Adds strict tick validation to prevent malformed or synthetic data from entering the engine.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Dict, Generator, List, Optional

import requests


from dotenv import load_dotenv
import os

BASE_URL = "https://api.polygon.io"
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
POLL_INTERVAL_SECONDS = 1.0

logger = logging.getLogger(__name__)
_last_ts_seen: Optional[float] = None


class PolygonAPIError(Exception):
    pass


def _api_key() -> str:
    load_dotenv()
    key = os.getenv("POLYGON_API_KEY")
    if not key:
        raise PolygonAPIError("POLYGON_API_KEY not set in environment or .env")
    return key


def _request_json(url: str, params: Optional[Dict[str, str]] = None) -> Dict:
    params = params or {}
    params["apiKey"] = _api_key()
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 403:
                raise PolygonAPIError("403 Forbidden: Check your API key and permissions.")
            if resp.status_code == 429:
                time.sleep(min(2 * attempt, 5))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # requests exceptions
            last_exc = exc
            time.sleep(min(2 * attempt, 5))
    raise PolygonAPIError(f"Request failed after {MAX_RETRIES} attempts: {last_exc}")


def _canonical_tick_from_bar(bar: Dict, symbol: str) -> Dict[str, float]:
    # v3 aggregate schema: t (timestamp), o (open), h (high), l (low), c (close), v (volume), vw (vwap)
    ts_raw = bar.get("t")
    open_ = bar.get("o")
    high = bar.get("h")
    low = bar.get("l")
    close = bar.get("c")
    volume = bar.get("v")
    vwap = bar.get("vw")
    if ts_raw is None or open_ is None or high is None or low is None or close is None or volume is None:
        raise PolygonAPIError("Malformed bar: missing o/h/l/c/v/t fields")
    ts = float(ts_raw)
    return {
        "timestamp": ts,
        "open": float(open_),
        "high": float(high),
        "low": float(low),
        "close": float(close),
        "vwap": float(vwap) if vwap is not None else None,
        "volume": float(volume),
        "symbol": symbol,
        "raw": bar,
    }


def get_historical_bars(symbol: str, date: str, timespan: str = "minute") -> List[Dict]:
    """
    Fetch historical bars for a specific date and normalize to canonical ticks.
    date: YYYY-MM-DD
    timespan: e.g., "minute", "second"
    """
    url = f"{BASE_URL}/v2/aggs/ticker/{symbol}/range/1/{timespan}/{date}/{date}"
    params = {"sort": "asc", "limit": 50000, "adjusted": "true"}
    data = _request_json(url, params=params)
    results = data.get("results") or []
    ticks: List[Dict] = []
    last_ts: Optional[float] = None
    for bar in results:
        try:
            candidate = _canonical_tick_from_bar(bar, symbol)
            # NBBO quote for this bar
            quote = get_nbbo_quotes(symbol, candidate["timestamp"])
            if quote:
                candidate["bid"] = quote["bid"]
                candidate["ask"] = quote["ask"]
            else:
                logger.warning(f"No NBBO quote for {symbol} at {candidate['timestamp']}")
            if _validate_bar(candidate, last_ts):
                last_ts = candidate["timestamp"]
                ticks.append(candidate)
        except PolygonAPIError as exc:
            logger.critical(f"Skipping malformed bar: {exc}")
            continue
    return ticks

# New: Get NBBO quote for a symbol at a given timestamp
def get_nbbo_quotes(symbol: str, timestamp: float) -> Optional[Dict]:
    # Polygon v3 quotes endpoint (latest NBBO for symbol)
    url = f"{BASE_URL}/v3/quotes/{symbol}"
    params = {"limit": 1, "timestamp": int(timestamp), "sort": "asc"}
    try:
        data = _request_json(url, params=params)
        results = data.get("results") or []
        if not results:
            return None
        quote = results[0]
        bid = quote.get("bidPrice")
        ask = quote.get("askPrice")
        ts = quote.get("t")
        if bid is None or ask is None or ts is None:
            return None
        return {"bid": float(bid), "ask": float(ask), "timestamp": float(ts)}
    except Exception as e:
        logger.warning(f"Failed to fetch NBBO quote: {e}")
        return None

# New: Validate bar with new schema
def _validate_bar(bar: Dict, last_ts: Optional[float]) -> bool:
    required = ["timestamp", "open", "high", "low", "close", "volume", "bid", "ask"]
    for field in required:
        if field not in bar or bar[field] is None:
            logger.warning(f"Bar missing required field {field}; skipping")
            return False
    if bar["bid"] <= 0 or bar["ask"] <= 0 or bar["ask"] <= bar["bid"]:
        logger.warning(f"Invalid bid/ask: {bar}")
        return False
    if last_ts is not None and bar["timestamp"] <= last_ts:
        logger.warning("Bar timestamp is not strictly increasing; skipping")
        return False
    return True


def _canonical_tick_from_quote(payload: Dict, symbol: str) -> Optional[Dict]:
    quote = payload.get("results") or payload.get("result") or payload
    if not quote:
        return None
    bid = quote.get("bP") or quote.get("bid")
    ask = quote.get("aP") or quote.get("ask")
    ts_raw = quote.get("t") or quote.get("timestamp")
    if bid is None or ask is None or ts_raw is None:
        return None
    mid = (float(bid) + float(ask)) / 2.0
    volume = quote.get("s") or quote.get("volume") or 0.0
    ts_val_f = float(ts_raw)
    ts_val = ts_val_f / 1000.0 if ts_val_f > 1e12 else ts_val_f
    return {
        "timestamp": ts_val,
        "bid": float(bid),
        "ask": float(ask),
        "mid": mid,
        "price": mid,
        "volume": float(volume),
        "buy_volume": float(volume) / 2.0,
        "sell_volume": float(volume) / 2.0,
        "symbol": symbol,
        "raw": quote,
    }


def stream_live(
    symbol: str, poll_interval: float = POLL_INTERVAL_SECONDS
) -> Generator[Dict, None, None]:
    """
    Stream live data using REST polling (WebSocket optional). Yields canonical ticks.
    """
    url = f"{BASE_URL}/v2/last/nbbo/{symbol}"
    global _last_ts_seen
    while True:
        try:
            payload = _request_json(url)
            tick = _canonical_tick_from_quote(payload, symbol)
            if tick and _validate_tick(tick, _last_ts_seen):
                _last_ts_seen = tick["timestamp"]
                yield tick
        except Exception as exc:
            logger.critical(f"Polygon live stream error: {exc}")
            time.sleep(2.0)
        time.sleep(poll_interval)


def _validate_tick(tick: Dict, last_ts: Optional[float]) -> bool:
    required = [
        "timestamp",
        "bid",
        "ask",
        "mid",
        "volume",
        "buy_volume",
        "sell_volume",
        "raw",
    ]
    for field in required:
        if field not in tick or tick[field] is None:
            logger.critical(f"Polygon tick missing required field {field}; skipping")
            return False

    bid = float(tick["bid"])
    ask = float(tick["ask"])
    mid = float(tick["mid"])
    volume = float(tick["volume"])
    ts = float(tick["timestamp"])

    if any(math.isnan(val) or math.isinf(val) for val in [bid, ask, mid, volume, ts]):
        logger.critical("Polygon tick has NaN/inf values; skipping")
        return False
    if bid <= 0 or ask <= 0:
        logger.critical("Polygon tick has non-positive price; skipping")
        return False
    if ask <= bid:
        logger.critical("Polygon tick has non-positive spread (ask <= bid); skipping")
        return False
    spread = ask - bid
    if spread <= 0:
        logger.critical("Polygon tick spread must be positive; skipping")
        return False

    expected_mid = (bid + ask) / 2.0
    if not math.isclose(mid, expected_mid, rel_tol=0.0, abs_tol=1e-9):
        logger.critical("Polygon tick mid does not match (bid+ask)/2; skipping")
        return False

    if last_ts is not None and ts <= last_ts:
        logger.critical("Polygon tick timestamp is not strictly increasing; skipping")
        return False

    return True
