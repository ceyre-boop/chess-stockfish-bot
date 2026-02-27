import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone, timedelta

# --- POLYGON ---
def get_polygon_bars(symbol="AAPL", limit=10):
    from polygon import RESTClient
    api_key = os.getenv("POLYGON_API_KEY")
    client = RESTClient(api_key)
    now = datetime.now(timezone.utc)
    from_ = (now - timedelta(days=limit)).strftime('%Y-%m-%d')
    to = now.strftime('%Y-%m-%d')
    bars = list(client.list_aggs(symbol, 1, "day", from_, to))
    return [
        {
            "timestamp": datetime.fromtimestamp(bar.timestamp/1000, tz=timezone.utc),
            "close": bar.close,
        }
        for bar in bars
    ]

# --- ALPACA ---
def get_alpaca_bars(symbol="AAPL", limit=10):
    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
        base_url="https://paper-api.alpaca.markets",
    )
    bars = api.get_bars(symbol, "1D", limit=limit).df
    return [
        {
            "timestamp": bar.name,
            "close": bar.close,
        }
        for _, bar in bars.iterrows()
    ]

polygon_bars = get_polygon_bars()
alpaca_bars = get_alpaca_bars()

print("timestamp\tPolygon close\tAlpaca close\tdiff")
for pb, ab in zip(polygon_bars, alpaca_bars):
    diff = pb["close"] - ab["close"]
    print(f"{pb['timestamp']}\t{pb['close']}\t{ab['close']}\t{diff}")
