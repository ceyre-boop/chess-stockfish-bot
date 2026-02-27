

from engine.io.record_replay import replay_stream
from engine.io.event_bus import EventBus
from engine.runtime.engine_loop import run_engine
from engine.adapters.polygon import polygon_to_event
from engine.adapters.alpaca import alpaca_to_event
from engine.adapters.mt5 import mt5_to_event
from engine.router.provider_router import route_request, get_stream_for
from engine.io.merge_streams import merge_streams

PROVIDERS = [
    ("polygon", polygon_to_event, "equities"),
    ("alpaca", alpaca_to_event, "equities"),
    ("mt5", mt5_to_event, "forex"),
]

def reducer(state, event):
    state["events"].append(event)
    provider = getattr(event, "provider", None) or getattr(event, "source", None) or "unknown"
    state.setdefault("by_provider", {})
    state["by_provider"].setdefault(provider, 0)
    state["by_provider"][provider] += 1
    return state

def main():
    bus = EventBus()
    streams = {}
    for provider, adapter, _ in PROVIDERS:
        if provider == "polygon":
            asset_class = "equities"
        elif provider == "alpaca":
            asset_class = "equities"
        elif provider == "mt5":
            asset_class = "forex"
        else:
            asset_class = "unknown"
        raw_stream = get_stream_for(asset_class)
        event_stream = (adapter(raw) for raw in raw_stream)
        streams[provider] = event_stream
    merged = merge_streams(streams)
    for event in merged:
        bus.publish(event)
    final_state = run_engine(bus, {"events": [], "by_provider": {}}, reducer, max_events=300)
    print(f"Total events consumed: {len(final_state['events'])}")
    print("Breakdown by provider:")
    for provider, count in final_state["by_provider"].items():
        print(f"  {provider}: {count}")

if __name__ == "__main__":
    main()
