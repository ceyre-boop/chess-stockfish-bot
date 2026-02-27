"""
Lightweight smoke test to validate MT5 adapter emits canonical bars/ticks.
This test is defensive: it never initializes MT5 or fabricates data.
It calls adapter functions if available and prints structured output.

Do NOT run automatically; this file is created for manual invocation.
"""

import math
import traceback
from datetime import datetime, timedelta

# Try adapters.mt5_adapter (historical bars hardening)
try:
    from adapters import mt5_adapter as mt5_adapter
except Exception:
    mt5_adapter = None

# Try data.mt5_adapter (live stream, if present)
try:
    from data import mt5_adapter as data_mt5_adapter
except Exception:
    data_mt5_adapter = None


def _is_valid_number(x):
    try:
        if x is None:
            return False
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return False
        return True
    except Exception:
        return False


def validate_bar(bar):
    """Validate a single bar (dataclass or dict) has canonical fields.
    Required fields: timestamp (float), bid (float), ask (float), last_price (float), volume (float)
    """
    out = {
        "ok": False,
        "errors": [],
    }
    try:
        # support dataclass or dict
        if hasattr(bar, "__dict__") and not isinstance(bar, dict):
            get = lambda k: getattr(bar, k, None)
        else:
            get = lambda k: bar.get(k)

        ts = get("timestamp")
        bid = get("bid")
        ask = get("ask")
        last_price = get("last_price") if get("last_price") is not None else get("last") if get("last") is not None else get("price")
        volume = get("volume")

        if not _is_valid_number(ts) or float(ts) <= 0:
            out["errors"].append("invalid timestamp")
        if not _is_valid_number(bid):
            out["errors"].append("invalid bid")
        if not _is_valid_number(ask):
            out["errors"].append("invalid ask")
        if not _is_valid_number(last_price):
            out["errors"].append("invalid last_price")
        if not _is_valid_number(volume):
            out["errors"].append("invalid volume")

        if not out["errors"]:
            out["ok"] = True
    except Exception as e:
        out["errors"].append(f"exception during validation: {e}")
    return out


if __name__ == "__main__":
    print("=== MT5 Adapter Smoke Test ===")

    # Historical bars
    if mt5_adapter is None:
        print("adapters.mt5_adapter not importable; skipping historical bars test")
    else:
        try:
            now = datetime.utcnow()
            start = now - timedelta(minutes=5)
            end = now
            print("Calling adapters.mt5_adapter.get_historical_bars_mt5(...) in a safe wrapper")
            try:
                bars = mt5_adapter.get_historical_bars_mt5("EURUSD", start, end, "M1")
            except ImportError:
                print("No data returned (MT5 not installed or not available)")
                bars = []
            except Exception as e:
                print("Error calling get_historical_bars_mt5:")
                traceback.print_exc()
                bars = []

            if not bars:
                print("No data returned from get_historical_bars_mt5")
            else:
                for idx, bar in enumerate(bars[:10]):
                    res = validate_bar(bar)
                    if res["ok"]:
                        print(f"MT5 bar OK [{idx}]")
                    else:
                        print(f"MT5 bar FAILED [{idx}] - errors: {res['errors']}")
        except Exception:
            print("Unexpected error during historical bars test:")
            traceback.print_exc()

    # Live tick stream (attempt one sample) - do not initialize live connection
    if data_mt5_adapter is None:
        print("data.mt5_adapter not importable; skipping live tick test")
    else:
        try:
            # Try to obtain one tick from stream_live, but guard against connection attempts
            print("Attempting to obtain one tick from data.mt5_adapter.stream_live (safe attempt)")
            gen = None
            try:
                gen = data_mt5_adapter.stream_live("EURUSD", poll_interval=0.1)
                tick = next(gen)
            except StopIteration:
                print("No data returned from stream_live (generator ended)")
                tick = None
            except Exception as e:
                # Expected in environments without MT5 or when not connected
                print("No data returned from stream_live (exception):", str(e))
                tick = None
            finally:
                # If generator created and has close, close it
                try:
                    if gen is not None:
                        gen.close()
                except Exception:
                    pass

            if not tick:
                print("No data returned from live tick stream")
            else:
                # validate tick dict
                res = validate_bar(tick)
                if res["ok"]:
                    print("MT5 tick OK")
                else:
                    print(f"MT5 tick FAILED - errors: {res['errors']}")
        except Exception:
            print("Unexpected error during live tick test:")
            traceback.print_exc()

    print("=== MT5 Adapter Smoke Test Complete ===")
