# AssetClass enum for use in mapping and routing
from enum import Enum

class AssetClass(Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    INDEX_FUTURES = "index_futures"
    METALS = "metals"

# Shared symbol constants for asset class routing and mapping

FUTURES_SYMBOLS = [
    "ES1!",
    "NQ",
]

METALS_SYMBOLS = [
    "XAUUSD",
    "XAGUSD",
]

FOREX_SYMBOLS = [
    # Add forex symbols here if needed
]
