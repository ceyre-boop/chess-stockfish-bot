def check_polygon() -> dict:
    return {"ok": True, "reason": "offline replay mode"}

def check_alpaca() -> dict:
    return {"ok": True, "reason": "offline replay mode"}

def check_mt5() -> dict:
    return {"ok": True, "reason": "offline replay mode"}

def provider_health() -> dict:
    return {
        "polygon": check_polygon(),
        "alpaca": check_alpaca(),
        "mt5": check_mt5(),
    }
