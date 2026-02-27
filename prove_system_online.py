import os
import traceback
from datetime import datetime, timezone

# --- POLYGON ---
def check_polygon():
    try:
        from polygon import RESTClient
        api_key = os.getenv("POLYGON_API_KEY")
        client = RESTClient(api_key)
        bars = list(client.list_aggs("AAPL", 1, "minute", limit=10))
        if not bars:
            raise ValueError("No bars returned.")
        last = bars[-1]
        print("\n[Polygon]")
        print(f"Symbol: AAPL")
        print(f"Last Bar: {datetime.fromtimestamp(last.timestamp/1000, tz=timezone.utc)}")
        print(f"OHLCV: O={last.open}, H={last.high}, L={last.low}, C={last.close}, V={last.volume}")
    except Exception as e:
        print("\n[Polygon] ERROR:", e)
        traceback.print_exc(limit=1)

# --- ALPACA ---
def check_alpaca():
    try:
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(
            os.getenv("ALPACA_API_KEY"),
            os.getenv("ALPACA_SECRET_KEY"),
            base_url="https://paper-api.alpaca.markets"
        )
        bars = api.get_bars("AAPL", "1Min", limit=10).df
        if bars.empty:
            raise ValueError("No bars returned.")
        last = bars.iloc[-1]
        print("\n[Alpaca]")
        print(f"Symbol: AAPL")
        print(f"Last Bar: {last.name}")
        print(f"OHLCV: O={last.open}, H={last.high}, L={last.low}, C={last.close}, V={last.volume}")
    except Exception as e:
        print("\n[Alpaca] ERROR:", e)
        traceback.print_exc(limit=1)

# --- MT5 ---
def check_mt5():
    try:
        import MetaTrader5 as mt5
        login = int(os.getenv("MT5_LOGIN"))
        password = os.getenv("MT5_PASSWORD")
        server = os.getenv("MT5_SERVER")
        symbol = "US500.cash"
        if not mt5.initialize(server=server, login=login, password=password):
            raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 10)
        if rates is None or len(rates) == 0:
            raise ValueError("No bars returned.")
        last = rates[-1]
        print("\n[MT5]")
        print(f"Symbol: {symbol}")
        print(f"Last Bar: {datetime.fromtimestamp(last['time'], tz=timezone.utc)}")
        print(f"OHLCV: O={last['open']}, H={last['high']}, L={last['low']}, C={last['close']}, V={last['tick_volume']}")
        mt5.shutdown()
    except Exception as e:
        print("\n[MT5] ERROR:", e)
        traceback.print_exc(limit=1)

if __name__ == "__main__":
    check_polygon()
    check_alpaca()
    check_mt5()