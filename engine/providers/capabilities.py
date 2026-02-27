PROVIDER_CAPABILITIES = {
    "polygon": {
        "equities": True,
        "crypto": True,
        "forex": False,
        "futures": False,
        "metals": False,
    },
    "alpaca": {
        "equities": True,
        "crypto": True,
        "forex": False,
        "futures": False,
        "metals": False,
    },
    "mt5": {
        "equities": False,
        "crypto": False,
        "forex": True,
        "futures": True,
        "metals": True,
    },
}

def supports(provider: str, asset_class: str) -> bool:
    return PROVIDER_CAPABILITIES.get(provider, {}).get(asset_class, False)
