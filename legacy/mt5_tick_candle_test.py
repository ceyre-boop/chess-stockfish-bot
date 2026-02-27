import os
import traceback
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

import MetaTrader5 as mt5

login = int(os.getenv("MT5_LOGIN"))
password = os.getenv("MT5_PASSWORD")
server = os.getenv("MT5_SERVER")
symbol = "EURUSD"

if not mt5.initialize(server=server, login=login, password=password):
    raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

# --- Real-time ticks ---
ticks = mt5.copy_ticks_from(symbol, datetime.now() - timedelta(minutes=5), 0, 20)
print("\n[MT5] Last 20 ticks:")
for tick in ticks:
    print(f"time: {datetime.fromtimestamp(tick['time'], tz=timezone.utc)} | bid: {tick['bid']} | ask: {tick['ask']} | volume: {tick['volume']}")

# --- 1m candles ---
bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 10)
print("\n[MT5] Last 10 candles:")
for bar in bars:
    print(f"time: {datetime.fromtimestamp(bar['time'], tz=timezone.utc)} | O: {bar['open']} | H: {bar['high']} | L: {bar['low']} | C: {bar['close']} | V: {bar['tick_volume']} | spread: {bar['spread']}")

mt5.shutdown()
