from typing import Protocol, Any, Callable, Iterator
from queue import Queue, Empty

# 1. MarketEvent Protocol (type marker only)
class MarketEvent(Protocol):
    pass

# 2. EventBus class
class EventBus:
    def __init__(self):
        self._queue: Queue[MarketEvent] = Queue()

    def publish(self, event: MarketEvent) -> None:
        self._queue.put(event)

    def consume(self) -> MarketEvent:
        try:
            return self._queue.get_nowait()
        except Empty:
            raise RuntimeError("No events to consume.")

# 3. pump_stream function

def pump_stream(raw_stream: Iterator[Any], adapter: Callable[[Any], MarketEvent], bus: EventBus):
    """
    For each raw payload in raw_stream, convert to event via adapter, publish to bus.
    """
    for raw in raw_stream:
        event = adapter(raw)
        bus.publish(event)
