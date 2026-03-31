"""Utility helper functions for trading-stockfish."""
from typing import Any, Dict, List, Optional


def safe_get(d: Dict, key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary."""
    return d.get(key, default)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def format_price(price: float, decimals: int = 5) -> str:
    """Format a price with specified decimal places."""
    return f"{price:.{decimals}f}"


def calculate_pips(price1: float, price2: float, symbol: str = "EURUSD") -> float:
    """Calculate pip difference between two prices."""
    multiplier = 10000 if "JPY" not in symbol else 100
    return abs(price1 - price2) * multiplier
