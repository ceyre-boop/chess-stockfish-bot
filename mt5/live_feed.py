#!/usr/bin/env python3
"""
MT5 Live Feed (Engine-facing) - Trading Stockfish

Engine-facing layer only. This module MUST NOT return dataclasses,
SDK objects, or mock/demo data. All outputs are primitive/canonical dicts.

Exports:
- MT5LiveFeed: methods get_tick, get_symbol_info, get_candles, get_multitf_candles

Behavioral guarantees:
- Only emit canonical dicts: {symbol,timestamp,bid,ask,last,volume,source}
- Drop invalid or missing timestamps (no fabrication)
- Enforce per-symbol monotonic timestamps (drop non-monotonic)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except Exception:
    MT5_AVAILABLE = False

logger = logging.getLogger(__name__)

# Timeframe mapping (minutes)
TIMEFRAMES = {"M1": 1, "M5": 5, "M15": 15, "H1": 60}

MT5_TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1 if MT5_AVAILABLE else 1,
    "M5": mt5.TIMEFRAME_M5 if MT5_AVAILABLE else 5,
    "M15": mt5.TIMEFRAME_M15 if MT5_AVAILABLE else 15,
    "H1": mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 60,
}


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class LiveFeedError(Exception):
    pass


class ConnectionError(LiveFeedError):
    pass


class DataValidationError(LiveFeedError):
    pass


class MT5LiveFeed:
    """Engine-facing MT5 live feed. Returns only canonical dicts."""

    def __init__(
        self,
        account: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        max_retries: int = 5,
        retry_delay: float = 1.0,
        use_demo: bool = False,
    ):
        self.account = account
        self.password = password
        self.server = server
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.use_demo = use_demo

        self.status = ConnectionStatus.DISCONNECTED
        self.last_error: Optional[str] = None
        self.last_connection_time: Optional[float] = None
        self.connection_attempts = 0

        # symbol -> primitive symbol info dict cache
        self._symbol_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Dict[str, float] = {}
        self._cache_ttl = 60

        # per-symbol last-seen values to enforce monotonicity and detect duplicates
        # each entry is a dict: {'ts': float, 'bid': float, 'ask': float, 'last': float, 'volume': float}
        self._last_tick_ts_by_symbol: Dict[str, Dict[str, Any]] = {}

        logger.info("MT5LiveFeed (engine) initialized")

        if not self.use_demo:
            self.connect()

    def connect(self) -> bool:
        if not MT5_AVAILABLE:
            logger.warning("MT5 not available - engine feed will be disabled")
            self.status = ConnectionStatus.ERROR
            return False

        if self.status == ConnectionStatus.CONNECTED:
            return True

        self.status = ConnectionStatus.CONNECTING
        self.connection_attempts = 0
        while self.connection_attempts < self.max_retries:
            try:
                self.connection_attempts += 1
                if mt5.initialize():
                    self.status = ConnectionStatus.CONNECTED
                    self.last_connection_time = time.time()
                    self.last_error = None
                    logger.info("MT5 connected (engine)")
                    return True
                else:
                    err = mt5.last_error()
                    self.last_error = str(err)
                    logger.warning("MT5 initialize failed: %s", err)
                    time.sleep(min(self.retry_delay * (2**self.connection_attempts), 30))
            except Exception as e:
                self.last_error = str(e)
                logger.error("MT5 connect exception: %s", e)
                time.sleep(self.retry_delay)

        self.status = ConnectionStatus.ERROR
        return False

    def disconnect(self) -> None:
        if MT5_AVAILABLE:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self.status = ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED

    def _parse_tick_ts(self, tick_obj) -> Optional[float]:
        """Parse common mt5 tick timestamp fields into float seconds or None."""
        try:
            t_msc = getattr(tick_obj, "time_msc", None)
            # Always prefer time_msc for ms precision. Fallback to 'time' only if time_msc missing.
            if t_msc is not None and int(t_msc) > 0:
                return float(int(t_msc)) / 1000.0
            # Fallback: try 'time' but do not truncate (preserve float if present)
            t_s = getattr(tick_obj, "time", None)
            if t_s is not None:
                return float(t_s)
        except Exception:
            return None
        return None

    def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return canonical tick dict or None. Never returns mocks or dataclasses."""
        if self.use_demo:
            logger.warning("Engine-facing get_tick() will not return demo/mock ticks")
            return None

        if not self.is_connected():
            logger.warning("Not connected, cannot fetch tick for %s", symbol)
            return None

        if not MT5_AVAILABLE:
            return None

        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.debug("No tick data for %s", symbol)
                return None

            # Capture raw fields for tracing
            try:
                raw_time = getattr(tick, "time", None)
                raw_time_msc = getattr(tick, "time_msc", None)
                raw_last = getattr(tick, "last", None)
                raw_bid = getattr(tick, "bid", None)
                raw_ask = getattr(tick, "ask", None)
            except Exception:
                raw_time = raw_time_msc = raw_last = raw_bid = raw_ask = None

            bid_vol = getattr(tick, "bid_volume", 0) or 0
            ask_vol = getattr(tick, "ask_volume", 0) or 0

            ts = self._parse_tick_ts(tick)
            if ts is None:
                logger.warning("MT5 tick missing timestamp; dropping event for %s", symbol)
                return None

            # compute volume and canonical dict early so we can update last-seen consistently
            try:
                volume = float(getattr(tick, "volume", float(int(bid_vol) + int(ask_vol))))
            except Exception:
                volume = float(int(bid_vol) + int(ask_vol))

            canonical = {
                "symbol": symbol,
                "timestamp": float(ts),
                "bid": float(getattr(tick, "bid", 0.0)),
                "ask": float(getattr(tick, "ask", 0.0)),
                "last": float(getattr(tick, "last", 0.0)),
                "volume": float(volume),
                "source": "mt5",
            }

            prev = self._last_tick_ts_by_symbol.get(symbol)
            if prev is not None and isinstance(prev, dict):
                try:
                    prev_ts = float(prev.get("ts"))
                except Exception:
                    prev_ts = None
                prev_bid = prev.get("bid")
                prev_ask = prev.get("ask")
                prev_last = prev.get("last")
                prev_vol = prev.get("volume")
            else:
                prev_ts = prev_bid = prev_ask = prev_last = prev_vol = None

            if prev_ts is not None and ts < prev_ts:
                try:
                    delta = float(ts) - float(prev_ts)
                except Exception:
                    delta = None
                logger.error(
                    "MT5 timestamp tracing: symbol=%s raw.time=%s raw.time_msc=%s raw.last=%s raw.bid=%s raw.ask=%s parsed_ts=%s prev_ts=%s delta=%s",
                    symbol,
                    raw_time,
                    raw_time_msc,
                    raw_last,
                    raw_bid,
                    raw_ask,
                    ts,
                    prev_ts,
                    delta,
                )
                logger.warning("Non-monotonic tick ts for %s: %s < %s; dropping", symbol, ts, prev_ts)
                return None

            # Equal timestamps: accept only if market content changed
            if prev_ts is not None and ts == prev_ts:
                try:
                    vol = float(canonical.get("volume", 0.0))
                except Exception:
                    vol = None
                try:
                    if (
                        float(canonical.get("bid", 0.0)) == float(prev_bid or 0.0)
                        and float(canonical.get("ask", 0.0)) == float(prev_ask or 0.0)
                        and float(canonical.get("last", 0.0)) == float(prev_last or 0.0)
                        and (vol is None or float(prev_vol or 0.0) == vol)
                    ):
                        logging.getLogger('trading_engine').info(
                            "MT5 timestamp trace OK: symbol=%s raw.time=%s raw.time_msc=%s raw.last=%s raw.bid=%s raw.ask=%s parsed_ts=%s prev_ts=%s delta=%s",
                            symbol,
                            raw_time,
                            raw_time_msc,
                            raw_last,
                            raw_bid,
                            raw_ask,
                            ts,
                            prev_ts,
                            0.0,
                        )
                        logger.info("MT5 timestamp tracing: duplicate tick for %s at ts=%s; dropping", symbol, ts)
                        return None
                    # else accepted (content changed)
                except Exception:
                    pass

            # Log successful parsed tick and update last_ts
            try:
                delta_ok = float(ts) - float(prev_ts) if prev_ts is not None else None
            except Exception:
                delta_ok = None
            # Emit to central trading_engine logger so harness log captures it
            logging.getLogger('trading_engine').info(
                "MT5 timestamp trace OK: symbol=%s raw.time=%s raw.time_msc=%s raw.last=%s raw.bid=%s raw.ask=%s parsed_ts=%s prev_ts=%s delta=%s",
                symbol,
                raw_time,
                raw_time_msc,
                raw_last,
                raw_bid,
                raw_ask,
                ts,
                prev_ts,
                delta_ok,
            )
            # update last-seen fields only when tick accepted
            try:
                self._last_tick_ts_by_symbol[symbol] = {
                    'ts': float(ts),
                    'bid': float(canonical.get('bid', 0.0)),
                    'ask': float(canonical.get('ask', 0.0)),
                    'last': float(canonical.get('last', 0.0)),
                    'volume': float(canonical.get('volume', 0.0)),
                }
            except Exception:
                self._last_tick_ts_by_symbol[symbol] = {'ts': float(ts)}

            return canonical
        except Exception as e:
            logger.error("Error fetching tick for %s: %s", symbol, e)
            return None

    def get_symbol_info(self, symbol: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Return primitive symbol info dict or None (no dataclasses)."""
        if self.use_demo:
            logger.warning("Engine-facing get_symbol_info() will not return demo data")
            return None

        if use_cache and symbol in self._symbol_cache:
            cache_age = time.time() - self._cache_timestamp.get(symbol, 0)
            if cache_age < self._cache_ttl:
                return self._symbol_cache[symbol]

        if not self.is_connected():
            logger.warning("Not connected, cannot fetch symbol info for %s", symbol)
            return None

        if not MT5_AVAILABLE:
            return None

        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None

            tick = mt5.symbol_info_tick(symbol)
            bid = getattr(tick, "bid", getattr(info, "bid", 0.0))
            ask = getattr(tick, "ask", getattr(info, "ask", 0.0))

            sym = {
                "symbol": symbol,
                "digits": int(getattr(info, "digits", 5)),
                "point": float(getattr(info, "point", 0.00001)),
                "bid": float(bid),
                "ask": float(ask),
                "volume_min": float(getattr(info, "volume_min", 0.01)),
                "volume_max": float(getattr(info, "volume_max", 100.0)),
                "volume_step": float(getattr(info, "volume_step", 0.01)),
                "swap_long": float(getattr(info, "swap_long", 0.0)),
                "swap_short": float(getattr(info, "swap_short", 0.0)),
                "commission": float(getattr(info, "commission", 0.0)),
                "spread": float((float(ask) - float(bid)) * (10 ** int(getattr(info, "digits", 5)))),
            }

            self._symbol_cache[symbol] = sym
            self._cache_timestamp[symbol] = time.time()
            return sym
        except Exception as e:
            logger.error("Error fetching symbol info for %s: %s", symbol, e)
            return None

    def get_candles(self, symbol: str, timeframe: str, count: int = 100, offset: int = 0) -> Optional[List[Dict[str, Any]]]:
        """Return list of primitive candle dicts or None."""
        if self.use_demo:
            logger.warning("Engine-facing get_candles() will not return demo data")
            return None

        if not self.is_connected():
            logger.warning("Not connected, cannot fetch candles for %s %s", symbol, timeframe)
            return None

        if not MT5_AVAILABLE or timeframe not in MT5_TIMEFRAMES:
            logger.error("Invalid timeframe or MT5 unavailable: %s", timeframe)
            return None

        try:
            mt5_tf = MT5_TIMEFRAMES[timeframe]
            raw = mt5.copy_rates_from_pos(symbol, mt5_tf, offset, count)
            if raw is None or len(raw) == 0:
                logger.warning("No candle data for %s %s", symbol, timeframe)
                return None

            candle_list: List[Dict[str, Any]] = []
            for candle in raw:
                # Prefer ms timestamp if available, else fall back to seconds 'time'
                if candle.get("time_msc"):
                    try:
                        ts = float(int(candle.get("time_msc"))) / 1000.0
                    except Exception:
                        ts = float(candle.get("time", 0))
                else:
                    ts = float(candle.get("time", 0))
                candle_list.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "open": float(candle.get("open", 0.0)),
                    "high": float(candle.get("high", 0.0)),
                    "low": float(candle.get("low", 0.0)),
                    "close": float(candle.get("close", 0.0)),
                    "volume": int(candle.get("tick_volume", 0)),
                    "timestamp": ts,
                    "source": "mt5",
                })

            return candle_list
        except Exception as e:
            logger.error("Error fetching candles for %s %s: %s", symbol, timeframe, e)
            return None

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        candles = self.get_candles(symbol, timeframe, count=1)
        if candles and len(candles) > 0:
            return candles[0]
        return None

    def get_multitf_candles(self, symbol: str, timeframes: Optional[List[str]] = None, count: int = 100) -> Optional[Dict[str, Optional[List[Dict[str, Any]]]]]:
        if timeframes is None:
            timeframes = ["M1", "M5", "M15", "H1"]
        results: Dict[str, Optional[List[Dict[str, Any]]]] = {}
        for tf in timeframes:
            results[tf] = self.get_candles(symbol, tf, count=count)
        return results

    def validate_tick(self, tick: Optional[Dict[str, Any]], max_age_sec: int = 60) -> (bool, str):
        if tick is None:
            return False, "Tick is None"
        try:
            ts = float(tick.get("timestamp", 0))
            bid = float(tick.get("bid", 0))
            ask = float(tick.get("ask", 0))
        except Exception:
            return False, "Malformed tick structure"

        age = time.time() - ts
        if age > max_age_sec:
            return False, f"Tick is stale: {age:.1f}s old"
        if bid <= 0 or ask <= 0 or bid >= ask:
            return False, "Invalid bid/ask"
        return True, "Tick valid"

    def validate_candles(self, candles: Optional[List[Dict[str, Any]]], min_count: int = 20, max_age_sec: int = 300) -> (bool, str):
        if candles is None:
            return False, "Candles is None"
        if len(candles) < min_count:
            return False, f"Insufficient candles: {len(candles)} < {min_count}"
        latest = candles[-1]
        age = time.time() - float(latest.get("timestamp", 0))
        if age > max_age_sec:
            return False, f"Candles stale: {age:.1f}s old"
        for c in candles[-5:]:
            high = float(c.get("high", 0))
            low = float(c.get("low", 0))
            if high < low:
                return False, "Invalid candle: high < low"
        return True, "Candles valid"

    def get_connection_status(self) -> Dict[str, Any]:
        uptime = None
        if self.last_connection_time:
            uptime = time.time() - self.last_connection_time
        return {
            "status": self.status.value,
            "is_connected": self.is_connected(),
            "connection_attempts": self.connection_attempts,
            "last_error": self.last_error,
            "uptime_seconds": uptime,
            "use_demo": self.use_demo,
        }


# global instance helpers
_live_feed: Optional[MT5LiveFeed] = None


def initialize_feed(use_demo: bool = False) -> MT5LiveFeed:
    global _live_feed
    _live_feed = MT5LiveFeed(use_demo=use_demo)
    return _live_feed


def get_feed() -> MT5LiveFeed:
    global _live_feed
    if _live_feed is None:
        _live_feed = initialize_feed()
    return _live_feed
