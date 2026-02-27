from typing import Protocol, Iterable
from engine.io.record_replay import replay_stream

class Connector(Protocol):
    def stream(self) -> Iterable[dict]:
        ...


class ReplayConnector:
    def __init__(self, provider: str):
        self.provider = provider

    def stream(self) -> Iterable[dict]:
        return replay_stream(self.provider)

import requests

import time

class PolygonLiveConnector:
    def __init__(self, api_key: str, limit: int = 5):
        self.api_key = api_key
        self.limit = limit

    def stream(self) -> Iterable[dict]:
        url = "https://api.polygon.io/v3/bars"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        last_ts = None
        for _ in range(self.limit):
            params = {
                "symbols": "BTCUSD",
                "limit": 1
            }
            if last_ts is not None:
                params["timestamp.gte"] = last_ts
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            if resp.status_code != 200:
                raise RuntimeError(f"Polygon error {resp.status_code}: {resp.text}")
            data = resp.json()
            # Extract bar timestamp and update last_ts
            results = data.get("results", [])
            if results:
                bar = results[0]
                bar_ts = bar.get("t")
                if bar_ts is not None:
                    # Add 1 ms to avoid duplicates (Polygon timestamps are in ms)
                    last_ts = str(int(bar_ts) + 1)
            yield data
            time.sleep(1)
