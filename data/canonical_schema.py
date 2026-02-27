"""Canonical market snapshot schema and lightweight validation utilities.

This module defines the authoritative snapshot contract for all market
data producers. It is intentionally dependency-free and small so it can be
imported in tests and inventory tools.
"""
from typing import Any, Dict

# Invariants / allowed providers (primary set)
PRIMARY_PROVIDERS = ("alpaca", "mt5", "polygon", "replay")
# Inventory-friendly providers allowed during discovery
ALLOW_PROVIDER_FALLBACK = set(PRIMARY_PROVIDERS) | {"mixed", "unknown"}

# Canonical snapshot shape: keys must exist (None allowed where noted)
CANONICAL_SNAPSHOT_SCHEMA = {
    "symbol": str,
    "provider": str,        # one of PRIMARY_PROVIDERS (allow fallback during discovery)
    "timestamp": float,     # UTC seconds (may include ms fractional part)
    "price": float,         # last trade price or mid price
    "bid": (float, type(None)),
    "ask": (float, type(None)),
    "spread": (float, type(None)),
    "volume": (float, type(None)),
    "bar": {
        "open": (float, type(None)),
        "high": (float, type(None)),
        "low": (float, type(None)),
        "close": (float, type(None)),
        "volume": (float, type(None)),
        "tf": (str, type(None)),
    },
    "quality": {
        "stale": bool,
        "synthetic": bool,
        "partial": bool,
    }
}


def _is_type(value: Any, expected) -> bool:
    """Helper: check that value conforms to expected type descriptor.

    expected may be a type, a tuple of types, or a nested dict following
    CANONICAL_SNAPSHOT_SCHEMA structure.
    """
    if isinstance(expected, dict):
        if not isinstance(value, dict):
            return False
        # every key in expected must exist (None allowed if tuple contains type(None))
        for k, v in expected.items():
            if k not in value:
                return False
            if not _is_type(value[k], v):
                return False
        return True
    if isinstance(expected, tuple):
        return any((isinstance(value, t) for t in expected if t is not type(None))) or value is None
    return isinstance(value, expected)


def canonicalize_missing_fields(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of snapshot with missing optional fields filled.

    - Ensures all top-level keys exist (fills None or defaults).
    - Ensures `bar` and `quality` substructures exist with default values.
    """
    out = dict(snapshot) if isinstance(snapshot, dict) else {}

    # Top-level required keys: ensure presence
    for key in ("symbol", "provider", "timestamp", "price", "bid", "ask", "spread", "volume"):
        out.setdefault(key, None)

    # Bar block
    bar = out.get("bar")
    if not isinstance(bar, dict):
        bar = {}
    for bk, bt in CANONICAL_SNAPSHOT_SCHEMA["bar"].items():
        bar.setdefault(bk, None)
    out["bar"] = bar

    # Quality block defaults
    quality = out.get("quality")
    if not isinstance(quality, dict):
        quality = {}
    quality.setdefault("stale", False)
    quality.setdefault("synthetic", False)
    quality.setdefault("partial", False)
    out["quality"] = quality

    return out


def validate_snapshot(snapshot: Dict[str, Any]) -> bool:
    """Lightweight boolean validation of a snapshot against schema.

    Returns True if snapshot appears to conform (keys present, types OK).
    Does not raise; use `assert_snapshot` for detailed errors.
    """
    if not isinstance(snapshot, dict):
        return False

    # Ensure top-level keys exist
    for k in CANONICAL_SNAPSHOT_SCHEMA:
        if k not in snapshot:
            return False

    # Type-check each field
    for k, expected in CANONICAL_SNAPSHOT_SCHEMA.items():
        if not _is_type(snapshot.get(k), expected):
            return False

    # provider type: allow fallback providers for discovery
    prov = snapshot.get("provider")
    if prov not in ALLOW_PROVIDER_FALLBACK:
        return False

    # timestamp numeric
    ts = snapshot.get("timestamp")
    if not isinstance(ts, (int, float)):
        return False

    return True


def assert_snapshot(snapshot: Dict[str, Any]) -> None:
    """Validate snapshot and raise descriptive AssertionError on failure."""
    if not isinstance(snapshot, dict):
        raise AssertionError("snapshot must be a dict")

    for k in CANONICAL_SNAPSHOT_SCHEMA:
        if k not in snapshot:
            raise AssertionError(f"missing key: {k}")

    for k, expected in CANONICAL_SNAPSHOT_SCHEMA.items():
        val = snapshot.get(k)
        if not _is_type(val, expected):
            raise AssertionError(f"field '{k}' has invalid type or value: {val!r}")

    prov = snapshot.get("provider")
    if prov not in ALLOW_PROVIDER_FALLBACK:
        raise AssertionError(f"provider '{prov}' not recognized; expected one of {PRIMARY_PROVIDERS}")

    ts = snapshot.get("timestamp")
    if not isinstance(ts, (int, float)):
        raise AssertionError("timestamp must be numeric seconds (float/int)")

    # spread invariant
    bid = snapshot.get("bid")
    ask = snapshot.get("ask")
    spread = snapshot.get("spread")
    if bid is not None and ask is not None:
        if spread is None:
            raise AssertionError("spread missing while bid and ask present")
        try:
            if round((ask - bid), 12) != round(spread, 12):
                raise AssertionError("spread inconsistent with ask - bid")
        except TypeError:
            raise AssertionError("bid/ask/spread must be numeric when present")


if __name__ == '__main__':
    # Self-test: construct minimal valid snapshot
    sample = {
        "symbol": "TEST",
        "provider": "mt5",
        "timestamp": 1600000000.0,
        "price": 100.0,
        "bid": 99.5,
        "ask": 100.5,
        "spread": 1.0,
        "volume": 10.0,
        "bar": {"open": None, "high": None, "low": None, "close": None, "volume": None, "tf": None},
        "quality": {"stale": False, "synthetic": False, "partial": False},
    }
    sample = canonicalize_missing_fields(sample)
    assert validate_snapshot(sample), "self-test validation failed"
    print("Schema OK")
