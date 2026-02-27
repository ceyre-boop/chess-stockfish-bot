import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import alpaca_trade_api as tradeapi

# Placeholder feature extraction
def extract_features(bar):
    features = {
        "momentum": bar.close - bar.open,
        "volatility": bar.high - bar.low,
        "spread": bar.close - bar.open,
    }
    return features

# Placeholder regime classifier
def classify_regime(features):
    if features["momentum"] > 0:
        return "bull"
    elif features["momentum"] < 0:
        return "bear"
    else:
        return "neutral"

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
SYMBOL = "AAPL"

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")
bars = api.get_bars(SYMBOL, "1Min", limit=60).df

for _, bar in bars.iterrows():
    raw = {
        "timestamp": bar.name,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
    }
    normalized = {k: v for k, v in raw.items()}  # Placeholder normalization
    features = extract_features(bar)
    regime = classify_regime(features)
    confidence = abs(features["momentum"]) / (features["volatility"] + 1e-6)
    print("--- Candle ---")
    print("Raw:", raw)
    print("Normalized:", normalized)
    print("Features:", features)
    print("Regime:", regime)
    print("Confidence:", confidence)
