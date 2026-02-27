"""
Quarantined tools/check_env original moved to legacy/tools
"""

import os
import sys
from pathlib import Path
from typing import Dict, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import requests  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"requests import failed: {exc}")
    sys.exit(1)

try:
    from dotenv import load_dotenv  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"python-dotenv import failed: {exc}")
    sys.exit(1)

# (rest of original tool preserved for manual use)
