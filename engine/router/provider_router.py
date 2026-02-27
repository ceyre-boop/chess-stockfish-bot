
from engine.providers.capabilities import supports
from engine.providers.health import provider_health
from engine.io.connectors import ReplayConnector, PolygonLiveConnector

# Mode switch: "replay" or "live"
MODE = "replay"  # allowed values: "replay", "live"

def get_connector(provider: str):
    if MODE == "replay":
        return ReplayConnector(provider)
    if MODE == "live":
        if provider == "polygon":
            return PolygonLiveConnector(api_key="YOUR_KEY_HERE")
        else:
            raise NotImplementedError(f"Live mode not implemented for {provider}")

def get_stream_for(asset_class: str):
    provider = choose_provider(asset_class)
    connector = get_connector(provider)
    return connector.stream()


def choose_provider(asset_class: str) -> str:
    health = provider_health()
    candidates = []
    for provider in ["polygon", "alpaca", "mt5"]:
        if supports(provider, asset_class) and health[provider]["ok"]:
            candidates.append(provider)
    if not candidates:
        return None  # or raise a clear error
    return candidates[0]  # simple deterministic routing


def route_request(asset_class: str, request_fn_map: dict):
    provider = choose_provider(asset_class)
    if provider is None:
        raise ValueError(f"No healthy provider supports asset class: {asset_class}")
    fn = request_fn_map[provider]
    return fn()
