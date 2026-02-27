#!/usr/bin/env python3
"""
State Builder Module - Trading Stockfish

Builds structured market state dictionaries from live MetaTrader5 data.
Fetches ticks, spreads, candles across multiple timeframes, calculates indicators,
and assembles a complete state snapshot for decision-making.

State Schema:
{
    'timestamp': float,           # Unix timestamp
    'symbol': str,                # e.g., 'EURUSD'
    'tick': {
        'bid': float,
        'ask': float,
        'spread': float,          # ask - bid in pips
        'last_tick_time': int,    # seconds since epoch
    },
    'candles': {
        'M1': {...},              # 1-minute candles with indicators
        'M5': {...},
        'M15': {...},
        'H1': {...},
    },
    'indicators': {
        'rsi_14': float,          # Relative Strength Index
        'sma_50': float,          # Simple Moving Average
        'sma_200': float,
        'atr_14': float,          # Average True Range
        'volatility': float,      # Current volatility metric
    },
    'trend': {
        'regime': str,            # 'uptrend', 'downtrend', 'sideways'
        'strength': float,        # 0-1, confidence in trend
    },
    'sentiment': {
        'score': float,           # -1 to 1, -1 = bearish, 1 = bullish
        'confidence': float,      # 0-1, confidence in sentiment
        'source': str,            # 'news', 'manual', 'placeholder'
    },
    'health': {
        'is_stale': bool,         # True if data is older than threshold
        'last_update': float,     # Unix timestamp of last successful update
        'errors': list,           # List of warnings/non-fatal errors
    }
}
"""


import logging
import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from engine.amd_features import AMDFeatures
from engine.liquidity_metrics import (
    compute_liquidity_score,
    compute_spread,
    detect_liquidity_stress,
)

# Microstructure imports
from engine.order_book_model import OrderBookModel
from engine.order_flow_features import OrderFlowFeatures
from engine.trend_structure import compute_trend_structure
from engine.volatility_features import VolatilityFeatures
from engine.volatility_utils import compute_atr
from session_regime import compute_session_regime

# MetaTrader5/sdk must not be referenced directly by state_builder.
# Adapters and `data.unified_feed` are the only allowed provider interfaces.
MT5_AVAILABLE = False


def _session_modifiers(session_label: str) -> Dict[str, float]:
    """Return deterministic session multipliers used by downstream policy/evaluator."""

    base = {
        "volatility_scale": 1.0,
        "liquidity_scale": 1.0,
        "trade_freq_scale": 1.0,
        "risk_scale": 1.0,
    }
    label = (session_label or "").upper()
    if label == "GLOBEX":
        base.update(
            {"volatility_scale": 0.8, "liquidity_scale": 0.7, "risk_scale": 0.9}
        )
    elif label == "PREMARKET":
        base.update({"volatility_scale": 0.9, "liquidity_scale": 0.8})
    elif label == "RTH_OPEN":
        base.update(
            {
                "volatility_scale": 1.2,
                "liquidity_scale": 1.2,
                "trade_freq_scale": 1.3,
                "risk_scale": 1.1,
            }
        )
    elif label == "MIDDAY":
        base.update({"volatility_scale": 0.9, "liquidity_scale": 1.0})
    elif label == "POWER_HOUR":
        base.update(
            {"volatility_scale": 1.3, "liquidity_scale": 0.9, "risk_scale": 1.2}
        )
    elif label == "CLOSE":
        base.update({"volatility_scale": 1.1, "liquidity_scale": 0.8})
    return base


# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
# Per-symbol last timestamp tracker to enforce monotonicity without fabrication
_last_tick_timestamp_by_symbol: Dict[str, Dict[str, Any]] = {}

# Configuration constants
STALE_TICK_THRESHOLD = 60  # seconds - warn if tick older than this
STALE_CANDLE_THRESHOLD = 300  # seconds - warn if candle older than this
MT5_INIT_TIMEOUT = 5  # seconds
MT5_CONNECTION_RETRIES = 3
MT5_RETRY_DELAY = 1  # seconds

# Timeframe mapping
TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "H1": 60,
}

MT5_TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "H1": 60,
}


class StateBuilderError(Exception):
    """Base exception for state builder errors"""

    pass


class MT5ConnectionError(StateBuilderError):
    """Raised when MT5 connection fails"""

    pass


def initialize_mt5(timeout: int = MT5_INIT_TIMEOUT) -> bool:
    """
    Initialize MetaTrader5 connection with retry logic.

    Args:
        timeout: Initialization timeout in seconds

    Returns:
        True if initialization successful, False otherwise
    """
    if not MT5_AVAILABLE:
        logger.warning("MT5 not available - running in mock mode")
        return False

    for attempt in range(MT5_CONNECTION_RETRIES):
        try:
            logger.debug(
                f"MT5 initialization attempt {attempt + 1}/{MT5_CONNECTION_RETRIES}"
            )
            if mt5.initialize():
                logger.info("MetaTrader5 initialized successfully")
                return True
            else:
                error_code, error_msg = mt5.last_error()
                logger.warning(
                    f"MT5 init failed (attempt {attempt + 1}): {error_code} - {error_msg}"
                )
                if attempt < MT5_CONNECTION_RETRIES - 1:
                    time.sleep(MT5_RETRY_DELAY)
        except Exception as e:
            logger.error(f"MT5 initialization exception (attempt {attempt + 1}): {e}")
            if attempt < MT5_CONNECTION_RETRIES - 1:
                time.sleep(MT5_RETRY_DELAY)

    logger.error("MT5 initialization failed after all retry attempts")
    return False


def shutdown_mt5():
    """Safely shutdown MetaTrader5 connection"""
    if MT5_AVAILABLE:
        try:
            mt5.shutdown()
            logger.info("MetaTrader5 shutdown complete")
        except Exception as e:
            logger.error(f"MT5 shutdown error: {e}")


def fetch_tick_data(symbol: str, use_demo: bool = False) -> Optional[Dict]:
    """
    Fetch a canonical snapshot for the symbol.
    This is the ONLY sensory entry point for state_builder.

    Returns:
        Canonical snapshot dict or None when no new data is available.
    """
    from data.unified_feed import get_snapshot

    snapshot = get_snapshot(symbol)
    return snapshot  # may be None (NO_DATA)


def fetch_candles(
    symbol: str, timeframe: str, count: int = 100, use_demo: bool = False
) -> Optional[Dict]:
    """
    Fetch candle data for a specific timeframe.

    Args:
        symbol: Trading symbol (e.g., 'EURUSD')
        timeframe: Timeframe code ('M1', 'M5', 'M15', 'H1')
        count: Number of candles to fetch
        use_demo: If True, use mock data instead of live MT5

    Returns:
        Dict with OHLC data and indicators. None if failed.
    """
    raise RuntimeError("Direct MT5 candle access from state_builder is forbidden; use adapters or data.unified_feed for canonical candles.")


def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return np.nan

    deltas = np.diff(prices)
    seed = deltas[: period + 1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period

    rs = up / down if down != 0 else 0
    rsi = 100.0 - (100.0 / (1.0 + rs))

    for d in deltas[period + 1 :]:
        up = (up * (period - 1) + (d if d > 0 else 0)) / period
        down = (down * (period - 1) + (-d if d < 0 else 0)) / period
        rs = up / down if down != 0 else 0
        rsi = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def _calculate_sma(prices: np.ndarray, period: int = 50) -> float:
    """Calculate Simple Moving Average (returns latest value)"""
    if len(prices) < period:
        return np.nan
    return np.mean(prices[-period:])


def _calculate_atr(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
) -> float:
    """Calculate Average True Range"""
    if len(high) < period:
        return np.nan

    tr = np.maximum(
        high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])
    )
    atr = np.mean(tr[-period:])
    return atr


def detect_trend_regime(
    rsi: float, sma_50: float, sma_200: float, close: float
) -> Dict:
    """
    Detect trend regime based on indicators.

    Args:
        rsi: RSI value (0-100)
        sma_50: 50-period moving average
        sma_200: 200-period moving average
        close: Latest close price

    Returns:
        Dict with regime type and strength
    """
    regime = "sideways"
    strength = 0.0

    if sma_50 is None or sma_200 is None or close is None:
        logger.warning("Cannot determine trend - missing data")
        return {"regime": regime, "strength": strength}

    # Trend detection logic
    if sma_50 > sma_200:
        regime = "uptrend"
        # Strength based on distance and RSI
        distance = (sma_50 - sma_200) / sma_200
        strength = min(0.9, 0.5 + distance * 100)  # Cap at 0.9
        if rsi > 70:
            strength = min(strength, 0.7)  # Overbought reduces confidence
    elif sma_50 < sma_200:
        regime = "downtrend"
        distance = (sma_200 - sma_50) / sma_200
        strength = min(0.9, 0.5 + distance * 100)
        if rsi < 30:
            strength = min(strength, 0.7)  # Oversold reduces confidence
    else:
        regime = "sideways"
        strength = 0.5

    return {"regime": regime, "strength": strength}


def interpret_news_sentiment(headlines: Optional[List[str]] = None) -> Dict:
    """
    Placeholder for news sentiment interpretation.

    In production, this would integrate with an LLM (OpenAI, Claude, etc.)
    to analyze news headlines and market sentiment.

    Args:
        headlines: List of news headlines (optional)

    Returns:
        Dict with sentiment score (-1 to 1), confidence, and source
    """
    # Placeholder implementation - returns neutral sentiment
    logger.debug("News sentiment interpretation (placeholder)")

    sentiment_data = {
        "score": 0.0,  # Range: -1 (bearish) to 1 (bullish), 0 (neutral)
        "confidence": 0.0,  # Range: 0 to 1
        "source": "placeholder",
        "headlines_processed": 0,
    }

    if headlines and len(headlines) > 0:
        # TODO: Integrate with LLM API (OpenAI, Claude, Gemini)
        # For now, just count positive/negative keywords
        sentiment_data["headlines_processed"] = len(headlines)
        logger.debug(f"Processed {len(headlines)} headlines (mock)")

    return sentiment_data


def calculate_volatility(atr: float, close: float) -> float:
    """
    Calculate volatility metric (ATR-based).

    Args:
        atr: Average True Range value
        close: Current close price

    Returns:
        Volatility as percentage
    """
    if atr is None or close is None or close == 0:
        return 0.0

    volatility = (atr / close) * 100  # Convert to percentage
    return volatility


def check_data_health(tick_time: int, candle_time: int) -> Dict:
    """
    Check health of market data (staleness, gaps, etc.).

    Args:
        tick_time: Timestamp of last tick
        candle_time: Timestamp of last candle

    Returns:
        Dict with health status and warnings
    """
    current_time = time.time()
    tick_age = current_time - tick_time
    candle_age = current_time - candle_time

    health = {
        "is_stale": False,
        "last_update": current_time,
        "errors": [],
    }

    if tick_age > STALE_TICK_THRESHOLD:
        health["is_stale"] = True
        health["errors"].append(f"Stale tick: {tick_age:.1f}s old")
        logger.warning(f"Stale tick detected: {tick_age:.1f} seconds old")

    if candle_age > STALE_CANDLE_THRESHOLD:
        health["is_stale"] = True
        health["errors"].append(f"Stale candle: {candle_age:.1f}s old")
        logger.warning(f"Stale candle detected: {candle_age:.1f} seconds old")

    return health


def build_state(
    symbol: str = "EURUSD",
    snapshot: Optional[Dict] = None,
    use_demo: bool = False,
    order_book_events: Optional[list] = None,
) -> Optional[Dict]:
    """
    Build complete market state dictionary.

    Fetches live data from MetaTrader5, calculates indicators, detects trends,
    and assembles a structured state for decision-making.

    Args:
        symbol: Trading symbol (default: 'EURUSD')
        use_demo: If True, use mock data instead of live MT5 (for testing)

    Returns:
        Complete state dictionary. None if critical data fetch failed.
    """

    logger.info(f"Building state for {symbol} (demo={use_demo})")

    # Expect a canonical snapshot dict supplied by the unified feed.
    # If no snapshot is provided, skip state update (benign no-op).
    # Backwards compatibility: callers may pass a snapshot dict as the first
    # positional argument (older code). Detect and adjust accordingly.
    if isinstance(symbol, dict) and snapshot is None:
        snapshot = symbol
        symbol = snapshot.get("symbol", "UNKNOWN")

    logger.info(f"Building state for {symbol} (demo={use_demo})")

    if snapshot is None:
        logger.debug(f"No canonical snapshot provided for {symbol}; skipping state build")
        return None

    if not isinstance(snapshot, dict):
        logger.error("Non-canonical snapshot provided to build_state; skipping")
        return None

    # Validate against canonical schema if available
    try:
        from data.canonical_schema import validate_snapshot, assert_snapshot

        if not validate_snapshot(snapshot):
            logger.warning(f"Snapshot failed canonical validation for {symbol}; skipping")
            return None
        # In debug scenarios assert the snapshot shape
        DEBUG = False
        if DEBUG:
            assert_snapshot(snapshot)
    except Exception:
        # If schema module missing or validation errors, continue conservatively
        logger.debug("canonical_schema unavailable; proceeding with basic mapping")

    # Map canonical snapshot fields into the legacy tick_data shape expected
    # by downstream functions. This is a thin adapter layer only.
    tick_data = {
        "symbol": snapshot.get("symbol"),
        "timestamp": snapshot.get("timestamp"),
        "bid": snapshot.get("bid") if snapshot.get("bid") is not None else snapshot.get("price"),
        "ask": snapshot.get("ask") if snapshot.get("ask") is not None else snapshot.get("price"),
        "last": snapshot.get("price"),
        "volume": snapshot.get("volume"),
        "source": snapshot.get("provider") or snapshot.get("source"),
    }

    # Validate the mapped tick_data for monotonicity and sanity
    _ensure_valid_tick_data(tick_data)

    # Fetch candles for all timeframes
    candles = {}
    candle_times = []
    for timeframe in TIMEFRAMES.keys():
        # Request more history for higher timeframes so long-period indicators
        # (e.g. SMA-200 on H1) can be computed. Keep default 100 for smaller
        # TFs but request 250 for H1.
        count = 250 if timeframe == "H1" else 100
        candle = fetch_candles(symbol, timeframe, count=count, use_demo=use_demo)
        if candle is not None:
            candles[timeframe] = candle
            # latest timestamp normalized to 'timestamp' by fetch_candles
            candle_times.append(candle["latest"].get("timestamp", candle["latest"].get("time")))
        else:
            logger.warning(f"Failed to fetch {timeframe} candles for {symbol}")
            candles[timeframe] = None

    # Extract indicators from H1 (primary decision timeframe)
    indicators = {
        "rsi_14": None,
        "sma_50": None,
        "sma_200": None,
        "atr_14": None,
        "volatility": None,
    }

    if candles["H1"] and candles["H1"]["indicators"]:
        indicators = candles["H1"]["indicators"].copy()
        # Calculate volatility
        atr_value = compute_atr(indicators.get("atr_14"), window=14)
        indicators["atr_14"] = atr_value
        indicators["volatility"] = calculate_volatility(atr_value, tick_data["bid"])
    _ensure_valid_volatility(indicators)

    # Detect trend
    trend = detect_trend_regime(
        indicators["rsi_14"],
        indicators["sma_50"],
        indicators["sma_200"],
        tick_data["bid"],
    )

    # Get sentiment (placeholder)
    sentiment = interpret_news_sentiment()

    # Check data health
    latest_candle_time = max(candle_times) if candle_times else int(time.time())
    health = check_data_health(int(tick_data.get("timestamp", int(time.time()))), int(latest_candle_time))

    # Order book integration (Phase v4.0-A only)
    vol_features = VolatilityFeatures(window=50, use_microstructure_realism=True)
    order_book = None
    order_flow_features = None
    amd_detector = AMDFeatures(window=50)
    mid_prices: List[float] = []
    volumes: List[float] = []
    if order_book_events:
        order_book = OrderBookModel(depth=5)
        order_flow_features = OrderFlowFeatures(lookback=10)
        for event in order_book_events:
            order_book.update_from_event(event)
            # For order flow, use the current book snapshot and event
            order_flow_features.update(order_book.get_depth_snapshot(), event)
            best_bid, best_ask = order_book.get_best_bid_ask()
            if best_bid is not None and best_ask is not None:
                mid_prices.append((best_bid + best_ask) / 2)
                vol_features.compute(mid_prices[-1])
            if event.get("type") == "trade":
                volumes.append(float(event.get("size", 1.0)))
    if not mid_prices and tick_data:
        mid_prices.append((tick_data.get("bid", 0.0) + tick_data.get("ask", 0.0)) / 2)
        vol_features.compute(mid_prices[-1], candle_data=indicators)

    # Session regime + deterministic modifiers for downstream policy/evaluator
    session_label = "UNKNOWN"
    try:
        ts_source = float(tick_data.get("timestamp") or time.time())
        session_label = compute_session_regime(ts_source).value
    except Exception:
        session_label = "UNKNOWN"
    session_modifiers = _session_modifiers(session_label)

    # Assemble complete state
    state = {
        "timestamp": time.time(),
        "symbol": symbol,
        "tick": tick_data,
        "candles": candles,
        "indicators": indicators,
        "trend": trend,
        "sentiment": sentiment,
        "health": health,
        "session_regime": session_label,
        "session_context": {
            "session": session_label,
            "modifiers": session_modifiers,
        },
    }

    if order_book:
        ob_snapshot = order_book.get_depth_snapshot()
        _ensure_depth(ob_snapshot)
        state["order_book"] = ob_snapshot
        # Attach liquidity metrics
        state["spread"] = compute_spread(ob_snapshot)
        state["liquidity_score"] = compute_liquidity_score(ob_snapshot)
        state["liquidity_stress_flags"] = detect_liquidity_stress(ob_snapshot)
        _ensure_liquidity_metrics(state)
    if order_flow_features:
        state["order_flow_features"] = order_flow_features.compute_features()

    atr_hint = compute_atr(indicators.get("atr_14"), window=14)
    state["volatility_state"] = vol_features.compute(
        mid_prices[-1] if mid_prices else tick_data.get("bid", 0.0),
        candle_data={
            "atr": atr_hint,
            "atr_14": atr_hint,
        },
    )

    trend_struct = compute_trend_structure(
        mid_prices,
        highs=(
            [candle["latest"]["high"] for candle in candles.values() if candle]
            if candles
            else None
        ),
        lows=(
            [candle["latest"]["low"] for candle in candles.values() if candle]
            if candles
            else None
        ),
        window=20,
        volatility_state=state["volatility_state"],
    )
    state.update(trend_struct)

    liquidity_hint = {"liquidity_shock": bool(state.get("liquidity_stress_flags"))}
    state["amd_state"] = amd_detector.compute(
        price_series=mid_prices,
        volume_series=volumes,
        liquidity_state=liquidity_hint,
    )

    logger.info(f"State built successfully for {symbol}")
    return state


def validate_state(state: Optional[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate state dictionary structure and contents.

    Args:
        state: State dictionary to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if state is None:
        return False, ["State is None"]

    required_keys = [
        "timestamp",
        "symbol",
        "tick",
        "candles",
        "indicators",
        "trend",
        "sentiment",
        "health",
    ]
    for key in required_keys:
        if key not in state:
            errors.append(f"Missing required key: {key}")

    if "tick" in state and state["tick"]:
        tick_keys = ["symbol", "timestamp", "bid", "ask", "last", "volume", "source"]
        for key in tick_keys:
            if key not in state["tick"]:
                errors.append(f"Missing tick key: {key}")
        bid = state["tick"].get("bid")
        ask = state["tick"].get("ask")
        if bid is None or ask is None:
            errors.append("Tick missing bid/ask values")
        else:
            if bid <= 0 or ask <= 0:
                errors.append("Tick has non-positive prices")
            if ask <= bid:
                errors.append("Tick spread not positive")

    if "health" in state and state["health"].get("is_stale"):
        errors.append("State data is stale")

    is_valid = len(errors) == 0
    return is_valid, errors


def _mock_tick_data(symbol: str) -> Dict:
    raise RuntimeError("Mock tick data is disabled; real market data required")


def _ensure_valid_tick_data(tick_data: Dict) -> None:
    # Validate canonical tick structure and enforce monotonicity per-symbol
    required = ["symbol", "timestamp", "bid", "ask", "last", "volume", "source"]
    for field in required:
        if tick_data.get(field) is None:
            raise StateBuilderError(f"Tick missing required field {field}")

    symbol = str(tick_data["symbol"]) if tick_data.get("symbol") is not None else ""
    bid = float(tick_data["bid"])
    ask = float(tick_data["ask"])
    ts = float(tick_data["timestamp"])

    if any(math.isnan(val) or math.isinf(val) for val in [bid, ask, ts]):
        raise StateBuilderError("Tick contains NaN/inf values")
    if bid <= 0 or ask <= 0:
        raise StateBuilderError("Tick has non-positive prices")
    if ask <= bid:
        raise StateBuilderError("Tick spread not positive (ask <= bid)")

    # Normalize stored last-seen entry: it may be a float (older code) or a dict
    last_entry = _last_tick_timestamp_by_symbol.get(symbol)
    prev_ts = prev_bid = prev_ask = prev_last = prev_vol = None
    if last_entry is not None:
        if isinstance(last_entry, dict):
            try:
                prev_ts = float(last_entry.get("ts"))
            except Exception:
                prev_ts = None
            prev_bid = last_entry.get("bid")
            prev_ask = last_entry.get("ask")
            prev_last = last_entry.get("last")
            prev_vol = last_entry.get("volume")
        else:
            try:
                prev_ts = float(last_entry)
            except Exception:
                prev_ts = None

    # Strictly drop older timestamps
    if prev_ts is not None and ts < prev_ts:
        logger.warning(
            f"Non-monotonic tick timestamp detected for {symbol}: {ts} < {prev_ts}"
        )
        raise StateBuilderError("Non-monotonic tick timestamp detected")

    # Equal timestamps: accept only if market content changed
    if prev_ts is not None and ts == prev_ts:
        try:
            if (
                float(prev_bid or 0.0) == float(bid or 0.0)
                and float(prev_ask or 0.0) == float(ask or 0.0)
                and float(prev_last or 0.0) == float(tick_data.get("last", 0.0))
                and float(prev_vol or 0.0) == float(tick_data.get("volume", 0.0))
            ):
                logger.warning(
                    f"Non-monotonic tick timestamp detected for {symbol}: {ts} == {prev_ts} with identical content"
                )
                raise StateBuilderError("Non-monotonic tick timestamp detected")
        except Exception:
            # On comparison error, be conservative and accept
            pass

    # Accept and store full last-seen dict
    _last_tick_timestamp_by_symbol[symbol] = {
        "ts": float(ts),
        "bid": float(bid),
        "ask": float(ask),
        "last": float(tick_data.get("last", 0.0)),
        "volume": float(tick_data.get("volume", 0.0)),
    }


def _ensure_valid_volatility(indicators: Dict) -> None:
    vol = indicators.get("volatility")
    if vol is None:
        return
    if math.isnan(vol) or math.isinf(vol) or vol < 0:
        raise StateBuilderError("Volatility metric invalid")


def _ensure_depth(order_book_snapshot: Dict) -> None:
    bids = (
        order_book_snapshot.get("bids")
        if isinstance(order_book_snapshot, dict)
        else None
    )
    asks = (
        order_book_snapshot.get("asks")
        if isinstance(order_book_snapshot, dict)
        else None
    )
    if not bids or not asks:
        raise StateBuilderError("Order book depth missing bids/asks")


def _ensure_liquidity_metrics(state: Dict) -> None:
    for key in ["spread", "liquidity_score"]:
        val = state.get(key)
        if val is None or math.isnan(val) or math.isinf(val):
            raise StateBuilderError(f"Invalid liquidity metric: {key}")
