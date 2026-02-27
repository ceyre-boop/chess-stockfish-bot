"""tests_live/test_alpaca_intraday.py

Minimal live validator for Alpaca intraday 1-minute bars (AAPL).
Pulls last 60 1-minute bars, prints raw/normalized OHLCV, features,
regime and confidence, then iterates for 60 seconds printing one bar/sec.
"""
import time
import math
from datetime import datetime, timedelta

from adapters.alpaca_adapter import get_historical_bars


def extract_features(bar):
    # bar is dict with open/high/low/close/volume
    momentum = (bar["close"] - bar["open"]) if bar.get("open") is not None else 0.0
    volatility = (bar["high"] - bar["low"]) if (bar.get("high") is not None and bar.get("low") is not None) else 0.0
    spread = 0.0
    return {"momentum": momentum, "volatility": volatility, "spread": spread}


def classify_regime(features):
    m = features.get("momentum", 0.0)
    if m > 0:
        return "bull", min(1.0, abs(m) / (features.get("volatility", 1.0) + 1e-6))
    if m < 0:
        return "bear", min(1.0, abs(m) / (features.get("volatility", 1.0) + 1e-6))
    return "neutral", 0.0


def validate_bar_schema(bar):
    required = ["timestamp_utc", "open", "high", "low", "close", "volume"]
    for f in required:
        if f not in bar:
            raise RuntimeError(f"Missing field: {f}")
        v = bar[f]
        if v is None:
            raise RuntimeError(f"Null value for {f}")
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise RuntimeError(f"Invalid numeric for {f}: {v}")


def main():
    print("Alpaca intraday live test — AAPL (60 bars)")
    # Request a window large enough to contain 60 1-min bars
    end = datetime.utcnow()
    start = end - timedelta(minutes=120)
    try:
        bars = get_historical_bars("AAPL", start, end, "1Min")
    except Exception as e:
        print("Alpaca API error:", e)
        return

    if not bars:
        print("No bars returned from Alpaca")
        return

    # Keep most recent 60
    bars = bars[-60:]

    # Print one bar per second (simulate live validation)
    for i, b in enumerate(bars):
        try:
            validate_bar_schema(b)
            normalized = {
                "timestamp": b.get("timestamp_utc"),
                "open": float(b.get("open")),
                "high": float(b.get("high")),
                "low": float(b.get("low")),
                "close": float(b.get("close")),
                "volume": int(b.get("volume")),
            }

            features = extract_features(normalized)
            regime, confidence = classify_regime(features)

            print(f"--- Bar {i+1} ---")
            print("Raw:", b)
            print("Normalized:", normalized)
            print("Features:", features)
            print("Regime:", regime)
            print("Confidence:", confidence)

        except Exception as e:
            print(f"Validation error on bar {i}: {e}")
        time.sleep(1)


if __name__ == '__main__':
    main()
