from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import os
import pytz
import logging
import time

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

log = logging.getLogger(__name__)

# Adapter-level per-symbol monotonic timestamp tracking
_last_ts_by_symbol = {}
# Adapter-level monotonic snapshot tracker
_last_snapshot_by_symbol = {}


@dataclass
class UnifiedBar:
    # Deprecated dataclass placeholder — adapter returns primitive dicts.
    # Keep for backward compatibility with tooling that inspects types,
    # but runtime consumers must use primitive canonical dicts.
    timestamp_utc: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    bid: float
    ask: float
    vwap: Optional[float]
    last_price: float

def init_mt5_from_env() -> None:
    """
    - Load MT5_* env vars
    - Initialize MT5 connection
    - Select PRIMARY or SECONDARY based on MT5_ACTIVE_ACCOUNT
    - Deterministic, no prints of credentials
    """
    if mt5 is None:
        raise ImportError("MetaTrader5 package is not installed.")
    login = os.getenv("MT5_LOGIN_PRIMARY")
    password = os.getenv("MT5_PASSWORD_PRIMARY")
    server = os.getenv("MT5_SERVER_PRIMARY")
    account = os.getenv("MT5_ACTIVE_ACCOUNT")
    if not all([login, password, server, account]):
        raise RuntimeError("Missing MT5 credentials in environment.")
    if not mt5.initialize(server=server, login=int(login), password=password):
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

def get_historical_bars_mt5(symbol: str, start: datetime, end: datetime, timeframe: str) -> List[Dict[str, Any]]:
    """
    - Map timeframe (e.g. 'M1', 'M5', 'H1') to MT5 timeframes
    - Fetch bars via MT5
    - Convert to UnifiedBar list
    - Ensure timestamp_utc is ISO in UTC
    - Fill bid/ask as None if not available
    - Compute vwap if possible, else None
    """
    if mt5 is None:
        raise ImportError("MetaTrader5 package is not installed.")
    from math import isnan
    tf_map = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "H1": mt5.TIMEFRAME_H1, "D1": mt5.TIMEFRAME_D1}
    mt5_tf = tf_map.get(timeframe.upper())
    if mt5_tf is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    utc_from = start.replace(tzinfo=pytz.UTC)
    utc_to = end.replace(tzinfo=pytz.UTC)

    # Ensure symbol is selected and visible before requesting history
    info = mt5.symbol_info(symbol)
    if info is None or not getattr(info, 'visible', False):
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
        if info is None or not getattr(info, 'visible', False):
            log.warning('MT5 adapter: symbol %s could not be selected or is not visible', symbol)
            return []

    log.info('MT5 adapter: requesting bars for %s', symbol)
    rates = mt5.copy_rates_range(symbol, mt5_tf, utc_from, utc_to)
    if not rates:
        log.info('MT5 adapter: no bars returned for %s', symbol)
        return []

    bars: List[Dict] = []
    for raw in rates:
        try:
            # Timestamp normalization: ALWAYS prefer time_msc (ms precision).
            # Fallback to 'timestamp' only if time_msc is missing; avoid using raw.time
            raw_time_msc = getattr(raw, 'time_msc', None)
            raw_timestamp = getattr(raw, 'timestamp', None)

            ts_sec: Optional[float] = None
            if raw_time_msc is not None and int(raw_time_msc) > 0:
                try:
                    ts_sec = float(raw_time_msc) / 1000.0
                except Exception:
                    ts_sec = None
            elif raw_timestamp is not None:
                try:
                    # raw_timestamp may be ms or s; detect magnitude
                    rtv = int(raw_timestamp)
                    if rtv > 1_000_000_000_000:  # clearly ms
                        ts_sec = float(rtv) / 1000.0
                    else:
                        ts_sec = float(raw_timestamp)
                except Exception:
                    ts_sec = None

            if ts_sec is None:
                log.warning('MT5 adapter: dropping bar for %s due to missing time_msc/timestamp fields', symbol)
                continue

            # Timestamp-source tracing (raw fields -> parsed ts, previous ts, delta)
            try:
                prev_ts = _last_ts_by_symbol.get(symbol)
                delta = None if prev_ts is None else float(ts_sec) - float(prev_ts)
            except Exception:
                prev_ts = None
                delta = None
            # Also emit to central trading_engine logger so harness log captures it
            logging.getLogger('trading_engine').info(
                'MT5 adapter timestamp trace: symbol=%s raw_time=%s raw_time_msc=%s raw_timestamp=%s parsed_ts=%s prev_ts=%s delta=%s',
                symbol, raw_time, raw_time_msc, raw_timestamp, ts_sec, prev_ts, delta,
            )

            # Reject obviously invalid timestamps
            if ts_sec <= 0 or ts_sec < 946684800:  # before 2000-01-01
                log.warning('MT5 adapter: dropping bar for %s due to invalid timestamp %s', symbol, ts_sec)
                continue

            # Adapter-level monotonicity per symbol — store full last-seen tuple
            prev = _last_ts_by_symbol.get(symbol)
            if prev is not None:
                try:
                    prev_ts = float(prev.get('ts'))
                except Exception:
                    prev_ts = None
                prev_bid = prev.get('bid')
                prev_ask = prev.get('ask')
                prev_last = prev.get('last')
                prev_vol = prev.get('volume')
            else:
                prev_ts = None
                prev_bid = prev_ask = prev_last = prev_vol = None

            # Strictly backwards in time -> drop
            if prev_ts is not None and ts_sec < prev_ts:
                log.warning('MT5 adapter: non-monotonic timestamp for %s (last=%s, candidate=%s), dropping tick', symbol, prev_ts, ts_sec)
                continue

            # Equal timestamps -> accept only if market content changed
            if prev_ts is not None and ts_sec == prev_ts:
                try:
                    # Compare numeric fields; treat None as unequal conservatively
                    if (
                        float(bid_) == float(prev_bid)
                        and float(ask_) == float(prev_ask)
                        and float(last_price) == float(prev_last)
                        and float(volume_) == float(prev_vol)
                    ):
                        log.info('MT5 adapter: duplicate tick detected for %s at ts=%s; dropping', symbol, ts_sec)
                        continue
                    # else: content changed -> accept
                except Exception:
                    # On any comparison error, be conservative and accept the tick
                    pass

            # Field normalization
            try:
                open_ = float(getattr(raw, 'open', raw[1] if len(raw) > 1 else 0.0))
            except Exception:
                open_ = 0.0
            try:
                high_ = float(getattr(raw, 'high', raw[2] if len(raw) > 2 else 0.0))
            except Exception:
                high_ = 0.0
            try:
                low_ = float(getattr(raw, 'low', raw[3] if len(raw) > 3 else 0.0))
            except Exception:
                low_ = 0.0
            try:
                close_ = float(getattr(raw, 'close', raw[4] if len(raw) > 4 else 0.0))
            except Exception:
                close_ = 0.0
            try:
                volume_ = float(getattr(raw, 'real_volume', getattr(raw, 'tick_volume', getattr(raw, 'volume', 0.0))))
            except Exception:
                volume_ = 0.0

            # bid/ask may not be present in historical bar; default to close for both if missing
            try:
                bid_ = getattr(raw, 'bid', None)
                ask_ = getattr(raw, 'ask', None)
            except Exception:
                bid_ = None
                ask_ = None
            try:
                bid_ = float(bid_) if bid_ is not None else 0.0
            except Exception:
                bid_ = 0.0
            try:
                ask_ = float(ask_) if ask_ is not None else 0.0
            except Exception:
                ask_ = 0.0

            # last_price: prefer explicit last/close, else mid if bid/ask positive
            last_price = 0.0
            try:
                last_candidate = getattr(raw, 'last', None)
                if last_candidate is not None:
                    last_price = float(last_candidate)
                elif bid_ > 0 and ask_ > 0:
                    last_price = (bid_ + ask_) / 2.0
                else:
                    last_price = float(close_)
            except Exception:
                last_price = float(close_)

            # vwap fallback
            try:
                vwap = float(getattr(raw, 'vwap', (high_ + low_ + close_) / 3))
            except Exception:
                vwap = (high_ + low_ + close_) / 3

            # sanity checks
            if any((x is None or (isinstance(x, float) and isnan(x))) for x in [open_, high_, low_, close_, volume_, bid_, ask_, last_price]):
                log.warning('MT5 adapter: dropping bar for %s due to NaN/None fields', symbol)
                continue

            # update monotonic tracker and append canonical dict (engine-facing)
            _last_ts_by_symbol[symbol] = {
                'ts': float(ts_sec),
                'bid': float(bid_),
                'ask': float(ask_),
                'last': float(last_price),
                'volume': float(volume_),
            }
            ts_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)

            canonical = {
                "symbol": symbol,
                "timestamp": float(ts_sec),
                "bid": float(bid_),
                "ask": float(ask_),
                "last": float(last_price),
                "volume": float(volume_),
                "source": "mt5",
            }

            # Defensive canonicalization: always append a primitive dict.
            bars.append(canonical)
        except Exception:
            # Never let a single bad bar crash the adapter; log and continue
            log.exception('MT5 adapter: error processing raw bar for %s', symbol)
            continue

    # Final safety pass: ensure every returned item is a primitive canonical dict
    required_keys = {"symbol", "timestamp", "bid", "ask", "last", "volume", "source"}
    final: List[Dict[str, Any]] = []
    for b in bars:
        if isinstance(b, dict) and required_keys.issubset(set(b.keys())):
            final.append({
                k: (float(v) if k in ("timestamp", "bid", "ask", "last", "volume") else v)
                for k, v in b.items()
            })
            continue

        # Attempt to convert objects with attributes into a canonical dict
        try:
            sym = getattr(b, "symbol", symbol)
            # prefer time_msc -> timestamp -> time (as last resort)
            ts_v = getattr(b, "time_msc", None)
            if ts_v is not None:
                ts_f = float(int(ts_v)) / 1000.0
            else:
                ts_v = getattr(b, "timestamp", None)
                if ts_v is not None:
                    rtv = int(ts_v)
                    if rtv > 1_000_000_000_000:
                        ts_f = float(rtv) / 1000.0
                    else:
                        ts_f = float(ts_v)
                else:
                    # last resort: try 'time' attr
                    ts_v = getattr(b, "time", None)
                    if ts_v is None:
                        raise ValueError("missing timestamp")
                    ts_f = float(ts_v)
            bid_v = float(getattr(b, "bid", 0.0))
            ask_v = float(getattr(b, "ask", 0.0))
            last_v = float(getattr(b, "last", getattr(b, "close", 0.0)))
            vol_v = float(getattr(b, "volume", getattr(b, "tick_volume", 0.0)))
            final.append({
                "symbol": str(sym),
                "timestamp": float(ts_f),
                "bid": bid_v,
                "ask": ask_v,
                "last": last_v,
                "volume": vol_v,
                "source": "mt5",
            })
        except Exception:
            log.exception('MT5 adapter: dropping non-canonical bar for %s', symbol)
            continue

    log.info('MT5 adapter: bars returned for %s: %d', symbol, len(final))
    return final


def get_latest_tick(symbol: str, use_demo: bool = False) -> Optional[Dict[str, Any]]:
    """
    Return a canonical tick dict for the given symbol.
    Adapter encapsulates all MetaTrader5 SDK access so callers receive
    only primitive canonical dictionaries.
    """
    if use_demo:
        raise RuntimeError("Demo tick retrieval via adapter is disabled")
    if mt5 is None:
        raise ImportError("MetaTrader5 package is not installed")

    try:
        raw = mt5.symbol_info_tick(symbol)
    except Exception as e:
        log.exception('MT5 adapter: symbol_info_tick failed for %s: %s', symbol, e)
        return None

    if raw is None:
        log.warning('MT5 adapter: no tick returned for %s', symbol)
        return None

    # Timestamp normalization: prefer time_msc
    try:
        t_msc = getattr(raw, 'time_msc', None)
        t_s = None
        if t_msc is not None and int(t_msc) > 0:
            t_s = float(int(t_msc)) / 1000.0
        else:
            t_v = getattr(raw, 'time', None)
            if t_v is not None:
                t_s = float(t_v)
    except Exception:
        t_s = None

    if t_s is None:
        log.warning('MT5 adapter: tick for %s missing timestamp', symbol)
        return None

    try:
        bid = float(getattr(raw, 'bid', 0.0))
    except Exception:
        bid = 0.0
    try:
        ask = float(getattr(raw, 'ask', 0.0))
    except Exception:
        ask = 0.0
    try:
        last = float(getattr(raw, 'last', 0.0))
    except Exception:
        last = 0.0
    try:
        vol = float(getattr(raw, 'volume', 0.0))
    except Exception:
        vol = 0.0

    try:
        spread = (ask - bid) * 10000.0
    except Exception:
        spread = float('inf')

    canonical = {
        'symbol': symbol,
        'timestamp': float(t_s),
        'bid': bid,
        'ask': ask,
        'last': last,
        'volume': vol,
        'source': 'mt5',
        'spread': spread,
    }

    # update adapter-level monotonic tracker
    try:
        _last_ts_by_symbol[symbol] = {
            'ts': float(t_s),
            'bid': bid,
            'ask': ask,
            'last': last,
            'volume': vol,
        }
    except Exception:
        pass

    return canonical


def get_latest_snapshot(symbol: str, use_demo: bool = False) -> Optional[Dict[str, Any]]:
    """Fetch latest MT5 tick and return a canonical snapshot dict or None.

    Enforces timestamp normalization, monotonicity, and schema compliance.
    """
    from data import canonical_schema as cs
    DEBUG = bool(os.getenv('DEBUG', '') )

    if use_demo:
        raise RuntimeError("Demo tick retrieval via adapter is disabled")
    if mt5 is None:
        raise ImportError("MetaTrader5 package is not installed")

    try:
        raw = mt5.symbol_info_tick(symbol)
    except Exception as e:
        log.exception('MT5 adapter: symbol_info_tick failed for %s: %s', symbol, e)
        return None

    if raw is None:
        return None

    # timestamp normalization: prefer time_msc
    t_s = None
    try:
        t_msc = getattr(raw, 'time_msc', None)
        if t_msc is not None and int(t_msc) > 0:
            t_s = float(int(t_msc)) / 1000.0
        else:
            t_v = getattr(raw, 'time', None)
            if t_v is not None:
                t_s = float(t_v)
    except Exception:
        t_s = None

    if t_s is None:
        log.warning('MT5 adapter: tick for %s missing timestamp', symbol)
        return None

    # extract numeric fields
    def _f(attr, default=None):
        try:
            v = getattr(raw, attr, default)
            return None if v is None else float(v)
        except Exception:
            return default

    bid = _f('bid', None)
    ask = _f('ask', None)
    last = _f('last', None)
    vol = _f('volume', None)

    # price selection
    price = None
    if last is not None and last > 0:
        price = last
    elif bid is not None and ask is not None:
        price = (bid + ask) / 2.0
    else:
        price = None

    spread = None
    if bid is not None and ask is not None:
        try:
            spread = float(ask - bid)
        except Exception:
            spread = None

    # quality flags
    partial = any(x is None for x in (bid, ask, last))
    snapshot = {
        'symbol': symbol,
        'provider': 'mt5',
        'timestamp': float(t_s),
        'price': price,
        'bid': bid,
        'ask': ask,
        'spread': spread,
        'volume': vol,
        'bar': {'open': None, 'high': None, 'low': None, 'close': None, 'volume': None, 'tf': None},
        'quality': {'stale': False, 'synthetic': False, 'partial': partial},
    }

    # Monotonicity enforcement
    prev = _last_snapshot_by_symbol.get(symbol)
    if prev is not None:
        prev_ts = prev.get('timestamp')
        if prev_ts is not None:
            if snapshot['timestamp'] < prev_ts:
                log.info('MT5 adapter: dropping older snapshot for %s (%s < %s)', symbol, snapshot['timestamp'], prev_ts)
                return None
            if snapshot['timestamp'] == prev_ts:
                # drop if identical content
                def _content(s):
                    return (s.get('price'), s.get('bid'), s.get('ask'), s.get('volume'))
                if _content(snapshot) == _content(prev):
                    return None

    # Fill missing optional fields and validate
    snapshot = cs.canonicalize_missing_fields(snapshot)
    ok = cs.validate_snapshot(snapshot)
    if not ok:
        log.warning('MT5 adapter: produced snapshot failed validation for %s', symbol)
        if DEBUG:
            cs.assert_snapshot(snapshot)
        return None

    # accept and update tracker
    _last_snapshot_by_symbol[symbol] = snapshot
    return snapshot
