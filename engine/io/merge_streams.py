from typing import Iterable, Iterator, Dict
import heapq

# Assume MarketEvent has a 'timestamp' attribute

def merge_streams(streams: Dict[str, Iterable]) -> Iterator:
    """
    Merge multiple provider event streams into a single time-sorted iterator.
    """
    iterators = {provider: iter(stream) for provider, stream in streams.items()}
    heap = []
    # Initialize heap with the first event from each stream
    for provider, it in iterators.items():
        try:
            event = next(it)
            heapq.heappush(heap, (event.timestamp, provider, event, it))
        except StopIteration:
            continue
    while heap:
        ts, provider, event, it = heapq.heappop(heap)
        yield event
        try:
            next_event = next(it)
            heapq.heappush(heap, (next_event.timestamp, provider, next_event, it))
        except StopIteration:
            continue
