"""Validation utilities for trading-stockfish."""
from typing import Any, Dict, List, Optional


def validate_symbol(symbol: str) -> bool:
    """Validate a trading symbol."""
    if not symbol or not isinstance(symbol, str):
        return False
    return len(symbol) >= 3 and symbol.isalpha()


def validate_price(price: Any) -> bool:
    """Validate a price value."""
    try:
        p = float(price)
        return p > 0 and not (p != p)  # Check for NaN
    except (TypeError, ValueError):
        return False


def validate_state_dict(state: Dict) -> List[str]:
    """Validate a market state dictionary and return list of errors."""
    errors = []
    
    if not isinstance(state, dict):
        errors.append("State must be a dictionary")
        return errors
    
    required_keys = ["timestamp", "symbol"]
    for key in required_keys:
        if key not in state:
            errors.append(f"Missing required key: {key}")
    
    return errors


def is_valid_timeframe(timeframe: str) -> bool:
    """Check if a timeframe string is valid."""
    valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
    return timeframe in valid_timeframes
