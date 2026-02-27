"""
Unified market feed interface for Trading Stockfish.
Supports polygon historical/live, mt5 live, and scenario replay sources.
"""

from __future__ import annotations
"""
Provides a thin canonicalization layer over adapters and scenario replay.

Rules enforced here:
- Only emit canonical tick dicts to the engine:
    {"symbol", "timestamp", "bid", "ask", "last", "volume", "source"}
- Drop invalid/missing timestamps (do not fabricate)
- Enforce per-symbol monotonic timestamps (drop non-monotonic)
"""

import gzip
import json
import logging
import math
from typing import Any, Dict, Generator, List, Optional

from adapters import mt5_adapter, polygon_adapter, alpaca_adapter
from data import canonical_schema as cs

# Provider priority for snapshot selection
PROVIDER_PRIORITY = ["mt5", "alpaca", "polygon"]

# Debug flag
DEBUG = bool(__import__('os').environ.get('DEBUG', ''))

logger = logging.getLogger(__name__)

# Per-symbol last accepted timestamp (seconds)
_last_ts_by_symbol: Dict[str, float] = {}

# Canonical tick key set enforced for every emitted tick
_CANONICAL_TICK_KEYS = {"symbol", "timestamp", "bid", "ask", "last", "volume", "source"}


CanonicalEvent = Dict[str, Any]


def _parse_ts_seconds(obj: Dict) -> Optional[float]:
    """Parse common timestamp fields without fabricating values.

    Accepts 'timestamp' (float seconds), 'time_msc' (ms int), 'time' (s int).
    Returns float seconds or None if not parseable.
    """
    ts = obj.get("timestamp")
    if ts is not None:
        try:
            return float(ts)
        except Exception:
            return None
    time_msc = obj.get("time_msc") or obj.get("timeMs")
    if time_msc is not None:
        try:
            return float(int(time_msc)) / 1000.0
        except Exception:
            return None
    time_s = obj.get("time") or obj.get("t")
    if time_s is not None:
        try:
            return float(time_s)
        except Exception:
            return None
    return None


def _canonicalize_tick(raw: Dict, symbol: str) -> Dict:
    """Return canonical tick dict or raise ValueError on invalid input.

    Minimal canonical keys: symbol,timestamp,bid,ask,last,volume,source
    """
    # If already canonical, validate and return
    if all(k in raw for k in ("symbol", "timestamp", "bid", "ask", "last", "volume", "source")):
        symbol_val = str(raw.get("symbol", symbol))
        ts = _parse_ts_seconds(raw)
        if ts is None:
            raise ValueError("Missing/invalid timestamp")
        bid = float(raw.get("bid", 0.0))
        ask = float(raw.get("ask", 0.0))
        last = float(raw.get("last", 0.0))
        volume = float(raw.get("volume", 0.0))
        if any(math.isnan(v) or math.isinf(v) for v in (bid, ask, last, volume, ts)):
            raise ValueError("NaN/inf in tick values")
        if bid <= 0 or ask <= 0 or ask <= bid:
            raise ValueError("Invalid prices/spread")
        return {
            "symbol": symbol_val,
            "timestamp": float(ts),
            "bid": bid,
            "ask": ask,
            "last": last,
            "volume": volume,
            "source": str(raw.get("source", "unknown")),
        }

    # Try to coerce common legacy shapes into canonical dict
    ts = _parse_ts_seconds(raw)
    if ts is None:
        raise ValueError("Missing/invalid timestamp")

    try:
        bid = float(raw.get("bid", raw.get("b", 0.0)))
        ask = float(raw.get("ask", raw.get("a", 0.0)))
        last = float(raw.get("last", raw.get("price", 0.0)))
        volume = float(raw.get("volume", raw.get("v", 0.0)))
    except Exception:
        raise ValueError("Invalid numeric tick fields")

    if any(math.isnan(v) or math.isinf(v) for v in (bid, ask, last, volume, ts)):
        raise ValueError("NaN/inf in tick values")
    if bid <= 0 or ask <= 0 or ask <= bid:
        raise ValueError("Invalid prices/spread")

    return {
        "symbol": symbol,
        "timestamp": float(ts),
        "bid": bid,
        "ask": ask,
        "last": last,
        "volume": volume,
        "source": str(raw.get("source", "unknown")),
    }


def _load_scenario(path: str) -> Dict:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class UnifiedFeed:
    def __init__(self, source: str, symbol: str, scenario_path: Optional[str] = None):
        self.source = source
        self.symbol = symbol
        self.scenario_path = scenario_path

    def load_historical(self, params: Optional[Dict] = None) -> List[CanonicalEvent]:
        params = params or {}
        events: List[CanonicalEvent] = []
        if self.source == "polygon":
            date = params.get("date")
            timespan = params.get("timespan", "minute")
            ticks = polygon_adapter.get_historical_bars(self.symbol, date, timespan)
            for tick in ticks:
                try:
                    canon = _canonicalize_tick(tick, self.symbol)
                except Exception as e:
                    logger.warning("UnifiedFeed: dropping historical polygon tick for %s: %s", self.symbol, e)
                    continue
                ts = float(canon["timestamp"])
                last_ts = _last_ts_by_symbol.get(self.symbol, 0.0)
                if ts <= last_ts:
                    logger.warning("UnifiedFeed: dropping historical tick for %s due to non-monotonic timestamp (last=%s, ts=%s)", self.symbol, last_ts, ts)
                    continue
                _last_ts_by_symbol[self.symbol] = ts
                events.append({"tick": canon, "book": {}, "market": self.symbol})
            return events

        if self.source == "scenario":
            if not self.scenario_path:
                raise ValueError("scenario_path required for scenario source")
            scenario = _load_scenario(self.scenario_path)
            books = scenario.get("order_books", [])
            ticks = scenario.get("ticks", [])
            if len(books) != len(ticks):
                raise RuntimeError("Order books must align 1:1 with ticks; synthetic padding is forbidden")
            last_ts = _last_ts_by_symbol.get(self.symbol, 0.0)
            for idx, raw_tick in enumerate(ticks):
                book = books[idx]
                if not book.get("bids") or not book.get("asks"):
                    logger.warning("UnifiedFeed: scenario order book missing bids/asks at index %s; skipping", idx)
                    continue
                try:
                    canon = _canonicalize_tick(raw_tick, scenario.get("instrument", self.symbol))
                except Exception as e:
                    logger.warning("UnifiedFeed: dropping scenario tick at index %s: %s", idx, e)
                    continue
                # Enforce exact canonical shape
                if set(canon.keys()) != _CANONICAL_TICK_KEYS:
                    logger.warning("UnifiedFeed: dropping scenario tick with non-canonical keys at index %s: %s", idx, set(canon.keys()))
                    continue
                ts = float(canon["timestamp"])
                if ts <= last_ts:
                    logger.warning("UnifiedFeed: dropping scenario tick for %s due to non-monotonic timestamp (last=%s, ts=%s)", self.symbol, last_ts, ts)
                    continue
                _last_ts_by_symbol[self.symbol] = ts
                events.append({"tick": canon, "book": book, "market": scenario.get("instrument", self.symbol)})
            return events

        raise ValueError(f"Unsupported source for historical load: {self.source}")

    def stream(self, params: Optional[Dict] = None) -> Generator[CanonicalEvent, None, None]:
        params = params or {}
        if self.source == "polygon":
            poll = float(params.get("poll_interval", 0.5))
            while True:
                snap = get_snapshot(self.symbol)
                if snap is None:
                    # nothing valid this poll
                    time.sleep(poll)
                    continue
                try:
                    # snapshot is canonical; use tick shape expected by engine
                    canon = {
                        "symbol": snap["symbol"],
                        "timestamp": snap["timestamp"],
                        "bid": snap.get("bid", 0.0) or 0.0,
                        "ask": snap.get("ask", 0.0) or 0.0,
                        "last": snap.get("price", 0.0) or 0.0,
                        "volume": snap.get("volume", 0.0) or 0.0,
                        "source": snap.get("provider", "unknown"),
                    }
                except Exception as e:
                    logger.warning("UnifiedFeed: malformed snapshot for %s: %s", self.symbol, e)
                    time.sleep(poll)
                    continue

                ts = float(canon["timestamp"])
                last_ts = _last_ts_by_symbol.get(self.symbol, 0.0)
                if ts <= last_ts:
                    logger.warning("UnifiedFeed: dropping polygon live tick for %s due to non-monotonic timestamp (last=%s, ts=%s)", self.symbol, last_ts, ts)
                    time.sleep(poll)
                    continue
                _last_ts_by_symbol[self.symbol] = ts
                yield {"tick": canon, "book": {}, "market": self.symbol}

        elif self.source == "mt5":
            poll = float(params.get("poll_interval", 0.5))
            while True:
                snap = get_snapshot(self.symbol)
                if snap is None:
                    time.sleep(poll)
                    continue
                try:
                    canon = {
                        "symbol": snap["symbol"],
                        "timestamp": snap["timestamp"],
                        "bid": snap.get("bid", 0.0) or 0.0,
                        "ask": snap.get("ask", 0.0) or 0.0,
                        "last": snap.get("price", 0.0) or 0.0,
                        "volume": snap.get("volume", 0.0) or 0.0,
                        "source": snap.get("provider", "unknown"),
                    }
                except Exception as e:
                    logger.warning("UnifiedFeed: malformed snapshot for %s: %s", self.symbol, e)
                    time.sleep(poll)
                    continue

                ts = float(canon["timestamp"])
                last_ts = _last_ts_by_symbol.get(self.symbol, 0.0)
                if ts <= last_ts:
                    logger.warning("UnifiedFeed: dropping mt5 live tick for %s due to non-monotonic timestamp (last=%s, ts=%s)", self.symbol, last_ts, ts)
                    time.sleep(poll)
                    continue
                _last_ts_by_symbol[self.symbol] = ts
                yield {"tick": canon, "book": {}, "market": self.symbol}

        elif self.source == "scenario":
            for event in self.load_historical(params):
                yield event
        else:
            raise ValueError(f"Unsupported source: {self.source}")


def get_snapshot(symbol: str) -> Optional[Dict]:
    """Fetch a canonical snapshot for `symbol` using provider priority rules.

    Returns the first valid, non-stale snapshot from providers in
    `PROVIDER_PRIORITY`, or None if no provider returns a valid snapshot.
    """
    reasons = []
    chosen = None
    chosen_provider = None
    for prov in PROVIDER_PRIORITY:
        try:
            if prov == 'mt5':
                snap = mt5_adapter.get_latest_snapshot(symbol)
            elif prov == 'alpaca':
                snap = alpaca_adapter.get_latest_snapshot(symbol)
            elif prov == 'polygon':
                snap = polygon_adapter.get_latest_snapshot(symbol)
            else:
                snap = None
        except Exception as ex:
            reasons.append(f"{prov}: exception {ex}")
            snap = None

        if snap is None:
            reasons.append(f"{prov}: no data")
            continue

        # Validate snapshot shape
        snap = cs.canonicalize_missing_fields(snap)
        valid = cs.validate_snapshot(snap)
        if not valid:
            reasons.append(f"{prov}: validation failed")
            continue

        # Check staleness and synthetic
        q = snap.get('quality', {})
        if q.get('stale'):
            reasons.append(f"{prov}: stale")
            continue
        if q.get('synthetic'):
            reasons.append(f"{prov}: synthetic")
            continue

        chosen = snap
        chosen_provider = prov
        break

    if chosen is not None:
        logger.info('UnifiedFeed: chosen provider=%s for %s ts=%s stale=%s synthetic=%s', chosen_provider, symbol, chosen.get('timestamp'), chosen.get('quality',{}).get('stale'), chosen.get('quality',{}).get('synthetic'))
        if DEBUG:
            cs.assert_snapshot(chosen)
        return chosen

    logger.debug('UnifiedFeed: no valid snapshot for %s; reasons: %s', symbol, '; '.join(reasons))
    return None
