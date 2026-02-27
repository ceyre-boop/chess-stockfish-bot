#!/usr/bin/env python3
"""
MT5 Live Feed - Test-only mocks (moved to legacy/)

Contains dataclasses and mock/demo generators for unit tests and offline tooling.
This module must NOT be imported by runtime engine code.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, List


@dataclass
class TickData:
    symbol: str
    bid: float = 1.0
    ask: float = 1.0002
    bid_volume: int = 1000
    ask_volume: int = 1000
    last: float = 1.0001
    time: int = field(default_factory=lambda: int(time.time()))
    time_msc: int = field(default_factory=lambda: int(time.time() * 1000))
    timestamp: float = 0.0

    def __post_init__(self):
        ts = float(self.time_msc) / 1000.0 if self.time_msc else float(self.time)
        self.timestamp = ts

    def to_canonical(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": float(self.timestamp),
            "bid": float(self.bid),
            "ask": float(self.ask),
            "last": float(self.last),
            "volume": float(self.bid_volume + self.ask_volume),
            "source": "mt5",
        }


@dataclass
class CandleData:
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    time: int
    count: int

    def to_canonical(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": int(self.volume),
            "timestamp": float(self.time),
            "source": "mt5",
        }


def mock_tick(symbol: str) -> Dict:
    t = TickData(symbol=symbol)
    return t.to_canonical()


def mock_candles(symbol: str, timeframe: str, count: int = 10) -> List[Dict]:
    now = int(time.time())
    candles = []
    for i in range(count):
        open_p = 1.0 + i * 0.0001
        close_p = open_p + 0.00005
        high_p = max(open_p, close_p) + 0.00008
        low_p = min(open_p, close_p) - 0.00005
        ts = now - (count - i) * 60
        c = CandleData(
            symbol=symbol,
            timeframe=timeframe,
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=1000,
            time=ts,
            count=count,
        )
        candles.append(c.to_canonical())
    return candles
