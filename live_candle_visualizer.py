import os
import time
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
import alpaca_trade_api as tradeapi

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
SYMBOL = "AAPL"

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")

plt.ion()
fig, ax = plt.subplots()

while True:
    bars = api.get_bars(SYMBOL, "1Min", limit=20).df
    times = [bar.name for _, bar in bars.iterrows()]
    opens = [bar.open for _, bar in bars.iterrows()]
    highs = [bar.high for _, bar in bars.iterrows()]
    lows = [bar.low for _, bar in bars.iterrows()]
    closes = [bar.close for _, bar in bars.iterrows()]
    volumes = [bar.volume for _, bar in bars.iterrows()]

    ax.clear()
    ax.plot(times, closes, label="Close", color="blue")
    ax.fill_between(times, lows, highs, color="lightgray", alpha=0.5, label="Range")
    ax.set_title(f"Live Candlestick Chart: {SYMBOL} (Alpaca)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.legend()
    ax2 = ax.twinx()
    ax2.bar(times, volumes, width=0.01, color="orange", alpha=0.3, label="Volume")
    ax2.set_ylabel("Volume")
    plt.pause(1)
