import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

SYMBOL = "AAPL"
LIMIT = 10

# --- POLYGON DAILY BARS ---
def get_polygon_daily_bars(symbol=SYMBOL, limit=LIMIT):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2020-01-01/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    params = {"apiKey": POLYGON_API_KEY, "limit": limit}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    bars = data.get("results", [])[-limit:]
    return [
        {
            "timestamp": datetime.fromtimestamp(bar["t"] / 1000, tz=timezone.utc),
            "close": bar["c"],
        }
        for bar in bars
    ]

# --- ALPACA DAILY BARS ---
def get_alpaca_daily_bars(symbol=SYMBOL, limit=LIMIT):
    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")
    bars = api.get_bars(symbol, "1D", limit=limit).df
    return [
        {
            "timestamp": bar.name,
            "close": bar.close,
        }
        for _, bar in bars.iterrows()
    ]

polygon_bars = get_polygon_daily_bars()
alpaca_bars = get_alpaca_daily_bars()

print("timestamp\tPolygon close\tAlpaca close\tdiff")
for pb, ab in zip(polygon_bars, alpaca_bars):
    diff = pb["close"] - ab["close"]
    print(f"{pb['timestamp']}\t{pb['close']}\t{ab['close']}\t{diff}")
