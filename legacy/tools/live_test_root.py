"""
Quarantined tools/live_test moved to legacy/tools
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import pandas as pd
except Exception as exc:  # pragma: no cover
    print(f"pandas import failed: {exc}")
    sys.exit(1)

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"MetaTrader5 import failed: {exc}")
    sys.exit(1)

# (rest preserved for manual use)
